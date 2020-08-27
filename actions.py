import copy, math, re, threading, pygame
from pygame.locals import *
import tkinter as tk
import numpy as np
from scipy.ndimage.filters import convolve1d
from tkinter import ttk
from tkinter import colorchooser
from tkinter import simpledialog

import shared, widgets, util, font
from shared import get_objects
from util import genBounds, genNormals, convertColour, lineIntersection, length2

class StopAction(Exception):
    def __init__(self, history_entry=None):
        self.history_entry = history_entry

class Action:
    def __init__(self, ignore_constraints=False):
        if len(shared.selection) == 0:
            set_error('Select some objects to start')
            raise StopAction

        # selection must always be sorted (highest to lowest)
        self.objects = [get_objects()[i] for i in shared.selection][::-1]
        self.adjusted = [copy.deepcopy(obj) for obj in self.objects]

        self.constraints = [shared.level['constraints'][i] for i in shared.joint_selection][::-1]

        if ignore_constraints:
            self.adjusted_constraints = None
        else:
            for constraint in shared.level['constraints']:
                objA, objB = constraint['objects']
                if (objA in self.objects) != (objB in self.objects):
                    set_error('Cannot start action: hanging constraints exist in current selection')
                    raise StopAction

            self.adjusted_constraints = []
            for constraint in self.constraints:
                new_constraint = constraint.copy()
                del new_constraint['objects']
                new_constraint = copy.deepcopy(new_constraint)
                new_constraint['objects'] = [self.adjusted[self.objects.index(obj)] for obj in constraint['objects']]
                self.adjusted_constraints.append(new_constraint)

        for i in shared.selection:
            get_objects().pop(i)
        for i in shared.joint_selection:
            shared.level['constraints'].pop(i)

        self.selection_snapshot = shared.selection.copy()
        self.joint_selection_snapshot = shared.joint_selection.copy()
        shared.selection = []
        shared.joint_selection = []

        set_error('Action started')

    def render(self):
        for obj in self.adjusted:
            shared.god.drawObject(obj)

        constraints = self.adjusted_constraints
        if constraints is None:
            constraints = self.constraints

        for joint in constraints:
            if joint['type'] == 'pivot':
                shared.god.drawCircle(joint['pos'], 5, None)
            elif joint['type'] == 'fixed':
                shared.god.drawLine(np.subtract(
                    joint['pos'], (3, 3)), np.add(joint['pos'], (3, 3)))
                shared.god.drawLine(np.subtract(
                    joint['pos'], (-3, 3)), np.add(joint['pos'], (-3, 3)))

    def click(self, pos, button):
        if button == BUTTON_RIGHT:
            self.cancel()
            raise StopAction
        elif button == BUTTON_LEFT:
            self.apply()
            raise StopAction(self)

    def undo(self):
        shared.level['objects'] = get_objects()[:-len(self.adjusted)]
        for i, obj in zip(self.selection_snapshot, self.objects):
            get_objects().insert(i, obj)

        if self.adjusted_constraints is None:
            shared.level['constraints'] = shared.level['constraints'][:-len(self.constraints)]
        else:
            shared.level['constraints'] = shared.level['constraints'][:-len(self.adjusted_constraints)]

        for i, constraint in zip(self.joint_selection_snapshot, self.constraints):
            shared.level['constraints'].insert(i, constraint)

    def redo(self):
        for i in self.selection_snapshot:
            get_objects().pop(i)
        shared.level['objects'] += self.adjusted

        for i in self.joint_selection_snapshot:
            shared.level['constraints'].pop(i)

        if self.adjusted_constraints is None:
            adjusted_constraints = copy.deepcopy(self.constraints, dict((id(obj), adjusted) for obj, adjusted in zip(self.objects, self.adjusted)))
        else:
            adjusted_constraints = self.adjusted_constraints

        shared.level['constraints'] += adjusted_constraints

    def cancel(self):
        if self.objects is not None:
            for i, obj in zip(reversed(self.selection_snapshot), reversed(self.objects)):
                get_objects().insert(i, obj)
            for i, constraint in zip(reversed(self.joint_selection_snapshot), reversed(self.constraints)):
                shared.level['constraints'].insert(i, constraint)
            insert()
            shared.selection = self.selection_snapshot
            shared.joint_selection = self.joint_selection_snapshot
        set_error('Cancelled')

    def apply(self):
        shared.level['objects'] += self.adjusted

        if self.adjusted_constraints is None:
            adjusted_constraints = copy.deepcopy(self.constraints, dict((id(obj), adjusted) for obj, adjusted in zip(self.objects, self.adjusted)))
        else:
            adjusted_constraints = self.adjusted_constraints
        shared.level['constraints'] += adjusted_constraints

        set_error('Finished')
        shared.selection = list(
            reversed(range(len(get_objects())-len(self.adjusted), len(get_objects()))))

        shared.joint_selection = list(reversed(range(len(shared.level['constraints'])-len(adjusted_constraints), len(shared.level['constraints']))))

        insert()
        shared.level_modified = True

