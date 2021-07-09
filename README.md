# pycrotuner
MIDI microtuner - Live MIDI input transformer for microtonal performance and composition

Note: This project is not yet ready for release or contributions.

Pycrotuner is a graphical application for performing and composing microtonal music. It
reads [Scala](http://huygens-fokker.org/scala) .scl scale files and .kbm keyboard map files to
map input MIDI notes to output notes and pitch bend messages. Pycrotuner supports 16-part polyphony,
outputting each voice to a separate channel, and an arbitrary
number of scales and mappings. It can switch tunings and parameters on the fly by keying
off of MIDI notes and messages as specified in its main configuration file. Pycrotuner outputs
controller messages when the tuning reference (e.g. A440) changes so that other tracks may
compensate for the pitch shift. Specific MIDI 
messages may also be treated as global and routed to all output channels. 

Most synthesizers and plugins do not support polyphonic pitch bends and do not
keep track of multiple instances of the same note with different pitch bends.
For this reason it is necessary to use a separate track and instance of the plugin
for each voice. 

The Logic Pro template in this project contains the following:
* One External Instrument track for input
* 16 retuned output tracks, each running a different instance of the same instrument
* One reference pitch bend output track
* MIDI Environment that intercepts the input, routes output voices to 16 instrument tracks, and routes the reference to the reference track

If no MIDI controller is available, notes may be played with the computer keyboard or mouse. Different
computer keyboard types are available:
* Standard piano keyboard
* Non-standard piano keyboards \([Vertical Keyboards](https://web.archive.org/web/20200930185217/http://www.verticalkeyboards.com/keyboardoptions/microtonalkeyboards/index.html)\)
* Grid keyboard \([Linnstrument](https://www.rogerlinndesign.com/linnstrument)\)
* Isomorphic keyboard \([Lumatone](https://www.lumatone.io/)\)
* [Tuning Lattices](https://en.wikipedia.org/wiki/Lattice_(music))

This software is being developed and tested on MacOS Catalina with Logic Pro 10.6. It
depends on the following packages:
* wxpython
* mido
* python-rtmidi
* pycairo

