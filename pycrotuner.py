#!/usr/bin/env python.app

# Copyleft 2021 GPL v3.0 Affero
# Drew Swalley

import mido
import time
from math import floor, log2
from threading import Thread
import wx
import re

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
class RetunerThread(Thread):

    scl = None
    kbm = None

    # Pitch bend range, cents
    pbr = 200

    note2channel = [{} for i in range(128)]
    speaking = [False] * 16


    def __init__(self, notify_window):

        # Match Scala .scl ratio and cent values
        # cents may be floats or ints
        self.reRatio = re.compile(r'(\d+)\/(\d+)')
        self.reFloat = re.compile(r'([-+]?\d+\.\d*)')
        self.reInt   = re.compile(r'\d+')

        Thread.__init__(self)
        self._notify_window = notify_window
        self._want_abort = 0
        # This starts the thread running on creation, but you could
        # also make the GUI thread responsible for calling this
        self.start()

    def run(self):
        self.scl = self.load_scl('24edo.scl')
        self.kbm = self.load_kbm('24edo.kbm')
        print(self.scl)
        print(self.kbm)

        self.process_messages(self)
        wx.PostEvent(self._notify_window, ResultEvent(None))
        return

    def abort(self):
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
                        if note_out is None:
                            print('unmapped note off')
                            # Unmapped note
                            continue

                        message.note = note_out
                        ch = self.note2channel[note_out][bend_out]
                        message.channel = ch
                        self.speaking[ch] = False
                        # Don't un-bend note-off events.  The note's decay is still sounding.
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
                        if note_out is None:
                            print('unmapped note_on')
                            # Unmapped note
                            continue

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
        # "octaves" (scale cycles) relative to kbm['start']
        map_cycles = floor((note_in - self.kbm['start']) / self.kbm['size'])

        # midi_in tonic for this cycle
        mapped_tonic = self.kbm['start'] + map_cycles*12
        kbm_index = (note_in - self.kbm['start']) % self.kbm['size']
        cent_index = self.kbm['degrees'][kbm_index]

        if cent_index < 0:
            return (None, None)

        cent = self.scl['cents'][cent_index]
        note_out = mapped_tonic + floor(cent/100)
        cent_bend = cent - 100*(note_out - mapped_tonic)
        # TODO:  Add controller pitch bend
        # TODO:  Add ref_freq compensation
        # mido: pitch bend range = (-8192, 8191), with 0 = no bend
        bend_out = round(cent_bend*8192/self.pbr)

        # print(f'note_in:{note_in} note_out:{note_out} bend_out:{bend_out} map_cycles:{map_cycles} midi_map_tonic:{mapped_tonic} kbm_index:{kbm_index} cent_index:{cent_index} cent:{cent} cent_bend:{cent_bend}')

        if bend_out > 8191:
            print(f'oops {bend_out} -> 8191')
            bend_out = 8191

        if bend_out < -8192:
            print(f'oops {bend_out} -> -8192')
            bend_out = -8192

        return (note_out, bend_out)

    def load_scl(self, filename):
        """
        Read a Scala .scl file as defined here:
        http://www.huygens-fokker.org/scala/scl_format.html
        Lines beginning with a ! are comments.

        Return a dictionary:
          description:  The first non-comment line
          cents:        Array of notes from the .scl file, in cents
                         0 is prepended as an implicit scale degree.
        """

        found_description = False
        found_notes = False
        cents = [0]

        err = f'Error reading scale file {filename}: '

        lineno = 0
        with open(filename, encoding='utf8') as scl:
            for line in scl:
                lineno += 1
                line = line.strip()
                if line[0] == '!':
                    continue

                if not found_description:
                    description = line
                    found_description = True
                    continue

                if not found_notes:
                    m = self.reInt.match(line)
                    if not m:
                        print(f'{err} invalid number of notes on line {lineno}: {line}')
                        return None

                    notes = int(line)
                    found_notes = True
                    continue

                cent = self.read_cents(line)
                if not cent:
                    print(f'{err} invalid cents value on line {lineno}: {line}')
                    return None

                cents.append(cent)

        if notes != len(cents) - 1:
            print(f'{err} expected {notes} notes but found {len(cents)}')
            return None

        return {
            'description': description,
            'cents': cents,
            }

    def load_kbm(self, filename):
        """
        Read a Scala ..kbm file as defined here:
        http://www.huygens-fokker.org/scala/help.htm#mappings
        Lines beginning with a ! are comments.

        Return a dictionary:
          size:     Size of map.  The pattern repeats every so many keys.
          first:    First MIDI note number to retune.
          last:     Last MIDI note number to retune.
          start:    Middle note where the first entry of the mapping is tuned to.
                     (e.g. 60 = C3)
          refnote:  MIDI note for which the reference frequency is given.
                     (e.g. 69 = A3)
          reffreq:  Frequency of the refnote in Hz
                     (e.g. 440.0)
          octave:   Scale degree representing the difference in pitch between
                     adjacent mapping patterns.  The ratio of this scale degree
                     does not have to be 2 (1200 cents).
          degrees:  Array of scale degrees to map to keys.  The first entry
                     is for the 'start' MIDI note, and the rest are for subsequent
                     higher keys.  An 'x' represents an unmapped scale degree.
        """

        found_size = False
        found_first = False
        found_last = False
        found_start = False
        found_refnote = False
        found_reffreq = False
        found_octave = False
        degrees = []

        err = f'Error reading keyboard map file {filename}: '

        lineno = 0
        with open(filename, encoding='utf8') as kbm:
            for line in kbm:
                lineno += 1
                line = line.strip()
                if line[0] == '!':
                    continue

                err2 = f'on line {lineno}: {line}'
                i = self.read_uint(line)
                f = self.read_float(line)

                if not found_size:
                    if i is None or i == 0:
                        print(f'{err} invalid size {err2}')
                        return None
                    size = i
                    found_size = True
                    continue

                if not found_first:
                    if i is None or i > 127:
                        print(f'{err} invalid first MIDI note {err2}')
                        return None
                    first = i
                    found_first = True
                    continue

                if not found_last:
                    if i is None or i > 127:
                        print(f'{err} invalid last MIDI note {err2}')
                        return None
                    last = i
                    found_last = True
                    continue

                if not found_start:
                    if i is None or i > 127:
                        print(f'{err} invalid start MIDI note {err2}')
                        return None
                    start = i
                    found_start = True
                    continue

                if not found_refnote:
                    if i is None or i > 127:
                        print(f'{err} invalid refnote MIDI note {err2}')
                        return None
                    refnote = i
                    found_refnote = True
                    continue

                if not found_reffreq:
                    if not f:
                        print(f'{err} invalid reference frequency {err2}')
                        return None
                    reffreq = f
                    found_reffreq = True
                    continue

                if not found_octave:
                    if i is None:
                        print(f'{err} invalid octave degree {err2}')
                        return None
                    octave = i
                    found_octave = True
                    continue

                degree = self.read_degree(line)
                if degree is None:
                    print(f'{err} invalid scale degree {err2}')
                    return None

                degrees.append(degree)

        if size != len(degrees):
            print(f'{err} expected {size} scale degrees but found {len(degrees)}')
            return None

        return {
            'size': size,
            'first': first,
            'last': last,
            'start': start,
            'refnote': refnote,
            'reffreq': reffreq,
            'octave': octave,
            'degrees': degrees
            }



    def read_uint(self, line):
        """
        Convert the string 'line' to a positive integer.
        Return None upon error.
        """
        m = self.reInt.match(line)
        if not m:
            return None

        i = int(m.group(0))
        if i < 0:
            return None

        return i


    def read_float(self, line):
        """
        Convert the string 'line' to a positive float.
        Return None upon error.
        """
        m = self.reFloat.match(line)
        if not m:
            return None

        f = float(m.group(0))
        if f < 0:
            return None

        return f


    def read_degree(self, line):
        """
        Convert the string 'line' from a Scala .kbm file
        to an integer scale degree.  An 'x' gets mapped to -1,
        meaning that the scale degree is not mapped to a key.
        """
        if line[0] == 'x' or line[0] == 'X':
            return -1

        return self.read_uint(line)


    def read_cents(self, line):
        """ 
        'line' is a string representation of a musical interval,
        either as a float (cents), or a ratio.
        Convert ratios to cents: 1200*log2(ratio)

        Return None upon error.
        """
        m = self.reFloat.match(line)
        if m:
            return float(m.group(0))
        m = self.reRatio.match(line)
        if m:
            try:
                return 1200.0*log2(int(m.group(1))/int(m.group(2)))
            except:
                return None

        m = self.reInt.match(line)
        if m:
            return float(m.group(0))

        return None



# GUI Frame class that spins off the retuner thread
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
            self.status.SetLabel('Starting retuner')
            self.worker = RetunerThread(self)

    def OnStop(self, event):
        """Stop Computation."""
        # Flag the worker thread to stop if running
        if self.worker:
            self.status.SetLabel('Trying to abort retuner')
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