class Group:
    class GroupElement(tk.Frame):
        def __init__(self, master, name, action):
            super().__init__(master)
            self.action = action
            self.name = name
            self.members = []
            self.label = tk.Label(self, text=name)
            self.label.grid(row=0,column=0, sticky='ew')
            self.label.bind('<Button-1>', self.click)
            self.bind('<Button-1>', self.click)
            tk.Button(self, text='Delete', command=self.destroy).grid(row=0,column=1, sticky='e')

        def click(self, e):
            if self is self.action.selected:
                self.action.select(None)
            else:
                self.select()

        def select(self):
            self.label['bg'] = self['bg'] = '#909090'
            self.action.select(self)

        def unselect(self):
            self.label['bg'] = self['bg'] = '#d9d9d9'

        def destroy(self):
            if self.action.selected is self:
                self.action.select(None)
            super().destroy()

    def __init__(self):
        self.selected = None

        frame = tk.Frame(get_inner())
        insert(frame)

        self.list = widgets.ScrolledList(frame, 150, 200)
        self.list.pack()

        tk.Button(frame, text='Apply', command=applyWrapper(self.apply)).pack(side='left')
        tk.Button(frame, text='Cancel', command=cancel_action).pack(side='left')
        tk.Button(frame, text='Add', command=self.makeGroup).pack(side='right')

        groups = {}
        for i, obj in enumerate(shared.get_objects()):
            for group in obj['groups']:
                if group not in groups:
                    groups[group] = []
                groups[group].append(i)

        for key, val in groups.items():
            element = Group.GroupElement(self.list, key, self)
            element.members = sorted(val, reverse=True)
            self.list.insert(element)

        self.list.updateScrollbar()

    def makeGroup(self):
        name = simpledialog.askstring('Enter Name', '')
        if name is None or len(name) == 0 or any(name == child.name for child in self.list.getChildren()):
            return
        element = Group.GroupElement(self.list, name, self)
        element.members = shared.selection.copy()
        self.list.insert(element)
        element.select()

    def select(self, element):
        if self.selected is not None:
            self.selected.unselect()
        self.selected = element
        if element is None:
            shared.selection = shared.selection.copy()
        else:
            shared.selection = element.members

    def click(self, pos, button):
        obj = getObjectAt(pos)

        if obj is None:
            return

        i = get_objects().index(obj)
        try:
            shared.selection.remove(i)
        except ValueError:
            shared.selection.append(i)
            shared.selection.sort(reverse=True)

    def apply(self):
        groups = [[] for _ in range(len(shared.get_objects()))]
        for element in self.list.getChildren():
            for member in element.members:
                groups[member].append(element.name)

        for newGroups, obj in zip(groups, shared.get_objects()):
            obj['groups'] = newGroups
        insert()

    def render(self):
        pass

    def cancel(self):
        insert()

class Rotate(Action):
    def __init__(self):
        super().__init__()
        self.centre = sum(np.sum(obj['points'], 0) / len(obj['points']) if obj['type'] == 'polygon' else np.array(obj['pos'])
                          for obj in self.adjusted) / len(self.adjusted)

        self.startAngle = math.atan2(*self.centre - shared.god.getCursorPosition())

        frame = tk.Frame(get_inner())
        insert(frame)

        def check(text):
            if text == '-' or text == '':
                return True
            try:
                int(text)
                return True
            except:
                return False
        validate = shared.root.register(check), '%P'
        tk.Label(frame, text='Angle:').grid(row=0, column=0)
        self.angle = tk.StringVar(value='0')
        tk.Entry(frame, textvariable=self.angle, width=3, validate='key',
                 validatecommand=validate).grid(row=0, column=1)

        tk.Button(frame, text='Done', command=applyWrapper(
            self.apply)).grid(row=1, column=0, columnspan=2)

        set_error('Click to finalise rotation')

    def render(self):
        if get_cursor_focus():
            a = math.atan2(
                *(self.centre - shared.god.getCursorPosition())) - self.startAngle
            self.angle.set(str(int(math.degrees(a))))
        else:
            a = math.radians(util.tryDefault(lambda: int(self.angle.get()), 0))

        rot = np.array([[math.cos(a), -math.sin(a)],
                        [math.sin(a), math.cos(a)]], float)

        for old, new in zip(self.objects, self.adjusted):
            if new['type'] == 'polygon':
                new['points'] = np.array(
                    [((point - self.centre) @ rot) + self.centre for point in old['points']], int)
            elif new['type'] in ('circle', 'text'):
                new['pos'] = (old['pos'] - self.centre) @ rot + self.centre

        for old, new in zip(self.constraints, self.adjusted_constraints):
            new['pos'] = ((old['pos'] - self.centre) @ rot + self.centre).astype(int)

        super().render()

    def apply(self):
        for obj in self.adjusted:
            if obj['type'] == 'polygon':
                obj['points'] = obj['points'].tolist()
            elif obj['type'] == 'circle':
                obj['pos'] = obj['pos'].tolist()
        for constraint in self.adjusted_constraints:
            constraint['pos'] = constraint['pos'].tolist()
        super().apply()


