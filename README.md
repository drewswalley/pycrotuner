# pycrotuner
MIDI microtuner - Live MIDI input transformer for microtonal performance and composition

Note: This project is not yet ready for release or contributions.

Pycrotuner is a graphical application for performing and composing microtonal music. It
reads [Scala](http://huygens-fokker.org/scala) .scl and .kbm files to
transform live MIDI input to new notes with pitch bend messages. Pycrotuner supports 16-part polyphony,
outputting each voice to a separate channel.  It loads an arbitrary
number of scales and mappings and can switch between them the fly by keying
off of messages as specified in its main configuration file. Pycrotuner outputs
a ccontroller message for the current tuning reference (e.g. A440) so that other tracks may
compensate for changes. Specific MIDI 
messages may also be treated as global and routed to all output channels. 

If no MIDI controller is available, notes may be played with the computer keyboard or mouse. Different
computer keyboard types are available:
* Standard piano keyboard
* Non-standard piano keyboards \([Vertical Keyboards](https://web.archive.org/web/20200930185217/http://www.verticalkeyboards.com/keyboardoptions/microtonalkeyboards/index.html)\)
* Grid keyboard \([Linnstrument](https://www.rogerlinndesign.com/linnstrument)\)
* Isomorphic keyboard \([Lumatone](https://www.lumatone.io/)\)
* [Tuning Lattices](https://en.wikipedia.org/wiki/Lattice_(music))

Most synthesizers and plugins do not support polyphonic pitch bends and do not
keep track of multiple instances of the same note with different pitch bends.
For this reason it is necessary to use a separate track and instance of the plugin
for each voice. 

The file pycrotuner_environment.logicx.zip is a Logic Pro template for use with this application.
Unzip it in $HOME/Music/Audio Music Apps/Project Templates. It contains the following:
* One External Instrument track for input
* 16 retuned output tracks, each running a different instance of a simple instrument
* One reference pitch bend output track
* MIDI Environment that intercepts the input, routes output voices to 16 instrument tracks, and routes the reference to the reference track

Usage: In Audio MIDI Setup, enable the IAC driver, and add a port named 'retuner'. 

Tip: To easily modify parameters across all 16 retuned tracks, shift-click to select all 16 tracks, then make a change to one track's synth or plugins. Or, cmd-alt-drag a plugin from one track to each of the others to copy its settings.

This application is being developed and tested on MacOS Catalina with Logic Pro 10.6. It
depends on the following packages:
* wxpython
* mido
* python-rtmidi
* pycairo

