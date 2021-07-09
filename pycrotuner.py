#!/usr/bin/env python.app

# Copyleft 2021 GPL v3.0 Affero
# Drew Swalley

import mido
import time
from math import floor
from threading import Thread
import wx

# Initial code based on https://wiki.wxpython.org/LongRunningTasks

# Button definitions
ID_START = wx.NewIdRef()
ID_STOP = wx.NewIdRef()

# Define notification event for thread completion
EVT_RESULT_ID = wx.NewIdRef()

def EVT_RESULT(win, func):
    """Define Result Event."""
    win.Connect(-1, -1, EVT_RESULT_ID, func)

class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""
    def __init__(self, data):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_RESULT_ID)
        self.data = data

# Thread class that executes processing
class WorkerThread(Thread):
    # 24-tet
    cents = [
        0, 50, 100, 150,
        200, 250, 300, 350,
        400, 450, 500, 550,
        600, 650, 700, 750,
        800, 850, 900, 950,
        1000, 1050, 1100, 1150
    ]

    num_degrees = 24
    midi_range_lo = 0
    midi_range_hi = 127
    midi_start_tonic = 60
    midi_ref = 69
    ref_freq = 440.0
    cycle_cent = 1200
    map_size = 24
    kbm_map = [
        0,  1,  2,  3,  4,  5,  6,  7,
        8,  9, 10, 11, 12, 13, 14, 15,
        16, 17, 18, 19, 20, 21, 22, 23
    ]

    pbr = 200

    note2channel = [{} for i in range(128)]
    speaking = [False] * 16


    """Worker Thread Class."""
    def __init__(self, notify_window):
        """Init Worker Thread Class."""
        Thread.__init__(self)
        self._notify_window = notify_window
        self._want_abort = 0
        # This starts the thread running on creation, but you could
        # also make the GUI thread responsible for calling this
        self.start()

    def run(self):
        self.process_messages(self)
        wx.PostEvent(self._notify_window, ResultEvent(None))
        return

    def abort(self):
        """abort worker thread."""
        # Method for use by main thread to signal an abort
        self._want_abort = 1


    def process_messages(self, workerThread):
        qs8 = mido.open_input('qs8', autoreset=True)
        logic = mido.open_output('IAC Driver retuner')

        # Round-robin channel selection
        # Mido nunbers the channels 0-15
        rrch = -1

        while True:
            try:
                for message in qs8.iter_pending():
                    if message.type == 'note_off':
                        note_out, bend_out = self.retune(message.note)
                        message.note = note_out
                        ch = self.note2channel[note_out][bend_out]
                        message.channel = ch
                        self.speaking[ch] = False
                        # Bends still-sounding note release
                        # bend = mido.Message('pitchwheel', channel=ch, pitch=0)
                        # logic.send(bend)
                        logic.send(message)
                        self.note2channel[note_out].pop(bend_out, None)
                        print(f'{message}', end=', ')
                        self.print_poly(self.note2channel)

                    elif message.type == 'note_on':
                        if all(self.speaking):
                           print('Max polyphony')
                           continue

                        note_out, bend_out = self.retune(message.note)
                        message.note = note_out

                        looking = True
                        lookcount = 0
                        while looking:
                            rrch += 1
                            if (rrch == 16):
                                rrch = 0
                            if not self.speaking[rrch]:
                                looking = False
                                break

                            lookcount += 1
                            if lookcount == 16:
                                break

                        if looking:
                            print('no nonspeacking channels')
                            continue
                        
                        message.channel = rrch
                        self.note2channel[note_out][bend_out] = rrch
                        self.speaking[rrch] = True
                        bend = mido.Message('pitchwheel', channel=rrch, pitch=bend_out)
                        print(f' {message}', end=', ')
                        self.print_poly(self.note2channel)
                        logic.send(bend)
                        logic.send(message)

                    elif message.type == 'control_change' and message.control == 64:
                        for i in range(16):
                            message.channel = i
                            logic.send(message)
                    else:
                        # TODO: Aftertouch: Look up channel similar to note_off, send there
                        print(message)

            except Exception as e:
                print('')
                print(e)

            if self._want_abort == 1:
                qs8.close()
                logic.close()
                return


    def print_poly(self, aod):
        """ Print polyphony information for debugging """
        print([int(s) for s in self.speaking], end=', ')
        print([f'{i}{aod[i]}' for i,v in enumerate(aod)
               if len(aod[i].keys())])


    def retune(self, note_in):
        # "octaves" (cycles) relative to midi_start_tonic
        map_cycles = floor((note_in - self.midi_start_tonic) / self.map_size)

        # midi_in tonic for this cycle
        self.midi_map_tonic = self.midi_start_tonic + map_cycles*12
        kbm_index = (note_in - self.midi_start_tonic) % self.map_size
        cent_index = self.kbm_map[kbm_index]

        # TODO:  if cent_index = -1, don't emit the note
        cent = self.cents[cent_index]
        note_out = self.midi_map_tonic + floor(cent/100)
        cent_bend = cent - 100*(note_out - self.midi_map_tonic)
        # TODO:  Add controller pitch bend
        # TODO:  Add ref_freq compensation
        # MIDI: pitch bend range = (0, 16383), with 8192 = no bend
        # mido: pitch bend range = (-8192, 8191), with 0 = no bend
        bend_out = round(cent_bend*8192/self.pbr)

        # print(f'note_in:{note_in} note_out:{note_out} bend_out:{bend_out} map_cycles:{map_cycles} midi_map_tonic:{self.midi_map_tonic} kbm_index:{kbm_index} cent_index:{cent_index} cent:{cent} cent_bend:{cent_bend}')

        if bend_out > 8191:
            print(f'oops {bend_out} -> 8191')
            bend_out = 8191

        if bend_out < -8192:
            print(f'oops {bend_out} -> -8192')
            bend_out = -8192

        return (note_out, bend_out)

