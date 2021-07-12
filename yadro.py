#!/usr/bin/python3

from __future__ import print_function
from tkinter import *
import argparse
import time
import linuxcnc

root = Tk()

# Linux cnc interface
class lc():
    def __init__(self):
        try:
            self.s = linuxcnc.stat()
            self.s.poll()
        except:
            exit(1)
        self.g5x_index = getattr(self.s, "g5x_index")
        self.c = linuxcnc.command()
        
    def send_mdi(self, s):
        print("send_mdi:", s)
        self.s.poll()
        if (not self.s.estop and
            self.s.enabled and
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
        # print("get_g5x_index:", self.s.g5x_index)
        return self.s.g5x_index

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
        print("enter_hit")
        self.callback(self.row, float(self.entry.get()))
        self.entry.delete(0, END)

    def zero_up(self, event):
        print("zero_up")
        self.callback(self.row, 0.0)

    def half_up(self, event):
        print("half_up")
        self.callback(self.row, float(self.value.get())/2.0)

    def set_value(self, v):
        self.value.set(params["inch_format"].format(v))

class main_gui():
    def __init__(self, lcnc):
        self.lcnc = lcnc

        px = 5

        root.title("yadro")
        self.f1 = Frame(root)
        self.f1.pack(padx=15, pady=15)
        self.row_info = dict()

        for row, name in enumerate(params["axes"]):
            self.row_info[row] = axis_row_gui(self.f1, row, name, self.entry_callback)

        self.f2 = Frame(root)
        self.f2.pack(padx=15, pady=15)
        self.rb_var = IntVar()
        self.rb_var.set(lcnc.get_g5x_index()-1)
        self.coord_sys = ['G54', 'G55', 'G56', 'G57', 'G58', 'G59', 'G59.1', 'G59.2', 'G59.3']
        for col, cs in enumerate(self.coord_sys):
            rb = Radiobutton(self.f2, text=cs, variable=self.rb_var, value=col, width=6,
                             indicatoron=0, command=lambda: self.rb_callback(),
                             font=params["font2"])
            rb.grid(row=0, column=col, columnspan=1, padx=px)

    def entry_callback(self, row, value):
        print("Entry callback", row, value)
        axis_name = self.row_info[row].text
        self.lcnc.send_mdi("G10 L20 P{} {}{}".format(row, axis_name, value))
        # self.row_info[row].set_value(value)

    def rb_callback(self):
        print("rb_callback", self.rb_var.get())
        self.lcnc.send_mdi(self.coord_sys[self.rb_var.get()])

    def poll(self):
        self.rb_var.set(lcnc.get_g5x_index()-1)
        return
        self.row_info[0].set_value(str(0.0))
        self.row_info[1].set_value(str(1.0))
        self.row_info[2].set_value(str(1.0))

def call_polls():
    global gui
    gui.poll()
    root.after(100, call_polls);

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', dest='verbose', type=int,
                        help='set verbose mode')
    parser.add_argument("axes", type=str, help="Axes (ex: XYZ)")

    args = parser.parse_args()

    axes = list(args.axes)

    params = {}
    params["naxis"] = len(axes)
    params["axes"] = axes
    params["verbose"] = args.verbose
    params["font1"] = ("Helvetica", 30)
    params["font2"] = ("Helvetica", 15)
    params["inch_format"] = "{:.4f}"

    lcnc = lc()
    gui = main_gui(lcnc)

    root.after(20, call_polls);
    root.mainloop()