class Translate(Action):
    def __init__(self):
        super().__init__()

        self.centre = sum(np.sum(obj['points'], 0) / len(obj['points']) if obj['type'] ==
                          'polygon' else np.array(obj['pos']) for obj in self.adjusted) / len(self.adjusted)

        frame = tk.Frame(get_inner())
        insert(frame)

        def check(text):
            if text == '-' or text == '':
                return True
            try:
                int(text)
                return True
            except:
                return False
        validate = shared.root.register(check), '%P'
        tk.Label(frame, text='X:').grid(row=0, column=0)
        self.strPos = tk.StringVar(value='0'), tk.StringVar(value='0')
        tk.Entry(frame, textvariable=self.strPos[0], width=5, validate='key', validatecommand=validate).grid(
            row=0, column=1)

        tk.Label(frame, text='Y:').grid(row=1, column=0)
        tk.Entry(frame, textvariable=self.strPos[1], width=5, validate='key', validatecommand=validate).grid(
            row=1, column=1)

        tk.Button(frame, text='Done', command=applyWrapper(
            self.apply)).grid(row=2, column=0, columnspan=2)

        #getError().set('Click to finalise translation')

    def render(self):
        if get_cursor_focus():
            delta = (shared.god.getCursorPosition() - self.centre).astype(int)
            [t.set(str(v)) for v, t in zip(delta, self.strPos)]
        else:
            delta = np.array([util.tryDefault(lambda: int(var.get()), 0)
                              for var in self.strPos], dtype=int)
        for old, new in zip(self.objects, self.adjusted):
            if old['type'] == 'polygon':
                new['points'] = old['points'] + delta
            elif old['type'] in ('circle', 'text'):
                new['pos'] = old['pos'] + delta

        for old, new in zip(self.constraints, self.adjusted_constraints):
            new['pos'] = old['pos'] + delta
        super().render()

    def apply(self):
        for obj in self.adjusted:
            if obj['type'] == 'polygon':
                obj['points'] = obj['points'].astype(int).tolist()
            elif obj['type'] in ('circle', 'text'):
                obj['pos'] = obj['pos'].astype(int).tolist()
        for constraint in self.adjusted_constraints:
            constraint['pos'] = constraint['pos'].astype(int).tolist()
        super().apply()


class Delete(Action):
    def __init__(self):
        super().__init__()
        raise StopAction(self)

    def undo(self):
        for i, obj in zip(reversed(self.selection_snapshot), reversed(self.objects)):
            shared.level['objects'].insert(i, obj)
        shared.selection = self.selection_snapshot

    def redo(self):
        for i in self.selection_snapshot:
            del shared.level['objects'][i]
        shared.selection = []



class Smooth(Action):
    rule = 1, 2, 1
    minAngle = 120  # replaced by stringvar

    def __init__(self):
        if any(shared.level['objects'][i]['type'] != 'polygon' for i in shared.selection):
            set_error('Smoothing can only be applied to polygons')
            raise StopAction()
        super().__init__()

        frame = tk.Frame(get_inner())
        insert(frame)
        tk.Label(frame, text='Min Angle:').grid(row=0, column=0)

        def checkAngle(text):
            if all(c in '0123456789' for c in text):
                if text == '':
                    Smooth.minAngle.set('0')
                    frame.after_idle(lambda: entry.config(validate='key'))
                elif int(text) > 180:
                    Smooth.minAngle.set('180')
                    frame.after_idle(lambda: entry.config(validate='key'))
                frame.after_idle(self.subdivide)
                return True
            else:
                return False

        entry = tk.Entry(frame, textvariable=Smooth.minAngle, width=3,
                         validate='key', validatecommand=(shared.root.register(checkAngle), '%P'))
        entry.grid(row=0, column=1)

        self.rule = Smooth.rule
        self.subdivide()

    def subdivide(self):
        val = util.tryDefault(lambda: int(Smooth.minAngle.get()), 0)
        if int(val) > 180:
            minAngle = math.pi
        else:
            minAngle = math.radians(int(val))

        for obj, newObj in zip(self.objects, self.adjusted):
            points = obj['points']
            splits = []
            for i, (p1, p2, p3) in enumerate(zip(np.roll(points, -1, 0), points, np.roll(points, 1, 0))):
                a = math.atan2(*(p1-p2)[::-1])
                b = math.atan2(*(p3-p2)[::-1])
                angle = a-b
                angle = abs(angle)
                angle = [angle, 2*math.pi-angle][angle > math.pi]
                #angle += [0, 2*math.pi][angle<0]
                if angle < minAngle:
                    splits.append(i)
            splits = np.array(splits, int)

            new = convolve1d(points, (1, 1), axis=0, mode='wrap') / 2

            splitShape = np.zeros((len(points) * 2, 2))
            splitShape[1::2, :] = new
            splitShape[0::2, :] = points

            convolved = convolve1d(splitShape, self.rule,
                                   axis=0, mode='wrap') / sum(self.rule)
            #print(type(convolved), convolved, type(points), type(splits))
            convolved[splits * 2] = np.array(points)[splits]

            newObj['points'] = convolved.tolist()

    def apply(self):
        for obj in self.adjusted:
            if obj['type'] == 'polygon':
                obj['points'] = obj['points']
        super().apply()


