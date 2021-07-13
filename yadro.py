#!/usr/bin/python3

from __future__ import print_function
import sys
if sys.version_info[0] == 2:
    from Tkinter import *
else:
    from tkinter import *
import argparse
import time
import linuxcnc
import hal

root = Tk()

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
        
    def send_mdi(self, s):
        if params["verbose"]:
            print("send_mdi:", s)
        self.s.poll()
        if (not self.s.estop and
            self.s.enabled > 0 and
            self.s.homed and
            (self.s.interp_state == linuxcnc.INTERP_IDLE)):
            if not self.s.task_mode == linuxcnc.MODE_MDI:
                self.c.mode(linuxcnc.MODE_MDI)
                self.c.wait_complete()
            self.c.mdi(s)
        else:
            print("can't send", s)
        
    def get_g5x_index(self):
        self.s.poll()
        if params["verbose"]:
            print("g5x_index:", self.s.g5x_index)
            print("g5x_offset:", self.s.g5x_offset)
            print("g92_offset:", self.s.g92_offset)
        return self.s.g5x_index

    def get_pins(self):
        pins = [self.h[str(p)] for p in range(params['naxes'])]
        if params["verbose"]:
            print("pins:", pins)
        return pins

    def set_enable(self, on):
        self.s.poll()
        if (self.s.enabled > 0) == on:
            return
        if on:
            self.s.state(linuxcnc.STATE_ON)
        else:
            self.s.state(linuxcnc.STATE_OFF)

# One of these for each DRO row
class axis_row_gui():
    def __init__(self, frame, row, text, callback):
        px = 10
        self.row = row
        self.text = text
        self.value = StringVar()
        self.value.set(params["inch_format"].format(0.0))
        self.callback = callback
        self.title = Label(frame, justify=RIGHT, anchor=E, text=text, font=params["font1"])
        self.title.grid(row=row, column=0, columnspan=1, sticky=W)
        self.vlabel = Label(frame, width=10, justify=RIGHT, anchor=E,
                            textvariable=self.value, font=params["font1"])
        self.vlabel.grid(row=row, column=1, columnspan=1, sticky=W)
        self.zero = Button(frame, text="Z", font=params["font2"])
        self.zero.bind("<ButtonRelease-1>", lambda event: self.zero_up(event))
        self.zero.grid(row=row, column=2, columnspan=1, padx=px, sticky=W)
        self.half = Button(frame, text="1/2", font=params["font2"])
        self.half.bind("<ButtonRelease-1>", lambda event: self.half_up(event))
        self.half.grid(row=row, column=3, columnspan=1, padx=px, sticky=W)
        self.entry = Entry(frame, width=10, justify=RIGHT, font=params["font1"])
        self.entry.bind("<Return>", lambda event: self.enter_hit())
        self.entry.grid(row=row, column=4, columnspan=1, sticky=W, padx=px)

    def enter_hit(self):
        if params["verbose"]:
            print("enter_hit")
        self.callback(self.row, float(self.entry.get()))
        self.entry.delete(0, END)

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

class keypad_gui():
    def __init__(self, frame, callback):
        self.kp_var = StringVar()
        self.callback = callback
        rows = (7,8,9), (4,5,6), (1,2,3) 
        for row, values in enumerate(rows):
            for col, n in enumerate(values):
                self.add_kp_button(frame, str(n), row, col, 1)
        self.add_kp_button(frame, '0', 3, 0, 2)
        self.add_kp_button(frame, '.', 3, 2, 1)

    def add_kp_button(self, frame, b, row, col, cw):
        px = 5
        rb = Radiobutton(frame, text=b, variable=self.kp_var, value=b, width=4,
                         indicatoron=0, command=lambda: self.kp_hit(),
                         font=params["font1"])
        rb.grid(row=row, column=col, columnspan=cw, padx=px)

    def kp_hit(self):
        print("kp_hit", self.kp_var.get())
        self.callback(self.kp_var.get())
        self.kp_var.set("")

class main_gui():
    def __init__(self, lcnc):
        self.lcnc = lcnc

        px = 5
        py = 15

        root.title("yadro")
        self.f1 = Frame(root)
        self.row_info = dict()

        for row, name in enumerate(params["axes"]):
            self.row_info[row] = axis_row_gui(self.f1, row, name, self.entry_callback)
        self.f1.grid(row=0, column=0, padx=px, pady=py)

        self.f2 = Frame(root)
        self.keypad = keypad_gui(self.f2, self.keypad_callback)
        self.f2.grid(row=1, column=0, padx=px, pady=py)

        self.f3 = Frame(root)
        self.rb_var = IntVar()
        self.rb_var.set(lcnc.get_g5x_index()-1)
        self.coord_sys = ['G54', 'G55', 'G56', 'G57', 'G58', 'G59', 'G59.1', 'G59.2', 'G59.3']
        for col, cs in enumerate(self.coord_sys):
            rb = Radiobutton(self.f3, text=cs, variable=self.rb_var, value=col, width=6,
                             indicatoron=0, command=lambda: self.rb_callback(),
                             font=params["font2"])
            rb.grid(row=0, column=col, columnspan=1, padx=px)
        self.f3.grid(row=2, column=0, padx=px, pady=py)

    def entry_callback(self, row, value):
        if params["verbose"]:
            print("Entry callback", row, value)
        axis_name = self.row_info[row].text
        self.lcnc.send_mdi("G10 L20 P{} {}{}".format(row, axis_name, value))
        # self.row_info[row].set_value(value)

    def rb_callback(self):
        if params["verbose"]:
            print("rb_callback", self.rb_var.get())
        self.lcnc.send_mdi(self.coord_sys[self.rb_var.get()])

    def keypad_callback(self, key):
        print("keypad_callback", key)

    def poll(self):
        self.rb_var.set(self.lcnc.get_g5x_index()-1)
        pins = self.lcnc.get_pins()
        for i in range(len(pins)):
            self.row_info[i].set_value(pins[i])

def call_polls():
    global gui
    gui.poll()
    root.after(100, call_polls);

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', dest='verbose', action="store_true",
                        help='set verbose mode')
    parser.add_argument("axes", type=str, help="Axes (ex: XYZ)")

    args = parser.parse_args()

    axes = list(args.axes)

    params = {}
    params["naxes"] = len(axes)
    params["axes"] = axes
    params["verbose"] = args.verbose
    params["font1"] = ("Helvetica", 20)
    params["font2"] = ("Helvetica", 10)
    params["inch_format"] = "{:.4f}"

    lcnc = lc()
    gui = main_gui(lcnc)

    root.after(20, call_polls);
    root.mainloop()
