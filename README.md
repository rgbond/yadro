# yadro

Yet another DRO for Linuxcnc. Big letters, touch-screen or mouse-only friendly.
Looks like a standard machinist's dro and provides similar functionality in a
linuxcnc environment.

Invoke with "yadro.py coord" where coord is the list of axes. Example:

    yadro XYZ

When it starts, yadro creates an input hal pin for each of the axes. For the above
example, yadro will create these hal pins:

    yadro.0
    yadro.1
    yadro.2

I hook them up to halui like this:

    loadusr -W /home/rgb/src/dro/yadro.py XYZ
    net cposx halui.axis.x.pos-relative => yadro.0
    net cposy halui.axis.y.pos-relative => yadro.1
    net cposz halui.axis.z.pos-relative => yadro.2

If you don't use a python3 build you will want to change the #! statment on line 1.

See screenshot.png for a screenshot.
