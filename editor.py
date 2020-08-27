#from scipy.ndimage.filters import convolve1d

import json, copy, string, os, time, tempfile, pygame, math, sys
import numpy as np
from pygame.locals import *

from threading import Timer
from functools import partial

import tkinter as tk
from tkinter import filedialog
from tkinter import colorchooser
from tkinter import ttk
from tkinter import messagebox
import tkinter.scrolledtext

import shared, actions, util, safe, widgets, font

DEFAULT_CLIENT_SCRIPT = '''
# This is your client level script.
# This script is only run by clients connected to an online server
# As it is only run on the client it cannot access certain functions such as adding or removing objects
# This script is only intended to be used to aid the client prediction process

# Functions inside this script will be executed based on triggers bound using the level editor, similar to the server script

def onDeath(player): # Called whenever any player dies.
    pass

def load(): # Called when the level is created, note that no objects will be inside the level at this point
    pass

def add_object(obj): # Called whenever an object is added to the world
    pass

def tick(): # Will be called once per tick
    pass
'''

DEFAULT_SERVER_SCRIPT = '''
# This is your server level script.
# Functions inside this script will be executed based on triggers bound using the level editor.

# The below function is a collision trigger, once bound to an object it will be called for each collision the object has.
def handler(self, other, normal, localA, localB):
   #A return value of True cancels the collision so no collision response is applied.
   return other.vel[1] < 0 # This example would allow any physics object (including players) to jump through this object but not fall down through it.

def onDeath(player): # Called whenever any player dies.
    pass

def load(): # Called when the level is created
    pass

def tick(): # Will be called once per tick
    pass
'''

class KeyTracker(dict):
    def __init__(self, widget):
        self.timers = {}
        self.widget = widget

        widget.bind('<KeyPress>', self.on_pressed_repeat)
        widget.bind('<KeyRelease>', self.on_release_repeat)

    def on_release(self, e):
        self[e.keysym_num] = False
        del self.timers[e.keysym_num]

    def on_pressed_repeat(self, e):
        if e.keysym_num in self.timers:
            self.timers.pop(e.keysym_num).cancel()

        self[e.keysym_num] = True

    def on_release_repeat(self, e):
        self.timers[e.keysym_num] = timer = Timer(0.05, self.on_release, [e])
        timer.start()

    def __getitem__(self, key):
        return super().get(key, False)

def loadPressed():
    global current_file
    filename = filedialog.askopenfilename(title='Load Level', filetypes=(
        ('JSON files', '*.json'), ('all files', '*.*')))
    if filename != '':
        shared.level = loadFile(filename)
        actions.set_error(
            'Level with ' + str(len(shared.get_objects())) + ' Objects Loaded')


def savePressed():
    global current_file
    if current_file != '':
        save(current_file)
        actions.set_error('Level saved to\n' + current_file)
    else:
        saveAsPressed()

    shared.level_modified = False


def saveAsPressed():
    global current_file
    filename = filedialog.asksaveasfilename(title='Save Level', defaultextension=".json", filetypes=(
        ('JSON files', '*.json'), ('all files', '*.*')))
    if filename != '':
        save(filename)
        actions.set_error('Level Saved')

    current_file = filename
    shared.level_modified = False


def undoPressed():
    if shared.history_index == -1:
        actions.set_error('Nothing to undo')
        return

    shared.history[shared.history_index].undo()
    shared.history_index -= 1


def redoPressed():
    if shared.history_index == len(shared.history) - 1:
        actions.set_error('Nothing to redo')
        return

    shared.history_index += 1
    shared.history[shared.history_index].redo()



def select(pos):
    global selection
    # Top polygon checked first
    for i, obj in enumerate(shared.get_objects()[::-1]):
        crossings = 0
        for p1, p2 in zip(obj['points'], np.roll(obj['points'], -1, 0)):
            if pos[1] < min(p1[1], p2[1]):
                continue
            if pos[1] > max(p1[1], p2[1]):
                continue
            if p1[1] == p2[1]:
                if pos[1] == p1[1] and pos[0] > min(p1[0], p2[0]):
                    crossings += 1
            elif pos[0] > p1[0] + (pos[1] - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1]):
                crossings += 1
        if crossings % 2 == 1:
            selection = len(shared.get_objects()) - i - 1
            return

