#!/usr/bin/python3
#
# Copyright 2021 Robert Bond
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#


from __future__ import print_function
import sys
if sys.version_info[0] == 2:
    import Tkinter as tk
else:
    import tkinter as tk
import argparse
import time
import linuxcnc
import hal

root = tk.Tk()

# Linux cnc interface
class lc():
    def __init__(self):
        try:
            self.s = linuxcnc.stat()
            self.s.poll()
            self.c = linuxcnc.command()
            self.h = hal.component("yadro")
            for p in range(params['naxes']):
                self.h.newpin(str(p), hal.HAL_FLOAT, hal.HAL_IN)
            self.h.ready()
        except:
            exit(1)

    def poll(self):
        self.s.poll()

    def is_homed(self):
        mask = 0
        for i in range(len(self.s.homed)):
            mask |= (self.s.homed[i] << i)
        return mask == self.s.axis_mask

    def is_running(self):
        rv = (not self.s.estop and
              self.s.task_state == linuxcnc.STATE_ON and
              self.is_homed() and
              (self.s.interp_state == linuxcnc.INTERP_IDLE))
        return rv

    def send_mdi(self, s):
        if params["verbose"]:
            print("send_mdi:", s)
        if self.is_running():
            if not self.s.task_mode == linuxcnc.MODE_MDI:
                self.c.mode(linuxcnc.MODE_MDI)
                self.c.wait_complete()
            self.c.mdi(s)
        else:
            print("can't send", s)

    def get_g5x_index(self):
        if params["very_verbose"]:
            print("g5x_index:", self.s.g5x_index)
        return self.s.g5x_index

    def get_pins(self):
        pins = [self.h[str(p)] for p in range(params['naxes'])]
        if params["very_verbose"]:
            print("pins:", pins)
        return pins

    def get_indicators(self):
        if params["very_verbose"]:
            print("get indicators:", self.s.estop, self.s.homed, self.s.task_state)
        estop = self.s.estop != 0
        homed = self.is_homed()
        enabled = self.s.task_state == linuxcnc.STATE_ON
        return estop, homed, enabled

    def set_enable(self, on):
        if params["verbose"]:
            print("set_enable:", on)
        if (self.s.enabled > 0) == on:
            return
        if on:
            self.c.state(linuxcnc.STATE_ON)
        else:
            self.c.state(linuxcnc.STATE_OFF)

# One of these for each DRO row
class axis_row_gui():
    def __init__(self, frame, row, text, callback):
        px = 10
        self.row = row
        self.text = text
        self.value = tk.StringVar()
        self.value.set(params["inch_format"].format(0.0))
        self.callback = callback
        self.title = tk.Label(frame, justify=tk.RIGHT, anchor=tk.E, text=text, font=params["font1"])
        self.title.grid(row=row, column=0, columnspan=1, sticky=tk.W)
        self.vlabel = tk.Label(frame, width=10, justify=tk.RIGHT, anchor=tk.E,
                            textvariable=self.value, font=params["font1"])
        self.vlabel.grid(row=row, column=1, columnspan=1, sticky=tk.W)
        self.zero = tk.Button(frame, text="Z", font=params["font2"])
        self.zero.bind("<ButtonRelease-1>", lambda event: self.zero_up(event))
        self.zero.grid(row=row, column=2, columnspan=1, padx=px, sticky=tk.W)
        self.half = tk.Button(frame, text="1/2", font=params["font2"])
        self.half.bind("<ButtonRelease-1>", lambda event: self.half_up(event))
        self.half.grid(row=row, column=3, columnspan=1, padx=px, sticky=tk.W)
        self.entry = tk.Entry(frame, width=10, justify=tk.RIGHT, font=params["font1"], bg='light gray')
        self.entry.bind("<Return>", lambda event: self.enter_hit())
        self.entry.bind("<ButtonPress-1>", lambda event: self.enter_clicked())
        self.entry.grid(row=row, column=4, columnspan=1, sticky=tk.W, padx=px)
        self.disable_entry()

    def enter_hit(self):
        if params["verbose"]:
            print("enter_hit")
        try:
            v = float(self.entry.get())
        except:
            print('\a')
            return
        self.callback(self.row, v)
        self.entry.delete(0, tk.END)

    def enter_clicked(self):
        if params["verbose"]:
            print("enter_clicked")
        self.callback(self.row, None)

    def zero_up(self, event):
        if params["verbose"]:
            print("zero_up")
        self.callback(self.row, 0.0)

    def half_up(self, event):
        if params["verbose"]:
            print("half_up")
        self.callback(self.row, float(self.value.get())/2.0)

    def set_value(self, v):
        self.value.set(params["inch_format"].format(v))

    def kp_entry(self, key):
        if key == 'E':
            self.enter_hit()
            return
        if key == 'C':
            self.entry.delete(0, tk.END)
            return
        if key == '<':
            s = self.entry.get()
            self.entry.delete(0, tk.END)
            self.entry.insert(tk.END, s[:-1])
            return
        self.entry.insert(tk.END, key)

    def disable_entry(self):
        self.entry.config(state=tk.DISABLED)

    def enable_entry(self):
        self.entry.config(state=tk.NORMAL)

