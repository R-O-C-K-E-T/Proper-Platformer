import math, string
import tkinter as tk
from tkinter import ttk
import numpy as np

from idlelib.percolator import Percolator
from idlelib.colorizer import ColorDelegator
from idlelib.statusbar import MultiStatusBar

import shared
import util

class TextWindow(tk.Frame):
    def __init__(self, master, initial='', width=90, **kwargs):
        super().__init__(master, **kwargs)

        self.text = text = tk.Text(self, name='text', padx=5, wrap='none', width=width, undo=True)
        vbar = tk.Scrollbar(self, name='vbar')
        vbar['command'] = text.yview
        vbar.pack(side=tk.LEFT, fill=tk.Y)
        text['yscrollcommand'] = vbar.set

        self.status_bar = MultiStatusBar(self)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        text.insert(tk.END, initial)
        text.edit_reset()
        text.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        Percolator(text).insertfilter(ColorDelegator())

        self.text.bind("<<set-line-and-column>>", self.set_line_and_column)
        self.text.event_add("<<set-line-and-column>>",
                            "<KeyRelease>", "<ButtonRelease>")
        self.text.after_idle(self.set_line_and_column)

    IDENTCHARS = string.ascii_letters + string.digits + "_"
    def check_syntax(self):
        try:
            compile(self.get_content(), '<string>', 'exec')
            return
        except (SyntaxError, OverflowError, ValueError) as value:
            msg = getattr(value, 'msg', '') or value or "<no detail available>"
            lineno = getattr(value, 'lineno', '') or 1
            offset = getattr(value, 'offset', '') or 0
            if offset == 0:
                lineno += 1  #mark end of offending line
            pos = "0.0 + %d lines + %d chars" % (lineno-1, offset-1)

            self.text.tag_add("ERROR", pos)
            char = self.text.get(pos)
            if char and char in self.IDENTCHARS:
                self.text.tag_add("ERROR", pos + " wordstart", pos)
            if '\n' == self.text.get(pos):   # error at line end
                self.text.mark_set("insert", pos)
            else:
                self.text.mark_set("insert", pos + "+1c")
            self.text.see(pos)

            return msg

    def set_line_and_column(self, event=None):
        line, column = self.text.index(tk.INSERT).split('.')
        self.status_bar.set_label('column', 'Col: %s' % column, side=tk.RIGHT)
        self.status_bar.set_label('line', 'Ln: %s' % line, side=tk.RIGHT)

    def get_content(self):
        return self.text.get("1.0",tk.END)


