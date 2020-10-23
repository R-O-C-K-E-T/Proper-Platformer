#!/usr/bin/python3
import json, os.path, pygame, subprocess, sys
import pygame.locals as pg_locals
from functools import partial
import numpy as np
import tkinter as tk
from glob import glob

from tkinter import colorchooser
from tkinter import messagebox
from tkinter.simpledialog import askinteger

import util, font

key_map = dict((getattr(pg_locals, name), name[2:]) for name in dir(pg_locals) if name.startswith('K_'))

def create_preview(filename):
    with open(filename) as f:
        level = json.load(f)
    scale = 1/10

    size = np.array([140,100])
    screen = pygame.Surface(size)
    screen.fill((255,255,255))
    centre = np.array(level.get('spawn', (0,0))) - size / 2 / scale

    for obj in level['objects']:
        colour = obj['colour']
        if obj['type'] == 'circle':
            pos = (obj['pos'] - centre) * scale
            pygame.draw.circle(screen, colour, pos.astype(int), round(obj['radius'] * scale))
        elif obj['type'] == 'polygon':
            points = [((pos - centre) * scale).astype(int) for pos in obj['points']]
            pygame.draw.polygon(screen, colour, points)
        elif obj['type'] == 'text':
            drawn = font.create_character(obj['char'], obj['size'] * scale)

            offset = drawn.offset + (obj['pos'] - centre) * scale
            for tri in drawn.triangles:
                pygame.draw.polygon(screen, colour, (np.array(tri) + offset).astype(int))

    image = tk.PhotoImage()
    for x in range(size[0]):
        for y in range(size[1]):
            colour = screen.get_at((x,y))[:3]
            image.put(util.convert_colour(colour), to=(x,y))
    return image


class ScrolledList(tk.Frame):
    def __init__(self, master, width, height, **kwargs):
        super().__init__(master, **kwargs)

        canvas = tk.Canvas(self)
        canvas.pack(side='left', fill='y')
        canvas.configure(scrollregion=canvas.bbox("all"), width=width, height=height)

        def update(command, y):
            assert command == 'moveto'
            y = max(0,min(1,float(y)))
            canvas.yview(command, y)
        scrollbar = tk.Scrollbar(self, orient='vertical', command=update)
        scrollbar.pack(side='right', fill='y')

        canvas.configure(yscrollcommand=scrollbar.set)

        self.frame = tk.Frame(canvas)
        #self.frame['bg'] = 'red'
        canvas.create_window((0,0), window=self.frame, anchor='nw', width=width)

        self.frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def insert(self, widget, **settings):
        settings = settings.copy()
        settings['in'] = self.frame
        widget.pack(**settings)

class SelectableFrame(tk.Frame):
    def __init__(self, master, command=lambda: None, **options):
        super().__init__(master, relief='raised', borderwidth=1, **options)
        self.command = command
        self.bind('<Button-1>', self.onclick)
        self.bind('<ButtonRelease-1>', self.onrelease)

    def bind_children(self):
        def bind(widget):
            widget.bind('<Button-1>', self.onclick)
            widget.bind('<ButtonRelease-1>', self.onrelease)
            for child in widget.children.values():
                bind(child)
        bind(self)

    def onclick(self, e):
        self['relief'] = 'sunken'
        self.command()

    def onrelease(self, e):
        self['relief'] = 'raised'

class LevelSelectorElement(SelectableFrame):
    def __init__(self, master, filename, set_selection):
        super().__init__(master, width=100, command=self.select)
        self.set_selection = set_selection
        self.filename = filename
        name, _ = os.path.splitext(os.path.basename(filename))
        self.imgLabel = tk.Label(self, image=BLANK_PHOTO)
        self.imgLabel.pack(pady=(2,0))
        self.label = tk.Label(self, text=name)
        self.label.pack()

        self.bind_children()

    def select(self):
        self['bg'] = self.label['bg'] = '#2222ff'
        self.set_selection(self)

    def unselect(self):
        self['bg'] = self.label['bg'] = util.convert_colour((240, 240, 237))

    def load_preview(self):
        try:
            self.image = create_preview(self.filename)
            self.imgLabel['image'] = self.image
        except:
            pass