class Edit(Action):
    def __init__(self):
        super().__init__()
        if len(self.objects) > 1:
            self.cancel()
            set_error('Only 1 polygon can be edited at once')
            raise StopAction()
        if self.objects[0]['type'] == 'circle':
            self.cancel()
            set_error("Circles can't be edited")
            raise StopAction()

        shared.selected_colour = col = self.objects[0]['colour']
        shared.colour_button['bg'] = util.convertColour(col)
        shared.colour_button['activebackground'] = util.convertColour(np.multiply(col, 15/16).astype(int))
        self.selection = None

    def click(self, pos, button):
        adjusted = self.adjusted[0]['points']
        if self.selection is None:
            for i, point in enumerate(adjusted):
                if sum((point-pos)**2) < 5**2:
                    self.selection = i, point.copy()
                    return

            for i, (a, b) in enumerate(zip(adjusted, np.roll(adjusted, 1, 0))):
                if abs(util.distance(a, b, pos)) < 5:
                    self.selection = i, a.copy(), b.tolist().copy()
                    return
        else:
            if button == BUTTON_RIGHT:
                if len(self.selection) == 2:
                    adjusted[self.selection[0]] = self.selection[1]
                else:
                    adjusted[self.selection[0]] = self.selection[1]
                    adjusted[self.selection[0]-1] = self.selection[2]
            self.selection = None
            return
        super().click(pos, button)

    def render(self):
        adjusted = self.adjusted[0]

        if self.selection is not None:
            pos = shared.god.getCursorPosition()
            if len(self.selection) == 2:
                adjusted['points'][self.selection[0]] = pos.tolist()
            else:
                normal = util.getNormal(*np.array(self.selection[1:]))
                dist = np.dot(pos-self.selection[1], normal)

                delta = (normal * dist).astype(int)

                adjusted['points'][self.selection[0]] = (self.selection[1] + delta).tolist()
                adjusted['points'][self.selection[0]-1] = (self.selection[2] + delta).tolist()
        adjusted['colour'] = shared.selected_colour

        super().render()

        for point in adjusted['points']:
            shared.god.drawCircle(point, 5, (0, 0, 0), None)


class Duplicate(Action):
    def __init__(self):
        super().__init__()
        self.apply()
        raise StopAction(self)

    def apply(self):
        shared.level['objects'] += self.objects + self.adjusted
        shared.level['constraints'] += self.constraints + self.adjusted_constraints
        shared.selection = list(
            reversed(range(len(get_objects())-len(self.adjusted), len(get_objects()))))
        shared.joint_selection = list(reversed(range(len(shared.level['constraints'])-len(self.adjusted_constraints), len(shared.level['constraints']))))

    def undo(self):
        shared.level['objects'] = shared.level['objects'][:-len(self.objects)*2]
        shared.level['constraints'] = shared.level['constraints'][:-len(self.adjusted_constraints)*2]

        for i, obj in zip(self.selection_snapshot, self.objects):
            get_objects().insert(i, obj)
        for i, constraint in zip(self.joint_selection_snapshot, self.constraints):
            shared.level['constraints'].insert(i, constraint)

        shared.selection = self.selection_snapshot
        shared.joint_selection = self.joint_selection_snapshot

    def redo(self):
        for i in self.selection_snapshot:
            del get_objects()[i]
        for i in self.joint_selection_snapshot:
            del shared.level['constraints'][i]
        self.apply()

class Select:
    def __init__(self):
        self.selection_snapshot = shared.selection.copy()
        self.objects = []

    def click(self, pos, button):
        if button == BUTTON_RIGHT:
            self.cancel()
            raise StopAction()

        obj = getObjectAt(pos)
        if obj is None:
            return

        #n = get_objects().index(obj)
        n = -1
        for i, other in enumerate(get_objects()):
            if other is obj:
                n = i
                break

        if n in shared.selection:
            shared.selection.remove(n)
            for i in shared.joint_selection.copy():
                objA, objB = shared.level['constraints'][i]['objects']
                if obj is objA or obj is objB:
                    shared.joint_selection.remove(i)
        else:
            for i, constraint in enumerate(shared.level['constraints']):
                objA, objB = constraint['objects']
                if (obj is objA and any(get_objects()[n] is objB for n in shared.selection))\
                or (obj is objB and any(get_objects()[n] is objA for n in shared.selection)):
                    shared.joint_selection.append(i)
            shared.joint_selection.sort(reverse=True)

            shared.selection.append(n)
            shared.selection.sort(reverse=True)

        set_error('Selecting {} objects'.format(len(shared.selection)))

    def render(self):
        pass

    def cancel(self):
        insert()