class ColourPicker(tk.Toplevel):
    def __init__(self, initial_colour=(255,255,255)):
        super().__init__()
        self.size = 150

        self.resizable(False, False)
        self.title('Colour Picker')
        self.attributes('-topmost', True)

        self.canvas = tk.Canvas(self, width=self.size + 20, height=self.size + 12, bg='white')
        self.canvas.bind('<B1-Motion>', self.move)
        self.canvas.bind('<Button-1>', self.click)
        self.canvas.bind('<ButtonRelease-1>', self.release)

        def try_close():
            self.colour = None
            self.destroy()
        self.protocol("WM_DELETE_WINDOW", try_close)

        self.img = tk.PhotoImage(width=self.size, height=self.size)
        self.canvas.create_image((0,0), anchor=tk.NW, image=self.img, state="normal")

        self._base_wheel = np.array([
            [
            util.HSVtoRGB(math.atan2(y,x)/math.pi/2, math.sqrt(x**2+y**2) / self.size*2, 1) if x**2+y**2 <= self.size*self.size/4 else (-1,-1,-1) for x in range(-self.size//2, self.size//2)
            ] for y in range(-self.size//2, self.size//2)])
        self._format_str = ' '.join('{' + ' '.join('#%02x%02x%02x' for _ in range(self.size)) + '}' for _ in range(self.size))

        self.canvas.create_line(self.size+10, 10, self.size+10, self.size-10, width=5, capstyle=tk.ROUND, fill=util.convert_colour((100,100,100)))

        self.canvas.grid(row=0, column=0, columnspan=2)

        self.cursors = [None]*2

        self.rgb_controls = [tk.StringVar() for i in range(3)]
        self.hsv_controls = [tk.StringVar() for i in range(3)]
        def updateHSV(*_):
            if self.selected is not None:
                return
            try:
                new_colour = [float(channel.get()) for channel in self.rgb_controls]
            except ValueError:
                return
            if min(new_colour) < 0 or max(new_colour) > 1:
                return

            new_colour = util.RGBtoHSV(*new_colour)
            self.selected = 3
            for channel, val in zip(self.hsv_controls, new_colour):
                channel.set(round(val, 2))
            self.selected = None
            self.update_cursors(new_colour)

        def updateRGB(*_):
            if self.selected is not None:
                return
            try:
                new_colour = [float(channel.get()) for channel in self.hsv_controls]
            except ValueError:
                return
            if min(new_colour) < 0 or max(new_colour) > 1:
                return

            self.selected = 3
            for channel, val in zip(self.rgb_controls, util.HSVtoRGB(*new_colour)):
                channel.set(round(val, 2))
            self.selected = None
            self.update_cursors(new_colour)

        for i, rgb, hsv in zip(range(3), self.rgb_controls, self.hsv_controls):
            tk.Spinbox(self,from_=0,to=1,increment=0.1,width=8, textvariable=rgb).grid(row=i+1,column=0, sticky='e')
            tk.Spinbox(self,from_=0,to=1,increment=0.1,width=8, textvariable=hsv).grid(row=i+1,column=1, sticky='w')

            rgb.trace('w', updateHSV)
            hsv.trace('w', updateRGB)

        tk.Button(self, text='Select', command=self.destroy).grid(row=4,column=0,columnspan=2)

        self.selected = None

        self.update_all(util.RGBtoHSV(*np.divide(initial_colour,255)))

    def click(self, e):
        if abs(e.x-self.size-10) <= 7 and 10 <= e.y <= self.size-10:
            self.selected = 0
        elif (e.x-self.size/2)**2 + (e.y-self.size/2)**2 <= (self.size/2)**2:
            self.selected = 1
        else:
            self.selected = None
            return
        self.move(e)

    def release(self, e):
        self.selected = None

    def move(self, e):
        pos = np.array([e.x, e.y],dtype=float)
        centred = pos-self.size/2
        new_colour = self.colour.copy()
        if self.selected == 0:
            self.canvas.delete(self.cursors[1])
            pos[1] = max(10,min(pos[1],self.size-10))
            self.move_cursor(1, self.size+10, pos[1])
            val = 1 - (pos[1]-10) / (self.size-20)
            self.refresh(val)

            new_colour[2] = val
        elif self.selected == 1:
            sat = util.length(centred) / self.size * 2

            if sat > 1:
                self.move_cursor(0, *(centred*(1/sat) + self.size/2))
            else:
                self.move_cursor(0, *pos)

            new_colour[0] = (math.atan2(centred[1], centred[0]) / math.pi / 2) % 1
            new_colour[1] = min(sat, 1)
        else:
            return
        self.update_textboxes(new_colour)

    def create_line(self, col):
        self.canvas.create_line(10, self.size+5, self.size+10, self.size+5, width=9, capstyle=tk.ROUND, fill=util.convert_colour((col*255).astype(int)))

    def update_all(self, col):
        rgb = util.HSVtoRGB(*col)

        for spinbox, val in zip(self.hsv_controls + self.rgb_controls, [*col, *rgb]):
            spinbox.set(round(val, 2))
        self.create_line(rgb)

        self.canvas.delete(self.cursors[0])
        self.canvas.delete(self.cursors[1])
        self.move_cursor(0, *(util.rotate([col[1]*self.size/2,0], col[0]*2*math.pi) + self.size/2))
        self.move_cursor(1, self.size+10, (1-col[2])*(self.size-20)+10)

        self.refresh(col[2])

        self.colour = list(col)

    def update_textboxes(self, col):
        rgb = util.HSVtoRGB(*col)
        self.create_line(rgb)
        for spinbox, val in zip(self.hsv_controls + self.rgb_controls, col + list(rgb)):
            spinbox.set(round(val, 2))
        self.colour = list(col)

    def update_cursors(self, col):
        self.move_cursor(0, *(util.rotate([col[1]*self.size/2,0], col[0]*2*math.pi) + self.size/2))
        self.move_cursor(1, self.size+10, (1-col[2])*(self.size-20)+10)

        self.create_line(util.HSVtoRGB(*col))

        self.refresh(col[2])

        self.colour = list(col)


    def refresh(self, val):
        adjusted = (self._base_wheel*255*val).astype(int)
        adjusted[self._base_wheel < 0] = 255
        self.img.put(self._format_str % tuple(adjusted.reshape(-1)))

    def move_cursor(self, i, x, y):
        radius = 5
        if self.cursors[i] is not None:
            self.canvas.delete(self.cursors[i])
        self.cursors[i] = self.canvas.create_oval((x-radius, y-radius, x+radius, y+radius), width=2, outline='#101010')

def open_picker(callback):
    def func():
        if shared.colour_picker is None:
            class CustomPicker(ColourPicker): # Yeet
                def destroy(self):
                    if shared.colour_picker.colour is not None:
                        callback(*shared.colour_picker.colour)
                    shared.colour_picker = None
                    super().destroy()
            shared.colour_picker = CustomPicker(shared.selected_colour)
    return func

def pick_colour(initial_colour=(255,255,255)): # returns HSV
    picker = ColourPicker(initial_colour)
    picker.wait_window()
    return picker.colour

class Editor:
    def __init__(self, target, location, *args, **kwargs):
        self.target = target
        self.location = location
        super().__init__(*args, **kwargs)

    def set_target(self, val):
        target = self.target
        for key in self.location[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[self.location[-1]] = val


class PropertyEntry(Editor, tk.Entry):
    def __init__(self, master, target, location, parser, **kwargs):
        self.parser = parser

        def validator(string):
            try:
                self.parser(string)
                return True
            except:
                return False
        command = shared.root.register(validator)

        self.var = tk.StringVar()
        super().__init__(target, location, master, textvariable=self.var, validate='key',
                         validatecommand=(command, '%P'), **kwargs)

        self.var.trace('w', self.update)

    def update(self, *args):
        val = self.var.get()
        try:
            parsed = self.parser(val)
        except:
            return

        self.set_target(parsed)


class BoolProperty(Editor, ttk.Combobox):
    def __init__(self, master, target, location, **kwargs):
        self.master = master
        self.var = tk.StringVar()
        super().__init__(target, location, master, textvariable=self.var, values=[
            'True', 'False'], width=6, state='readonly', **kwargs)
        self.bind('<<ComboboxSelected>>', self.selected)

    def selected(self, e):
        val = self.var.get()
        if val == 'True':
            boolean_val = True
        elif val == 'False':
            boolean_val = False
        else:
            return
        self.set_target(boolean_val)

class ColourProperty(Editor, tk.Button):
    def __init__(self, master, target, location):
        super().__init__(target, location, master, command=open_picker(self.set_colour))

    def set_colour(self, *col):
        rgb = (util.HSVtoRGB(*col)*255).astype(int)
        self['bg'] = util.convert_colour(rgb)
        self['activebackground'] = util.convert_colour((rgb*(15/16)).astype(int))
        self.set_target(rgb.tolist())

class ParentProperty(BoolProperty):
    def __init__(self, master, target, location, subnodes, **kwargs):
        self.subnodes = subnodes
        self.values = []
        for node in subnodes:
            self.set_node_target(node)
        super().__init__(master, target, location, **kwargs)
        self.update_subnodes()

    def set_node_target(self, node):
        i = len(self.values)
        self.values.append(None)
        original = node.set_target
        def func(val):
            original(val)
            self.values[i] = val
        node.set_target = func

    def set_target(self, val):
        if val:
            for node, val in zip(self.subnodes, self.values):
                if val is not None:
                    node.set_target(val)
        else:
            super().set_target(None)
        self.update_subnodes()

    def update_subnodes(self):
        state = 'normal' if self.var.get() == 'True' else 'disabled'
        for node in self.subnodes:
            node['state'] = state

class ScrolledList(tk.Frame):
    def __init__(self, master, width, height):
        super().__init__(master, relief='sunken', borderwidth=1)

        self.canvas = tk.Canvas(self)
        self.canvas.pack(side='left', fill='y')
        self.canvas.configure(scrollregion=self.canvas.bbox("all"), width=width, height=height)

        scrollbar = tk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.frame = tk.Frame(self.canvas)
        self.canvas.create_window((0,0),window=self.frame, anchor='nw', width=width)

        self.frame.bind("<Configure>", self.update_scrollbar)

    def update_scrollbar(self, *_):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def insert(self, widget, **settings):
        settings = settings.copy()
        settings['in'] = self.frame
        widget.master = self.frame
        widget.pack(**settings)

    def get_children(self):
        return [child for child in self.winfo_children() if child.master == self.frame]