# GUI Frame class that spins off the worker thread
class MainFrame(wx.Frame):
    """Class MainFrame."""
    def __init__(self, parent, id):
        """Create the MainFrame."""
        wx.Frame.__init__(self, parent, id, 'Thread Test')

        # Dumb sample frame with two buttons
        wx.Button(self, ID_START, 'Start', pos=(0,0))
        wx.Button(self, ID_STOP, 'Stop', pos=(0,50))
        self.status = wx.StaticText(self, -1, '', pos=(0,100))

        self.Bind(wx.EVT_BUTTON, self.OnStart, id=ID_START)
        self.Bind(wx.EVT_BUTTON, self.OnStop, id=ID_STOP)

        # Set up event handler for any worker thread results
        EVT_RESULT(self,self.OnResult)

        # And indicate we don't have a worker thread yet
        self.worker = None

    def OnStart(self, event):
        """Start Computation."""
        # Trigger the worker thread unless it's already busy
        if not self.worker:
            self.status.SetLabel('Starting computation')
            self.worker = WorkerThread(self)

    def OnStop(self, event):
        """Stop Computation."""
        # Flag the worker thread to stop if running
        if self.worker:
            self.status.SetLabel('Trying to abort computation')
            self.worker.abort()

    def OnResult(self, event):
        """Show Result status."""
        if event.data is None:
            # Thread aborted (using our convention of None return)
            self.status.SetLabel('Computation aborted')
        else:
            # Process results here
            self.status.SetLabel('Computation Result: %s' % event.data)
        # In either event, the worker is done
        self.worker = None

class MainApp(wx.App):
    """Class Main App."""
    def OnInit(self):
        """Init Main App."""
        self.frame = MainFrame(None, -1)
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True

if __name__ == '__main__':
    app = MainApp(0)
    app.MainLoop()