def saveToString(pretty):
    level_copy = copy.deepcopy(shared.level)

    for nConstraint, constraint in zip(level_copy['constraints'], shared.level['constraints']):
        a, b = constraint['objects']
        try:
            nConstraint['objects'] = [shared.get_objects().index(
                a), shared.get_objects().index(b)]
        except ValueError:
            nConstraint['objects'] = None

    level_copy['constraints'] = list(filter(
        lambda constraint: constraint['objects'] is not None, level_copy['constraints']))

    if pretty: # calling it pretty is a bit of a stretch
        data = '{\n'
        if len(level_copy) > 1:
            data += '  ' + ',\n  '.join('"{}": '.format(key) + json.dumps(
                level_copy[key]) for key in filter(lambda key: key != 'objects', level_copy)) + ',\n'
        data += '  "objects": [\n    '+',\n    '.join('{\n      ' + ',\n      '.join('"'+name+'": '+json.dumps(
            obj[name]) for name in obj) + '\n    }' for obj in level_copy['objects'])+'\n  ]'
        data += '\n}'
    else:
        data = json.dumps(level_copy)
    return data

def save(level_name):
    data = saveToString(True)
    with open(level_name, 'w') as file:
        file.write(data)

def load(data):
    if len(data) == 0:
        data = '{}'
    level = {'gravity': [0, 0.3], 'spawn': [0, 0], 'constraints': [], 'objects': []}
    level.update(json.loads(data))

    level['objects'] = [actions.add_default_properties(obj) for obj in level['objects']] # Fill in missing props

    # Convert constraints to hard links
    for constraint in level['constraints']:
        i, j = constraint['objects']
        constraint['objects'] = [level['objects'][i], level['objects'][j]]

    #allowScript = False
    if 'script' in shared.level:
        try:
            res = safe.validate(shared.level['script'])
            #allowScript = res is None or showUnsafeScriptDialog()
        except SyntaxError as e:
            actions.set_error('Syntax Error in level script')
            print(e)

    shared.level_modified = False
    shared.selection = []
    shared.joint_selection = []

    shared.history = []
    shared.history_index = -1

    return level

def loadFile(level_name):
    global current_file
    if handleUnsaved():
        return
    current_file = level_name

    with open(level_name, 'rb') as file:
        str = file.read().decode('utf-8')
    return load(str)

def showUnsafeScriptDialog():
    dialog = tk.Toplevel()
    dialog.title('Unsafe Script')
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Fuck you

    inner = tk.Frame(dialog)
    inner.pack(padx=5, pady=5)

    tk.Label(inner, text='The level you are trying to load contains a potentially unsafe script',
             wraplength=400, font=(None, 12)).pack()
    tk.Label(inner, text='Only load this level script if you trust the author or have validated the code below.',
             wraplength=400, font=(None, 10)).pack()

    text = tkinter.scrolledtext.ScrolledText(inner, width=80, wrap=tk.NONE)
    text.insert(tk.END, shared.level['script'])
    text['state'] = 'disabled'
    text.pack()

    choices = tk.Frame(inner, width=300)
    choices.pack()

    def cancelLoad():
        nonlocal waiting
        waiting = False

    def allowLoad():
        nonlocal waiting, load
        waiting = False
        load = True

    tk.Button(choices, text='Allow', command=allowLoad).pack(side=tk.LEFT)
    tk.Button(choices, text='Deny', command=cancelLoad).pack(side=tk.RIGHT)

    load = False
    waiting = True
    while waiting:
        time.sleep(0.1)

    dialog.destroy()

    return load

def handleUnsaved():
    if not shared.level_modified:
        return False

    result = messagebox.askyesnocancel('Unsaved Level', 'Do you wish to save?')
    if result is None:
        return True

    if result:
        savePressed()

    return False

