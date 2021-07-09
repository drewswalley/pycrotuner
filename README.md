# pycrotuner
MIDI microtuner - Live MIDI input transformer for microtonal performance and composition

Note: This project is not yet ready for release or contributions.

Pycrotuner is a graphical application for performing and composing microtonal music. It
reads Scala .scl scale files and .kbm keyboard map files to map input MIDI notes to
output notes and pitch bend messages.  Pycrotuner supports 16-part polyphony and an arbitrary
number of scales and mappings.  It can switch tunings and parameters on the fly by keying
off of MIDI notes and messages as specified in its main configuration file. If no MIDI
controller is available, notes may be played with the computer keyboard or mouse. Different
computer keyboard types are available:
* Standard piano keyboard
* Grid keyboard \([Linnstrument]https://www.rogerlinndesign.com/linnstrument)\)
* Isomorphic keyboard \(Lumatone]\(https://www.lumatone.io/\)
* 


This software is being developed and tested on MacOS Catalina with Logic Pro 10.6. It
depends on the following packages:
* wxpython
* mido
* python-rtmidi
* pycairo
