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
# Manual DRO
# Hook this one directly to the dro pins

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
            self.h = hal.component("mdro")
            for p in range(params["naxes"]):
                self.h.newpin(str(p), hal.HAL_FLOAT, hal.HAL_IN)
            self.h.ready()
            if params["verbose"]:
                print("Linuxcnc interface up")
        except:
            print("Linuxcnc interface aborted")
            exit(1)

    def poll(self):
        self.s.poll()

    def get_pins(self):
        pins = [self.h[str(p)] for p in range(params['naxes'])]
        if params["very_verbose"]:
            print("pins:", pins)
        return pins

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

class coord_systems():
    def __init__(self, frame, ncoords, callback):
        self.callback = callback
        self.rb_var = tk.IntVar()
        self.rb_var.set(1)
        self.coord_sys = ['mcs', 'cs1', 'cs2', 'cs3', 'cs4']
        self.coords = []
        for i in range(len(self.coord_sys)):
            self.coords.append([0]*ncoords)
        self.cur_idx = 0
        self.cur_sys = self.coords[self.cur_idx]
        for row, cs in enumerate(self.coord_sys):
            rb = tk.Radiobutton(frame, text=cs, variable=self.rb_var, value=row, width=6,
                     indicatoron=0, command=lambda: self.rb_hit(),
                     font=params["font1"])
            rb.grid(row=row, column=0, columnspan=1, padx=5)

    def rb_hit(self):
        self.cur_idx = self.rb_var.get()
        if params["verbose"]:
            print("rb_hit", self.coord_sys[self.cur_idx])
        self.cur_sys = self.coords[self.cur_idx]
        self.callback(self.cur_idx)

class main_gui():
    def __init__(self, lcnc):
        self.lcnc = lcnc

        px = 5
        py = 15

        root.title("mdro")
        self.dro_frame = tk.Frame(root)
        self.axis_row = dict()
        self.last_row = None

        for row, name in enumerate(params["axes"]):
            self.axis_row[row] = axis_row_gui(self.dro_frame, row, name,
                                              self.entry_callback)
            self.axis_row[row].enable_entry()
        self.dro_frame.grid(row=0, column=0, columnspan=2, padx=px, pady=py, sticky=tk.NW)

        self.keypad_frame = tk.Frame(root)
        self.keypad = keypad_gui(self.keypad_frame, self.keypad_callback)
        self.keypad_frame.grid(row=1, column=0, padx=px, pady=py, sticky=tk.NW)

        self.coord_frame = tk.Frame(root)
        self.coords = coord_systems(self.coord_frame, params["naxes"], self.coord_callback)
        self.coord_frame.grid(row=1, column=1, padx=px, pady=py, sticky=tk.N)

    def entry_callback(self, row, value):
        if params["verbose"]:
            print("Entry callback", row, value)
        if value is None:
            # just a click
            if not self.last_row is None:
                self.axis_row[self.last_row].entry.config(bg='light gray')
            self.axis_row[row].entry.config(bg='white')
            self.last_row = row
            return
        # Enter
        self.lcnc.poll()
        pins = self.lcnc.get_pins()
        # Can't change the mcs entry
        if self.coords.cur_idx != 0:
            self.coords.cur_sys[row] = value - pins[row]
        if not self.last_row is None:
            self.axis_row[self.last_row].entry.config(bg='light gray')
        self.last_row = None

    def coord_callback(self, coord_sys_idx):
        if params["verbose"]:
            print("coord_callback", coord_sys_idx)
        if coord_sys_idx == 0:
            for row in range(params["naxes"]):
                self.axis_row[row].disable_entry()
        else:
            for row in range(params["naxes"]):
                self.axis_row[row].enable_entry()

    def keypad_callback(self, key):
        if params["verbose"]:
            print("keypad_callback", key)
        if self.last_row is None:
            return
        self.axis_row[self.last_row].kp_entry(key)

    def poll(self):
        self.lcnc.poll()
        pins = self.lcnc.get_pins()
        for i in range(len(pins)):
            self.axis_row[i].set_value(pins[i] + self.coords.cur_sys[i])

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