def openScript():
    '''fd, filepath = tempfile.mkstemp('.py')
    try:
        with open(filepath, 'w') as f:
            f.write(script)

        util.openWithIDLE(filepath)

        with open(filepath, 'r') as f:
            newScript = f.read()
    finally:
        os.close(fd)
        os.remove(filepath)

    try:
        res = safe.validate(newScript)
        if res is not None:
            actions.set_error(
                'Potentially dangerous operation\n Line:{} Column:{}'.format(*res))
        shared.level_modified = True
    except SyntaxError:
        actions.set_error('Syntax Error')
        return

    if all(char in string.whitespace for char in newScript):
        if location in shared.level:
            del shared.level[location]
    else:
        shared.level[location] = newScript'''

    clientScript = shared.level.get('clientScript', DEFAULT_CLIENT_SCRIPT)
    serverScript = shared.level.get('serverScript', DEFAULT_SERVER_SCRIPT)

    top = tk.Toplevel()
    top.title('Script Editor')
    top.resizable(False, True)

    left_frame = tk.Frame(top)
    tk.Label(left_frame, text='Client Script').pack()
    client_window = widgets.TextWindow(left_frame, clientScript)
    client_window.pack(expand=True, fill=tk.Y)

    right_frame = tk.Frame(top)
    tk.Label(right_frame, text='Server Script').pack()
    server_window = widgets.TextWindow(right_frame, serverScript)
    server_window.pack(expand=True, fill=tk.Y)

    def save():
        error = client_window.check_syntax()
        if error is not None:
            messagebox.showerror('Client InvalidSyntax', error)
            return
        error = server_window.check_syntax()
        if error is not None:
            messagebox.showerror('Client InvalidSyntax', error)
            return

        new_client = client_window.get_content()
        if all(char in string.whitespace for char in new_client):
            if 'clientScript' in shared.level:
                del shared.level['clientScript']
        else:
            shared.level['clientScript'] = new_client

        new_server = server_window.get_content()
        if all(char in string.whitespace for char in new_server):
            if 'serverScript' in shared.level:
                del shared.level['serverScript']
        else:
            shared.level['serverScript'] = new_server
        shared.level_modified = True
        top.destroy()
    tk.Button(left_frame, text='Save', command=save).pack(side=tk.RIGHT)

    def cancel():
        top.destroy()
    tk.Button(right_frame, text='Cancel', command=cancel).pack(side=tk.LEFT)

    left_frame.pack(expand=True, fill=tk.Y, side=tk.LEFT)
    right_frame.pack(expand=True, fill=tk.Y, side=tk.RIGHT)

    top.wait_window()

class God:
    def __init__(self, screen):
        self.controls = [[K_d, K_a], [K_s, K_w]]
        #self.pressed = pressed
        self.pos = np.array(shared.level['spawn'], dtype=int)
        self.current_action = None
        self.screen = screen

    def update(self):
        pressed = pygame.key.get_pressed()
        delta = np.array([pressed[a] - pressed[b] for a, b in self.controls])
        self.pos += delta * 5 * (1 + 3*pressed[K_LSHIFT])
        #print(self.pos)

    def getCursorPosition(self):
        return self.pos + np.array(pygame.mouse.get_pos()) - np.array(self.screen.get_size()) // 2

    def drawCircle(self, pos, size, colour, outline=(1,(0,0,0))):
        screenPos = pos - self.pos + np.floor_divide(self.screen.get_size(), 2)
        if colour is not None:
            pygame.draw.circle(self.screen, colour, screenPos, size)
        if outline is not None:
            rect = pygame.Rect(tuple(screenPos-size), (size*2,size*2))
            pygame.draw.arc(self.screen, outline[1], rect, 0, 2*math.pi, outline[0])
            #pygame.draw.circle(self.screen, outline[1], screenPos, size, outline[0])

    def drawPolygon(self, points, colour, outline=(1,(0,0,0))):
        screen_points = (points - (self.pos - np.floor_divide(self.screen.get_size(), 2))).astype(int)
        if colour is not None:
            pygame.draw.polygon(self.screen, colour, screen_points)
        if outline is not None:
            pygame.draw.polygon(self.screen, outline[1], screen_points, outline[0])

    def drawLine(self, a, b, colour=(0,0,0), width=1):
        offset = self.pos - np.floor_divide(self.screen.get_size(), 2)
        pygame.draw.line(self.screen, colour, a - offset, b - offset, width)

    def drawObject(self, obj, outline=(1,(0,0,0))):
        if obj['type'] == 'polygon':
            self.drawPolygon(obj['points'], obj['colour'], outline)
        elif obj['type'] == 'circle':
            self.drawCircle(obj['pos'], obj['radius'], obj['colour'], outline)
        elif obj['type'] == 'text':
            character = font.createCharacter(obj['char'], obj['size'])

            offset = character.offset + obj['pos'] - self.pos + np.floor_divide(self.screen.get_size(), 2)
            for tri in character.triangles:
                pygame.draw.polygon(self.screen, obj['colour'], (np.array(tri) + offset).astype(int))


            for loop in character.loops:
                for a, b in zip(loop, np.roll(loop, 1, 0)):
                    pygame.draw.line(self.screen, outline[1], (a + offset).astype(int), (b + offset).astype(int), outline[0])

SHORTCUTS = {K_t: actions.Translate, K_f: actions.Select, K_r: actions.Rotate, K_c: actions.Duplicate, K_DELETE: actions.Delete}