# The keypad
class keypad_gui():
    def __init__(self, frame, callback):
        self.kp_var = tk.StringVar()
        self.callback = callback
        rows = (('7','8','9'), ('4','5','6'),
                ('1','2','3'), ('0','.','-'),
                ('C','<','E'))
        px = 5
        for row, values in enumerate(rows):
            for col, c in enumerate(values):
                rb = tk.Radiobutton(frame, text=c, variable=self.kp_var, value=c, width=4,
                                 indicatoron=0, command=lambda: self.kp_hit(),
                                 font=params["font1"])
                rb.grid(row=row, column=col, padx=px)

    def kp_hit(self):
        if params["verbose"]:
            print("kp_hit", self.kp_var.get())
        self.callback(self.kp_var.get())
        self.kp_var.set("")

# Misc indicators, enable control
class indicator_gui():
    def __init__(self, frame, callback):
        px = 5
        py = 2
        self.id_var = tk.StringVar()
        self.callback = callback
        self.estop = tk.Label(frame, width=8, text="Estop", font=params["font1"])
        self.estop.grid(row=0, column=0, padx=px, pady=py)
        self.homed = tk.Label(frame, width=8, text="Homed", font=params["font1"])
        self.homed.grid(row=1, column=0, padx=px, pady=py)
        self.enabled = tk.Label(frame, width=8, text="Enabled", font=params["font1"])
        self.enabled.grid(row=2, column=0, padx=px, pady=py)
        self.enable = tk.Button(frame, width=6, text="On/Off", font=params["font1"])
        self.enable.bind("<ButtonRelease-1>", lambda event: self.enable_up(event))
        self.enable.grid(row=3, column=0, padx=px, pady=py)

    def enable_up(self, event):
        if params["verbose"]:
            print("enable_up")
        self.callback()

    def set_colors(self, estop, homed, enabled):
        # print("set_colors")
        estop_color = "green"
        if estop:
            estop_color = "red"
        homed_color = "green"
        if not homed:
            homed_color = "red"
        enabled_color = "green"
        if not enabled:
            enabled_color = "red"
        self.estop.config(bg=estop_color)
        self.homed.config(bg=homed_color)
        self.enabled.config(bg=enabled_color)

# The G5x radio button5
class coord_systems():
    def __init__(self, frame, g5x, callback):
        self.callback = callback
        self.rb_var = tk.IntVar()
        self.rb_var.set(g5x - 1)
        self.coord_sys = ['G54', 'G55', 'G56', 'G57', 'G58', 'G59', 'G59.1', 'G59.2', 'G59.3']
        for col, cs in enumerate(self.coord_sys):
            rb = tk.Radiobutton(frame, text=cs, variable=self.rb_var, value=col, width=6,
                             indicatoron=0, command=lambda: self.rb_hit(),
                             font=params["font2"])
            rb.grid(row=0, column=col, columnspan=1, padx=5)

    def rb_hit(self):
        if params["verbose"]:
            print("rb_hit")
        coord_sys_name = self.coord_sys[self.rb_var.get()]
        self.callback(coord_sys_name)

    def set_g5x_index(self, g5x):
        if params["very_verbose"]:
            print("set_g5x_index", g5x)
        self.rb_var.set(g5x - 1)