class LevelSelector(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        scrolled = ScrolledList(self, 450, 300, borderwidth=1, relief='sunken')
        self.items = tk.Frame(scrolled, width=450)
        #self.items['bg'] = 'green'
        for i in range(3):
            self.items.columnconfigure(i, minsize=150)

        scrolled.insert(self.items)
        scrolled.pack()

        self.selection = None
        self.selectors = []

        self.refresh(False)

    def refresh(self, immediate=True):
        for widget in self.selectors:
            widget.grid_forget()
        self.selectors = []
        for i, filename in enumerate(sorted(glob('levels/*.json'))):
            x = i % 3
            y = i // 3

            widget = LevelSelectorElement(self.items, filename, self.set_selection)
            widget.grid(column=x, row=y, sticky='nsew', padx=1, pady=1)
            self.selectors.append(widget)

        tk.Button(self.items, text='Refresh', command=self.refresh, justify='left').grid(column=0, row=y + 1, sticky='w')

        self.selectors[0].select()

        iterator = iter(self.selectors)
        def show_next():
            try:
                widget = next(iterator)
            except StopIteration:
                return
            widget.load_preview()
            self.after_idle(show_next)

        root.update()
        root.update_idletasks()

        if immediate:
            self.after_idle(show_next)
        else:
            self.after(500, show_next)

    def set_selection(self, widget):
        if self.selection is not None and self.selection is not widget:
            self.selection.unselect()
        self.selection = widget

class Menu(tk.Frame):
    def __init__(self):
        super().__init__(root, padx=10, pady=10)

class CreateGame(Menu):
    def __init__(self):
        super().__init__()
        tk.Label(self, text='Create Game', font=h2).pack()

        self.selector = LevelSelector(self)
        self.selector.pack()

        footer = tk.Frame(self)
        footer.pack()

        tk.Button(footer, text='Local Game', command=self.play_local).pack(side='left')
        tk.Button(footer, text='Online Game', command=self.play_online).pack(side='left')

        tk.Button(self, text='Back', command=pop_stack).pack()

    def play_local(self):
        filename = self.selector.selection.filename

        root.withdraw()
        subprocess.run([sys.executable, 'main.py', 'local', filename])
        root.deiconify()

    def play_online(self):
        filename = self.selector.selection.filename
        port = askinteger('Port Selection', 'Enter Port', minvalue=0)
        if port is None:
            return
        root.withdraw()

        server_process = subprocess.Popen([sys.executable, 'main.py', 'server', filename, str(port)])
        subprocess.run([sys.executable, 'main.py', 'client', 'localhost', str(port)])
        server_process.terminate() # TODO Make more graceful
        #server_process.send_signal(signal.SIGQUIT)

        root.deiconify()

class JoinGame(Menu):
    def __init__(self):
        super().__init__()
        tk.Label(self, text='Join Game', font=h2).grid(row=0,column=0,columnspan=2)

        self.address = tk.StringVar()
        self.port = tk.StringVar()

        tk.Label(self, text='Address:').grid(row=1,column=0,sticky='e')
        tk.Entry(self, textvariable=self.address, width=15).grid(row=1,column=1,sticky='w')

        tk.Label(self, text='Port:').grid(row=2,column=0,sticky='e')
        tk.Entry(self, textvariable=self.port, width=15).grid(row=2,column=1,sticky='w')

        footer = tk.Frame(self)
        tk.Button(footer, text='Join', command=self.join).grid(row=0,column=0, sticky='e')
        tk.Button(footer, text='Back', command=pop_stack).grid(row=0,column=1, sticky='w')
        footer.grid(row=3,column=0,columnspan=2)

    def join(self):
        address = self.address.get()
        if len(address) == 0:
            messagebox.showerror("Error", "Invalid Address")
            return

        try:
            port = int(self.port.get())
            if port < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid Port")
            return

        root.withdraw()
        subprocess.run([sys.executable, 'main.py', 'client', address, str(port)])
        root.deiconify()

class LevelEditor(Menu):
    def __init__(self):
        super().__init__()
        tk.Label(self, text='Level Editor', font=h2).pack()
        self.selector = LevelSelector(self)
        self.selector.pack()
        footer = tk.Frame(self)
        tk.Button(footer, text='Edit', command=self.edit).grid(row=0,column=0)
        tk.Button(footer, text='Back', command=pop_stack).grid(row=0,column=1)
        footer.pack()

    def edit(self):
        filename = self.selector.selection.filename

        root.withdraw()
        subprocess.run([sys.executable, 'editor.py', filename])
        root.deiconify()

def get_key():
    screen = pygame.display.set_mode((200,100))
    pygame.display.set_caption('Press Key')
    screen.fill((255,255,255))
    pygame.font.init() # Module is uninitialised when we quit
    font = pygame.font.SysFont(None, 50)
    text = font.render('Press Key', True, (0,0,0))
    screen.blit(text, (100-text.get_width()//2,50-text.get_height()//2,))
    clock = pygame.time.Clock()
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pg_locals.QUIT:
                    return None
                elif event.type == pg_locals.KEYDOWN:
                    return event.key
            pygame.display.update()
            clock.tick(60)
    finally:
        pygame.quit()

class EditPlayer(Menu):
    def __init__(self, callback, player=None):
        super().__init__()
        new = player is None
        if new:
            player = {'name': '', 'active':True, 'colour': [255,0,0], 'controls': [None]*4}

        tk.Label(self, text=('Create' if new else 'Modify')+' Player', font=h2).grid(row=0,column=0,columnspan=2)

        self.callback = callback
        self.active = player['active']

        tk.Label(self, text='Name:').grid(row=1, column=0)
        self.name_var = tk.StringVar(value=player['name'])
        tk.Entry(self, textvariable=self.name_var, width=15).grid(row=1,column=1)

        tk.Label(self, text='Colour:').grid(row=2,column=0)
        self.colour_button = tk.Button(self, command=self.update_colour, bg=util.convert_colour(player['colour']), activebackground=util.convert_colour((np.array(player['colour']) * 0.9).astype(int)))
        self.colour_button.grid(row=2,column=1, sticky='ew')

        keys = tk.Frame(self)
        for i in range(3):
            keys.grid_columnconfigure(i, minsize=40)
        for i in range(2):
            keys.grid_rowconfigure(i, minsize=40)

        self.buttons = [tk.Button(keys,command=partial(self.update_key, i)) for i in range(4)]
        self.buttons[0].grid(row=1,column=2,sticky='nsew')
        self.buttons[2].grid(row=1,column=1,sticky='nsew')
        self.buttons[1].grid(row=1,column=0,sticky='nsew')
        self.buttons[3].grid(row=0,column=1,sticky='nsew')

        self.controls = player['controls'].copy()

        for key, button in zip(self.controls, self.buttons):
            try:
                code = getattr(pg_locals, 'K_' + key)
                button['text'] = pygame.key.name(code)
            except:
                button['text'] = 'Unknown Key'

        keys.grid(row=3,column=0,columnspan=2)

        footer = tk.Frame(self)
        tk.Button(footer, text='Save', command=self.save_player).pack(side='left')
        tk.Button(footer, text='Cancel', command=pop_stack).pack(side='left')
        footer.grid(row=4,column=0,columnspan=2)

    def update_key(self, index):
        val = get_key()
        if val is None:
            return
        self.controls[index] = key_map[val]
        self.buttons[index]['text'] = pygame.key.name(val)

    def update_colour(self):
        res, _ = colorchooser.askcolor(self.colour_button['bg'])
        if res is None:
            return
        res = np.array(res)
        self.colour_button['bg'] = util.convert_colour(res.astype(int))
        self.colour_button['activebackground'] = util.convert_colour((res * 0.9).astype(int))

    def save_player(self):
        player = {}
        player['active'] = self.active
        player['name'] = self.name_var.get()
        col = self.colour_button['bg']
        player['colour'] = [int(col[i:i+2],16) for i in range(1,7,2)]
        player['controls'] = self.controls
        self.callback(player)
        pop_stack()

class Options(Menu):
    def __init__(self):
        super().__init__()
        self.vars = [] # Unused, but necessary

        tk.Label(self, text='Profile Editor', font=h2).grid(row=0,column=0,columnspan=2)

        scrolled_list = ScrolledList(self, 250, 250, borderwidth=1, relief='sunken')
        scrolled_list.grid(row=1,column=0,columnspan=2, padx=1)
        self.list = tk.Frame(scrolled_list)
        self.list.columnconfigure(0, minsize=250)
        #self.list['bg'] = 'yellow'
        scrolled_list.insert(self.list, fill='x')
        scrolled_list.insert(tk.Button(scrolled_list, text='New', command=self.add_player))
        with open('settings.json') as f:
            settings = json.load(f)

        self.players = settings.get('players', [])
        for i, player in enumerate(self.players):
            entry = self.generate_list_entry(player)
            entry.grid(row=i, column=0, sticky='ew', pady=1, padx=1)

        tk.Label(self, text='Multisamples:').grid(row=2,column=0, sticky='e')

        self.multisample_var = tk.StringVar(value=str(settings.get('multisampling', 0)))
        self.fancy_var = tk.BooleanVar(value=settings.get('fancy', True))

        tk.Entry(self, textvariable=self.multisample_var, width=3).grid(row=2,column=1, sticky='w')

        tk.Label(self, text='Fancy:').grid(row=3, column=0, sticky='e')
        tk.Checkbutton(self, variable=self.fancy_var).grid(row=3, column=1, sticky='w')

        tk.Button(self, text='Save', command=self.update_profiles).grid(row=4,column=0)
        tk.Button(self, text='Exit', command=pop_stack).grid(row=4,column=1)

    def generate_list_entry(self, player):
        var = tk.StringVar(value=int(player['active']))
        def onchange(*_):
            value = bool(int(var.get()))
            player['active'] = value
        var.trace("w", onchange)
        self.vars.append(var) # Nice garbage collection

        entry = tk.Frame(self.list, borderwidth=1, relief='raised')
        #entry['bg'] = 'green'
        tk.Label(entry, text=player['name'], anchor='w', width=10, font=body).pack(side='left')
        tk.Frame(entry, width=25, height=15, bg=util.convert_colour(player['colour']), highlightthickness=1, highlightbackground='black').pack(side='left')
        tk.Checkbutton(entry, variable=var).pack(side='left')
        tk.Button(entry, text='Del', command=partial(self.remove_player, player), padx=3, pady=3).pack(side='right', padx=2, pady=2)
        tk.Button(entry, text='Edit', command=partial(self.modify_entry, player), padx=3, pady=3).pack(side='right', padx=2, pady=2)
        return entry

    def add_player(self):
        def apply(player):
            self.players.append(player)
            _, i = self.list.grid_size()
            self.generate_list_entry(player).grid(row=i, column=0, sticky='ew', padx=1, pady=1)

        push_stack(EditPlayer(apply))

    def remove_player(self, old_plyaer):
        index = self.players.index(old_plyaer)
        self.players.pop(index)
        widget = self.list.grid_slaves(row=index, column=0)[0]
        for i in range(index+1, len(self.players)):
            self.list.grid_slaves(row=i, column=0)[0].grid(row=i-1, column=0)
        widget.grid_forget()

    def modify_entry(self, old_plyaer):
        def apply(player):
            i = self.players.index(old_plyaer)
            self.players[i] = player
            self.list.grid_slaves(row=i, column=0)[0].grid_forget()
            self.generate_list_entry(player).grid(row=i, column=0, sticky='ew', padx=1, pady=1)

        push_stack(EditPlayer(apply, old_plyaer))

    def update_profiles(self):
        with open('settings.json') as f:
            settings = json.load(f)
        settings['players'] = self.players
        try:
            value = int(self.multisample_var.get())
            if value >= 1:
                settings['multisampling'] = value
        except ValueError:
            pass
        settings['fancy'] = self.fancy_var.get()
        with open('settings.json', 'w') as f:
            json.dump(settings, f)
        pop_stack()

class MainMenu(Menu):
    def __init__(self):
        super().__init__()
        tk.Label(self, text='Proper Platformer', font=h1).pack()
        entries = [
           ('Create Game', CreateGame),
           ('Join Multiplayer', JoinGame),
           ('Level Editor', LevelEditor),
           ('Options', Options),
        ]
        for label, clz in entries:
            widget = clz()
            tk.Button(self, text=label, width=15, font=body, command=partial(push_stack, widget)).pack()


def push_stack(widget):
    widget.update()
    width, height = widget.winfo_reqwidth(), widget.winfo_reqheight()
    widget.place(width=width,height=height)
    root.geometry('{}x{}'.format(width,height))
    stack.append(widget)

def pop_stack():
    widget = stack.pop()
    widget.place_forget()

    shown = stack[-1]
    width, height = shown.winfo_reqwidth(), shown.winfo_reqheight()
    root.geometry('{}x{}'.format(width,height))

if __name__ == '__main__':
    pygame.display.init()

    h1 = None, 15
    h2 = None, 13

    body = None, 11

    stack = []

    root = tk.Tk()
    root.resizable(False, False)
    root.title('Game')

    BLANK_PHOTO = tk.PhotoImage()
    BLANK_PHOTO.put(('{' + 'white '*140 + '} ')*100)

    menu = MainMenu()
    push_stack(menu)

    root.mainloop()