def getObjectAt(pos):
    pos = np.array(pos)
    for obj in reversed(get_objects()):  # Top polygon checked first
        if obj['type'] == 'polygon':
            intersects = False
            for p1, p2 in zip(np.array(obj['points']), np.roll(obj['points'], -1, 0)):
                if not (min(p1[1], p2[1]) < pos[1] < max(p1[1], p2[1])):
                    continue

                t = (pos[1] - p1[1]) / (p2[1] - p1[1])
                proj_x = p2[0]*t + p1[0]*(1-t)

                if proj_x < pos[0]:
                    intersects = not intersects
            if intersects:
                return obj
        elif obj['type'] == 'circle':
            if length2(obj['pos'] - pos) <= obj['radius']**2:
                return obj
        elif obj['type'] == 'text':
            if font.isPointInChar(obj['char'], obj['size'], pos - obj['pos']):
                return obj
    return None

class Create:
    def __init__(self):
        self.obj = None
        self.selection_snapshot = shared.selection.copy()
        self.joinSelectionSnapshot = shared.joint_selection.copy()

    def render(self):
        if self.obj is not None:
            shared.god.drawObject(add_default_properties(self.obj))

    def apply(self):
        assert self.obj is not None
        self.obj = add_default_properties(self.obj)
        add_object(self.obj)
        shared.selection = [len(get_objects())-1]
        shared.joint_selection = []
        shared.level_modified = True

    def undo(self):
        del shared.level['objects'][-1]
        shared.selection = self.selection_snapshot
        shared.joint_selection = self.joinSelectionSnapshot

    def redo(self):
        self.apply()

class Circle(Create):
    def __init__(self):
        super().__init__()
        self.pos = None
        self.radius = tk.StringVar(value='0')
        set_error('Click point to start circle')

    def initGUI(self):
        frame = tk.Frame(get_inner())
        insert(frame)

        posIntValidator = createValidator('^[0-9]*$')

        tk.Label(frame, text='Radius:').grid(row=0, column=0)
        tk.Entry(frame, textvariable=self.radius, validate='key',
                 validatecommand=posIntValidator, width=6).grid(row=0, column=1)

        tk.Button(frame, text='Done', command=applyWrapper(
            self.apply)).grid(row=1, column=0, columnspan=2)

    def click(self, pos, button):
        if button == BUTTON_RIGHT:
            self.cancel()

        if self.pos is None:
            self.pos = pos
            self.initGUI()
            return

        self.apply()
        raise StopAction(self)

    def apply(self):
        set_error('Circle Created')
        insert()
        super().apply()

    def render(self):
        if self.pos is not None:
            if get_cursor_focus():
                delta = self.pos - shared.god.getCursorPosition()
                radius = round(math.sqrt(sum(delta**2)))
                self.radius.set(str(radius))
            else:
                radius = util.tryDefault(lambda: int(self.radius.get()), 0)

            if radius < 2:
                return

            self.obj = {'type':'circle', 'radius': radius, 'pos': self.pos.tolist()}
        super().render()

    def cancel(self):
        insert()
        set_error('Circle creation cancelled')