def run(initialFile):
    shared.root = root = tk.Tk()
    inner = tk.Frame(root, name='innerFrame')
    inner.pack(padx=5, pady=(0, 5), side='left', anchor='n')

    ttk.Separator(root, orient=tk.VERTICAL).pack(side='left', fill='y')

    saveload = tk.Frame(inner)
    saveload.grid(row=0)
    # tk.Label(saveload,text='Save/Load').grid(row=0,column=0,columnspan=3)
    tk.Frame(saveload, height=5).grid(row=0, columnspan=3)
    tk.Button(saveload, text='Save', command=savePressed).grid(row=1, column=0)
    tk.Button(saveload, text='Save As',
              command=saveAsPressed).grid(row=1, column=1)
    tk.Button(saveload, text='Load', command=loadPressed).grid(row=1, column=2)

    ttk.Separator(inner, orient=tk.HORIZONTAL).grid(row=1, sticky='ew', pady=5)

    general = tk.Frame(inner)
    general.grid(row=2)
    tk.Button(general, text='Select', command=actions.set_action(
        actions.Select)).grid(row=0, column=0, columnspan=2, sticky='ew')
    tk.Button(general, text='Undo', command=undoPressed).grid(row=1, column=0)
    tk.Button(general, text='Redo', command=redoPressed).grid(row=1, column=1)

    def changeColour(*hsv):
        rgb = (util.HSVtoRGB(*hsv)*255).astype(int)
        shared.selected_colour = rgb.tolist()
        shared.colour_button['bg'] = util.convertColour(rgb)
        shared.colour_button['activebackground'] = util.convertColour((rgb*(15/16)).astype(int))

    shared.colour_button = tk.Button(general, command=widgets.openPicker(changeColour))
    shared.colour_button.grid(row=2, column=0, columnspan=2, ipadx=10)
    shared.colour_button['bg'] = util.convertColour(shared.selected_colour)
    shared.colour_button['activebackground'] = util.convertColour(np.multiply(shared.selected_colour, 15/16).astype(int))
    ttk.Separator(inner, orient=tk.HORIZONTAL).grid(row=3, sticky='ew', pady=5)

    create = tk.Frame(inner)
    create.grid(row=4)
    tk.Label(create, text='Create').grid(row=0, column=0, columnspan=2)
    tk.Button(create, text='Polygon',
              command=actions.polygonPressed).grid(row=1, column=0)
    tk.Button(create, text='Rectangle', command=actions.set_action(
        actions.Rectangle)).grid(row=1, column=1)
    tk.Button(create, text='NGon', command=actions.set_action(
        actions.NGon)).grid(row=2, column=0)
    tk.Button(create, text='Circle', command=actions.set_action(
        actions.Circle)).grid(row=2, column=1)
    tk.Button(create, text='Text', command=actions.set_action(actions.Text)).grid(row=3,column=0)

    ttk.Separator(inner, orient=tk.HORIZONTAL).grid(row=5, sticky='ew', pady=5)

    modify = tk.Frame(inner)
    modify.grid(row=6)
    tk.Label(modify, text='Modify').grid(row=0, column=0, columnspan=2)
    tk.Button(modify, text='Rotate', command=actions.set_action(
        actions.Rotate)).grid(row=1, column=0, sticky='ew')
    tk.Button(modify, text='Translate', command=actions.set_action(
        actions.Translate)).grid(row=1, column=1, sticky='ew')
    tk.Button(modify, text='Smooth', command=actions.set_action(
        actions.Smooth)).grid(row=2, column=0, sticky='ew')
    tk.Button(modify, text='Edit', command=actions.set_action(
        actions.Edit)).grid(row=2, column=1, sticky='ew')
    tk.Button(modify, text='Delete', command=actions.set_action(
        actions.Delete)).grid(row=3, column=0, sticky='ew')
    tk.Button(modify, text='Duplicate', command=actions.set_action(
        actions.Duplicate)).grid(row=3, column=1, sticky='ew')
    tk.Button(modify, text='Properties', command=actions.set_action(
        actions.Properties)).grid(row=4, column=0, columnspan=2)

    ttk.Separator(inner, orient=tk.HORIZONTAL).grid(row=7, sticky='ew', pady=5)

    joints = tk.Frame(inner)
    joints.grid(row=8)
    tk.Label(joints, text='Joints').grid(row=0, column=0, columnspan=2)

    tk.Button(joints, text='Pivot', command=actions.set_action(
        actions.AddPivot)).grid(row=1, column=0)
    tk.Button(joints, text='Fixed', command=actions.set_action(
        actions.AddFixed)).grid(row=1, column=1)
    tk.Button(joints, text='Delete', command=actions.set_action(actions.RemoveJoint)).grid(row=2, column=0)

    ttk.Separator(inner, orient=tk.HORIZONTAL).grid(row=9, sticky='ew', pady=5)

    globalProps = tk.Frame(inner)
    globalProps.grid(row=10)
    tk.Label(globalProps, text='Script').grid(row=0, column=0, columnspan=2)

    tk.Button(globalProps, text='Edit', command=openScript).grid(row=1,column=0)
    tk.Button(globalProps, text='Group', command=actions.set_action(actions.Group)).grid(row=1, column=1)

    ttk.Separator(inner, orient=tk.HORIZONTAL).grid(
        row=11, sticky='ew', pady=5)

    # Extra section inserted by current_action.

    error = tk.StringVar(name='errorVar')
    tk.Label(inner, textvariable=error, wraplength=180).grid(row=14)

    actions.Smooth.minAngle = tk.StringVar(value=str(actions.Smooth.minAngle)) # Hmmm

    shared.level = loadFile(initialFile)

    root.title('Editor')

    root.update_idletasks()
    root.update()

    def on_closing():
        nonlocal running
        running = False
    root.protocol("WM_DELETE_WINDOW", on_closing)

    if os.name == 'nt': # Embedded pygame window
        root.minsize(800, inner.winfo_height())
        pygameFrame = tk.Frame(root)
        pygameFrame.pack(side='left', expand=True, fill='both')
        os.environ['SDL_WINDOWID'] = str(pygameFrame.winfo_id())
        screen = pygame.display.set_mode(flags=NOFRAME)
    else: # Seperate windows
        root.attributes("-topmost", True)
        size = 1024, 768
        screen = pygame.display.set_mode(size, RESIZABLE)
        pygame.display.set_caption('Editor')

    pygame.font.init()
    positionFont = pygame.font.SysFont(None, 15)

    clock = pygame.time.Clock()

    god = shared.god = God(screen)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                action = SHORTCUTS.get(event.key)
                if action is not None:
                    actions.set_action(action)()
            elif event.type == MOUSEBUTTONDOWN:
                if shared.colour_picker is not None:
                    obj = actions.getObjectAt(god.getCursorPosition())
                    if obj is None:
                        colour = 1,1,1
                    else:
                        colour = np.divide(obj['colour'], 255)
                    shared.colour_picker.updateAll(util.RGBtoHSV(*colour))
                elif god.current_action is not None:
                    #print(event.button)
                    try:
                        god.current_action.click(god.getCursorPosition(), event.button)
                    except actions.StopAction as e:
                        if e.history_entry is not None:
                            shared.history = shared.history[:shared.history_index+1]

                            shared.history.append(e.history_entry)
                            shared.history_index = len(shared.history) - 1
                        god.current_action = None

            elif event.type == VIDEORESIZE: # Only occurs on non embedded pygame
                screen = pygame.display.set_mode(event.size, RESIZABLE)
            elif event.type == QUIT: # Only occurs on non embedded pygame
                running = False
        god.update()

        screen.fill((255,255,255))

        for i, obj in enumerate(shared.level['objects']):
            outline = (2, (0,0,255)) if i in shared.selection else (1, (0,0,0))
            god.drawObject(obj, outline)

        for i, joint in enumerate(shared.level['constraints']):
            outline = (2, (0, 0, 255)) if i in shared.joint_selection else (1, (0, 0, 0))
            if joint['type'] == 'pivot':
                god.drawCircle(joint['pos'], 5, None, outline)
            elif joint['type'] == 'fixed':
                god.drawLine(np.subtract(joint['pos'], (3, 3)), np.add(joint['pos'], (3, 3)), *outline[::-1])
                god.drawLine(np.subtract(joint['pos'], (-3, 3)), np.add(joint['pos'], (-3, 3)), *outline[::-1])

        if god.current_action is not None:
            god.current_action.render()


        pos = god.getCursorPosition()
        renderedPosition = positionFont.render('{:},{:}'.format(*pos), True, (0,0,0,255))
        screenPos = np.add(pygame.mouse.get_pos(), (0, -8))
        screen.blit(renderedPosition, screenPos)

        pygame.display.update()

        root.update_idletasks()
        root.update()

        clock.tick(60)

    root.destroy()
    pygame.quit()

if __name__ == '__main__':
    filename = sys.argv[1]
    run(filename)
    #run('levels/pendulum.json')
