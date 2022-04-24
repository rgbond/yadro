# yadro

Yadro is yet another DRO for Linuxcnc. Big letters, touch-screen or mouse-only friendly.
Looks like a standard machinist's dro and provides similar functionality in a
Linuxcnc environment, Yadro supports all of the G5x coordinate systems. It works
best with Linuxcnc fully up with the axes homed and enabled.

Mdro is a simpler, manual only dro that is less hooked into Linuxcnc internals. It
should be hooked directly to the machine's dro outputs. It is blissfully unaware
of most of the Linuxcnc state. I use it when running the machine in manual mode
using the hand cranks on the machine.

See screenshot.png for a screenshot.

## yadro invocation

Invoke from your hal file with "yadro.py coord" where coord is the list of axes. Example:

    yadro XYZ

A optional "--point_size" argument changes the default font point size which
adjusts the overall size of the display.

When it starts, yadro creates an input hal pin for each of the axes. For the above
example, yadro will create these hal pins:


    yadro.0
    yadro.1
    yadro.2

If you don't use a python3 build you will want to change the #! statement on line 1.
I hook them up to halui like this:

    loadusr -W /home/rgb/src/dro/yadro.py XYZ
    net cposx halui.axis.x.pos-relative => yadro.0
    net cposy halui.axis.y.pos-relative => yadro.1
    net cposz halui.axis.z.pos-relative => yadro.2

## mdro invocation

Invoke from your hal file with "mdro.py coord" where coord is the list of axes. Example:

    mdro XYZ

An optional "--point_size" argument changes the default font point size which
adjusts the overall size of the display.

An optional "--mm" argument can be used to specify that the dro units are in mm.

When it starts, mdro creates an input hal pin index hal pin for each of the axes.
For the above example, mdro will create these hal pins:

    mdro.axis.0
    mdro.axis.1
    mdro.axis.2

If you don't use a python3 build you will want to change the #! statement on line 1.
I hook them up to halui like this in the non-display case:

    loadusr -W /home/rgb/src/dro/mdro.py XYZ
    net x-pos-fb => mdro.0
    net y-pos-fb => mdro.1
    net z-pos-fb => mdro.2

Mdro can be started from the "DISPLAY" entry in a dedicated .ini file in place of
axis or another GUI. In that case, mdro assumes that it is also handling the index
pulse functions from the DRO and creates the following index-enable entries. 
They should be hooked to the encoder index-enable pins The mdro pins must be
hooked up in a postgui.hal file in this case.

    mdro.index-enable.0
    mdro.index-enable.1
    mdro.index-enable.2