class NGon(Create):
    def __init__(self):
        super().__init__()
        self.centre = None
        self.radius = tk.StringVar(value='0')
        self.rotation = tk.StringVar(value='0')
        self.sides = tk.StringVar(value='10')

        set_error('Click point to start N-Gon')

    def initGUI(self):
        frame = tk.Frame(get_inner())
        insert(frame)

        intValidator = createValidator('^-?[0-9]*$')
        posIntValidator = createValidator('^[0-9]*$')

        tk.Label(frame, text='Rotation:').grid(row=0, column=0)
        tk.Entry(frame, textvariable=self.rotation, validate='key',
                 validatecommand=intValidator, width=6).grid(row=0, column=1)

        tk.Label(frame, text='Radius:').grid(row=1, column=0)
        tk.Entry(frame, textvariable=self.radius, validate='key',
                 validatecommand=posIntValidator, width=6).grid(row=1, column=1)

        tk.Label(frame, text='Sides:').grid(row=2, column=0)
        tk.Entry(frame, textvariable=self.sides, validate='key',
                 validatecommand=posIntValidator, width=6).grid(row=2, column=1)

        tk.Button(frame, text='Done', command=applyWrapper(
            self.apply)).grid(row=3, column=0, columnspan=2)

    def click(self, pos, button):
        if button == BUTTON_RIGHT:
            self.cancel()

        if self.centre is None:
            self.centre = pos
            self.initGUI()
            return

        self.apply()
        raise StopAction(self)

    def apply(self):
        if util.tryDefault(lambda: int(self.radius.get()), 0) < 10:
            set_error('Radius too small')
            return

        super().apply()
        set_error('N-Gon Created')
        insert()

    def getPoints(self):
        rotation = util.tryDefault(lambda: int(self.rotation.get()), 0)
        sides = max(util.tryDefault(lambda: int(self.sides.get()), 0), 3)
        points = np.array(list(map(lambda v: [math.cos(v), math.sin(v)], [
                          i*2*math.pi/sides + math.radians(rotation) for i in range(sides)])))
        points *= util.tryDefault(lambda: int(self.radius.get()), 0)
        points += self.centre
        return points.astype(int).tolist()

    def render(self):
        if self.centre is not None:
            if get_cursor_focus():
                delta = self.centre - shared.god.getCursorPosition()
                self.radius.set(str(round(math.sqrt(sum(delta**2)))))
                self.rotation.set(str(round(-math.degrees(math.atan2(*delta)))))

            self.obj = {'type': 'polygon', 'points': self.getPoints()}

        super().render()

    def cancel(self):
        insert()
        set_error('N-gon creation cancelled')


class Text(Create):
    def __init__(self):
        self.pos = shared.god.getCursorPosition()
        self.content = tk.StringVar(value='0')
        self.size = tk.StringVar(value='70')

        frame = tk.Frame(get_inner())
        insert(frame)

        posIntValidator = createValidator('^[0-9]*$')

        tk.Label(frame, text='Content:').grid(row=0, column=0)
        tk.Entry(frame, textvariable=self.content, validate='key', width=6).grid(row=0, column=1)

        tk.Label(frame, text='Size:').grid(row=1, column=0)
        tk.Entry(frame, textvariable=self.size, validate='key',
                 validatecommand=posIntValidator, width=6).grid(row=1, column=1)

    def apply(self):
        try:
            if int(self.size.get()) < 10:
                set_error('Size too small')
                return
        except ValueError:
            set_error('Invalid size')
            return

        if len(self.content.get()) != 1:
            set_error('Invalid content length')
            return

        super().apply()
        set_error('Text Created')
        shared.selection = [len(get_objects())-1]
        insert()

    def click(self, pos, button):
        if button == BUTTON_RIGHT:
            self.cancel()
            raise StopAction()
        elif button == BUTTON_LEFT:
            self.apply()
            raise StopAction(self)

    def render(self):
        if get_cursor_focus():
            self.pos = shared.god.getCursorPosition().tolist()

        size = util.tryDefault(lambda: int(self.size.get()), 0)

        if len(self.content.get()) != 1 or size < 10:
            self.obj = None
        else:
            self.obj = {'type': 'text', 'char': self.content.get(), 'size': int(self.size.get()), 'pos': self.pos}

        super().render()

    def cancel(self):
        insert()
        set_error('Text creation cancelled')


class Rectangle(Create):
    def __init__(self):
        super().__init__()
        self.points = []
        set_error('Click point to start Rectangle')

    def click(self, pos, button):
        if button == BUTTON_RIGHT:
            self.cancel()
            raise StopAction()

        self.points.append(pos)

        if len(self.points) == 2:
            super().apply()
            raise StopAction(self)

    def render(self):
        if len(self.points) == 1:
            corners = self.points[0], shared.god.getCursorPosition()
            points = np.array([[corners[i][0], corners[j][1]]
                               for i, j in ((0, 0), (0, 1), (1, 1), (1, 0))], int)
            self.obj = {'type':'polygon', 'points': points.tolist()}

        super().render()


    def cancel(self):
        insert()
        set_error('Rectangle creation cancelled')


class Polygon(Create):
    def __init__(self):
        self.points = []
        super().__init__()

    def click(self, pos, button):
        if button == BUTTON_RIGHT:
            self.cancel()
            raise StopAction()
        self.points.append(pos.tolist())

    def render(self):
        if len(self.points) == 2:
            shared.god.drawLine(self.points[0], self.points[1])
        elif len(self.points) > 2:
            self.obj = {'type':'polygon', 'points': self.points}
        super().render()

    def apply(self):
        set_error(str(len(self.points)) + ' Sided Polygon Created')
        super().apply()

    def cancel(self):
        insert()
        set_error('Polgon creation cancelled')