class main_gui():
    def __init__(self, lcnc):
        self.lcnc = lcnc

        px = 5
        py = 15

        root.title("yadro")
        self.dro_frame = tk.Frame(root)
        self.axis_row = dict()
        self.last_row = None

        for row, name in enumerate(params["axes"]):
            self.axis_row[row] = axis_row_gui(self.dro_frame, row, name, self.entry_callback)
        self.dro_frame.grid(row=0, column=0, columnspan = 2, padx=px, pady=py, sticky=tk.NW)

        self.keypad_frame = tk.Frame(root)
        self.keypad = keypad_gui(self.keypad_frame, self.keypad_callback)
        self.keypad_frame.grid(row=1, column=0, padx=px, pady=py, sticky=tk.NW)

        self.indicator_frame = tk.Frame(root)
        self.indicators = indicator_gui(self.indicator_frame, self.indicator_callback)
        self.indicator_frame.grid(row=1, column=1, padx = px, pady=py, sticky=tk.N)

        self.coord_frame = tk.Frame(root)
        self.coords = coord_systems(self.coord_frame, lcnc.get_g5x_index(), self.coord_callback)
        self.coord_frame.grid(row=2, column=0, columnspan = 2, padx=px, pady=py, sticky=tk.NW)

        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(1, weight=1)

    def entry_callback(self, row, value):
        if params["verbose"]:
            print("Entry callback", row, value)
        self.lcnc.poll()
        if not self.lcnc.is_running():
            return
        if value is None:
            # just a click
            if not self.last_row is None:
                self.axis_row[self.last_row].entry.config(bg='light gray')
            self.axis_row[row].entry.config(bg='white')
            self.last_row = row
            return
        # Enter
        axis_name = self.axis_row[row].text
        g5x_index = self.lcnc.get_g5x_index()
        self.lcnc.send_mdi("G10 L20 P{} {}{}".format(g5x_index, axis_name, value))
        if not self.last_row is None:
            self.axis_row[self.last_row].entry.config(bg='light gray')
        self.last_row = None
        # self.axis_row[row].set_value(value)

    def coord_callback(self, g5x):
        if params["verbose"]:
            print("coord_callback", g5x)
        self.lcnc.poll()
        if not self.lcnc.is_running():
            return
        self.lcnc.send_mdi(g5x)

    def keypad_callback(self, key):
        if params["verbose"]:
            print("keypad_callback", key)
        self.lcnc.poll()
        if not self.lcnc.is_running():
            return
        if self.last_row is None:
            return
        self.axis_row[self.last_row].kp_entry(key)

    def indicator_callback(self):
        if params["verbose"]:
            print("indicator_callback")
        self.lcnc.poll()
        estop, homed, enabled = self.lcnc.get_indicators()
        if enabled:
            lcnc.set_enable(False)
        else:
            lcnc.set_enable(True)

    def poll(self):
        self.lcnc.poll()
        self.coords.set_g5x_index(self.lcnc.get_g5x_index())
        pins = self.lcnc.get_pins()
        for i in range(len(pins)):
            self.axis_row[i].set_value(pins[i])
        estop, homed, enabled = self.lcnc.get_indicators()
        self.indicators.set_colors(estop, homed, enabled)
        if self.lcnc.is_running():
            for row in range(params["naxes"]):
                self.axis_row[row].enable_entry()
        else:
            for row in range(params["naxes"]):
                self.axis_row[row].disable_entry()

def call_polls():
    global gui
    gui.poll()
    root.after(100, call_polls);

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0,
                    help='print debug info')
    parser.add_argument('--point_size', '-p', dest='point_size', type=int, default=20,
                    help='font point size, default: 20')
    parser.add_argument("axes", type=str, help="Axes (example: XYZ)")

    args = parser.parse_args()

    axes = list(args.axes)

    params = {}
    params["naxes"] = len(axes)
    params["axes"] = axes
    params["verbose"] = False
    params["very_verbose"] = False
    if args.verbose > 0:
        params["verbose"] = True
    if args.verbose > 1:
        params["very_verbose"] = True
    params["font1"] = ("Helvetica", args.point_size)
    params["font2"] = ("Helvetica", int(args.point_size / 2))
    params["inch_format"] = "{:.4f}"

    lcnc = lc()
    gui = main_gui(lcnc)

    root.after(20, call_polls);
    root.mainloop()