def polygonPressed():
    if type(shared.god.current_action) == Polygon:
        points = shared.god.current_action.points
        if len(points) >= 3:
            '''for i, L1 in enumerate(zip(points, np.roll(points,-1,0))):
                for L2 in zip(points[i:], np.roll(points,-1,0)[i:]):
                    output = lineIntersection(L1,L2)
                    if output is False:
                        continue
                    if any((p.astype(int) == output.astype(int)).all() for p in [L1[0],L1[1],L2[0],L2[1]]):
                        continue
                    set_error('Polygon self intersects')
                    return'''
            shared.god.current_action.apply()
            shared.god.current_action = None
        else:
            set_error('At least 3 points required')
    else:
        set_error("Click 'Polygon' to finalise shape")
        shared.god.current_action = Polygon()


def createValidator(regex):
    if type(regex) == str:
        regex = re.compile(regex)

    def function(text):
        return regex.search(text) is not None
    command = shared.root.register(function)
    return command, '%P'


def applyWrapper(apply):
    def function():
        shared.god.current_action = apply()
    return function

class TriggerProperty(widgets.Editor, ttk.Combobox):
    def __init__(self, master, location, **kwargs):
        self.master = master
        super().__init__(location, ('trigger',), master, values=[],
                         width=6, **kwargs)
        self.bind('<<ComboboxSelected>>', self.selected)
        script = {}
        if 'serverScript' in shared.level:
            exec(shared.level['serverScript'], script, script)
        self['values'] = [str(key) for key in script.keys()] + ['']

    def selected(self, e):
        val = self.get()
        self.setTarget(None if val == '' else val)

class Properties(Action):
    def __init__(self):
        super().__init__(ignore_constraints=True)
        self.window = tk.Toplevel(shared.root)
        self.window.title('Selection')
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", cancel_action)
        self.newValues = {}

        inner = tk.Frame(self.window )
        inner.pack(padx=5, pady=5)

        primary = tk.Frame(inner)
        primary.pack()

        def posFloatParser(s):
            if s == '':
                return 0
            v = float(s)
            if v < 0:
                raise ValueError
            return v
        def posIntParser(s):
            if s == '':
                return 0
            v = int(s)
            if v < 0:
                raise ValueError
            return v
        def intParser(s):
            if s in ('','-'):
                return 0
            return int(s)

        tk.Label(primary, text='Friction:').grid(row=0, column=0)
        widgets.PropertyEntry(primary, self.newValues, ('friction',), posFloatParser, width=6).grid(row=0, column=1)

        tk.Label(primary, text='Resitution:').grid(row=1, column=0)
        widgets.PropertyEntry(primary, self.newValues, ('restitution',), posFloatParser, width=6).grid(row=1, column=1)

        tk.Label(primary, text='Lethal:').grid(row=2, column=0)
        widgets.BoolProperty(primary, self.newValues, ('lethal',)).grid(row=2, column=1)

        tk.Label(primary, text='Trigger:').grid(row=3, column=0)
        TriggerProperty(primary, self.newValues).grid(row=3, column=1)

        ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill='x', pady=5)

        notebook = ttk.Notebook(inner)
        notebook.pack()

        physics = tk.Frame(notebook, padx=5)
        notebook.add(physics, text='Physics', sticky='n')

        densityEntry = widgets.PropertyEntry(
            physics, self.newValues, ('physics', 'density'), posFloatParser, width=6)

        tk.Label(physics, text='Enabled:').grid(row=0, column=0)
        widgets.ParentProperty(physics, self.newValues, ('physics',), [densityEntry]).grid(row=0, column=1)

        tk.Label(physics, text='Density:').grid(row=1, column=0)
        densityEntry.grid(row=1, column=1)

        animated = tk.Frame(notebook, padx=5)
        notebook.add(animated, text='Animation', sticky='n')
        children = [
            widgets.PropertyEntry(animated, self.newValues, ('animated', 'period'), posIntParser, width=6),
            widgets.PropertyEntry(animated, self.newValues, ('animated', 'xOffset'), intParser, width=6),
            widgets.PropertyEntry(animated, self.newValues, ('animated', 'yOffset'), intParser, width=6),
            widgets.PropertyEntry(animated, self.newValues, ('animated', 'tOffset'), intParser, width=6)
        ]
        tk.Label(animated, text='Enabled:').grid(row=0, column=0)
        widgets.ParentProperty(animated, self.newValues, ('animated',), children).grid(row=0, column=1)
        for i, (name, child) in enumerate(zip(('Period:', 'X-Offset:', 'Y-Offset:', 'T-Offset:'), children)):
            tk.Label(animated, text=name).grid(row=i+1, column=0)
            child.grid(row=i+1, column=1)

        checkpoint = tk.Frame(notebook, padx=5)
        notebook.add(checkpoint, text='Checkpoint', sticky='n')

        children = [
            widgets.ColourProperty(checkpoint, self.newValues, ('checkpoint','colour')),
            widgets.PropertyEntry(checkpoint, self.newValues, ('checkpoint', 'xOffset'), intParser, width=6),
            widgets.PropertyEntry(checkpoint, self.newValues, ('checkpoint', 'yOffset'), intParser, width=6),
        ]

        tk.Label(checkpoint, text='Enabled:').grid(row=0, column=0)
        widgets.ParentProperty(checkpoint, self.newValues, ('checkpoint',), children).grid(row=0,column=1)
        for i, (name, child) in enumerate(zip(('Colour:','X-Offset:','Y-Offset:'), children)):
            tk.Label(checkpoint, text=name).grid(row=i+1, column=0)
            child.grid(row=i+1, column=1)


        def apply():
            for obj in self.adjusted:
                obj.update(self.newValues)
                def update(source, dest):
                    for key, val in source.items():
                        if type(val) == dict:
                            update(val, dest[key])
                        elif val is None:
                            del dest[key]
                update(self.newValues, obj)
            self.window.destroy()
            self.apply()
            shared.god.current_action = None
        tk.Button(master=inner, text='Apply', command=apply).pack()

    def cancel(self):
        self.window.destroy()
        super().cancel()

    def click(self, pos, button):
        pass

    def render(self):
        super().render()

class AddJoint:
    def __init__(self):
        if len(shared.selection) != 2:
            set_error('Select two objects')
            raise StopAction()
        self.objects = [get_objects()[i] for i in shared.selection]
        if all('physics' not in obj for obj in self.objects):
            set_error('At least one object must have physics enabled')
            raise StopAction()

        self.snapPoints = [np.array(obj['pos'], dtype=int)
                           for obj in self.objects if obj['type'] == 'circle']

    def render(self):
        self.point = shared.god.getCursorPosition().astype(int)

        closest = min(self.snapPoints, key=lambda v: util.length2(
            v-self.point), default=None)
        if closest is not None and util.length2(self.point-closest) < 3**2:
            self.point = closest

        shared.god.drawCircle(self.point, 5, (0, 0, 255))

    def click(self, button, constraint):
        if button == BUTTON_RIGHT:
            self.cancel()
            raise StopAction()
        self.constraint = constraint
        self.apply()
        raise StopAction(self)

    def apply(self):
        shared.level['constraints'].append(self.constraint)
        shared.joint_selection.append(len(shared.level['constraints'])-1)

    def cancel(self):
        set_error('Constraint creation cancelled')

    def undo(self):
        del shared.level['constraints'][-1]
        del shared.joint_selection[-1]

    def redo(self):
        self.apply()


class AddPivot(AddJoint):
    def click(self, pos, button):
        return super().click(button, {
            'type': 'pivot',
            'objects': self.objects,
            'pos': self.point.tolist(),
        })


class AddFixed(AddJoint):
    def click(self, pos, button):
        return super().click(button, {
            'type': 'fixed',
            'objects': self.objects,
            'pos': self.point.tolist(),
        })

class RemoveJoint:
    def __init__(self):
        if len(shared.joint_selection) == 0:
            set_error('Select some joints first')
            raise StopAction()
        self.joint_selection_snapshot = shared.joint_selection.copy()
        self.apply()
        raise StopAction(self)

    def apply(self):
        self.joints = []
        for i in self.joint_selection_snapshot:
            self.joints.append(shared.level['constraints'].pop(i))
        shared.joint_selection = []

    def undo(self):
        for i, joint in zip(self.joint_selection_snapshot, self.joints):
            shared.level['constraints'].insert(i, joint)
        shared.joint_selection = self.joint_selection_snapshot

    def redo(self):
        self.apply()

def set_action(action):
    def function():
        if type(shared.god.current_action) == action:
            shared.god.current_action.cancel()
            shared.god.current_action = None
        else:
            if shared.god.current_action is not None:
                shared.god.current_action.cancel()

            try:
                shared.god.current_action = action()
            except StopAction as e:
                if e.history_entry is not None:
                    shared.history = shared.history[:shared.history_index+1]
                    shared.history.append(e.history_entry)
                    shared.history_index = len(shared.history) - 1
                shared.god.current_action = None
    return function


def cancel_action():
    if shared.god.current_action is not None:
        shared.god.current_action.cancel()
        insert()
        shared.god.current_action = None


def set_error(value):
    error = tk.StringVar(name='errorVar')
    error.set(value)


def get_inner():
    return shared.root.nametowidget('.innerFrame')


def insert(widget=None):
    inner = get_inner()
    if widget is None:  # Remove inserted area
        [w.grid_forget() for w in inner.grid_slaves(row=12, column=0) +
         inner.grid_slaves(row=11, column=0)]
    else:
        widget.grid(row=12)
        ttk.Separator(inner, orient=tk.HORIZONTAL).grid(
            row=11, sticky='ew', pady=5)


def add_default_properties(obj):
    new = {'colour': shared.selected_colour, 'friction': 0.5,
           'restitution': 0.2, 'lethal': False, 'groups': []}
    new.update(obj)
    return new


def add_object(properties):
    shared.level['objects'].append(add_default_properties(properties))
    shared.level_modified = True

def get_cursor_focus():
    return pygame.mouse.get_focused()
