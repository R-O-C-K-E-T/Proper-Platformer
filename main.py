from typing import *

import time, json, sys, pygame, queue, math
from contextlib import contextmanager
import numpy as np

import pygame.locals as pg_locals
from OpenGL import GL as gl

import wrapper, util, editor, packets, networking
from objects import Player
from draw import Drawer
from client import Client
from server import Server

@contextmanager
def with_framebuffer(framebuffer):
    _, _, width, height = gl.glGetIntegerv(gl.GL_VIEWPORT)
    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, framebuffer)
    gl.glViewport(0, 0, width, height)
    try:
        yield None
    except:
        gl.glBindFramebuffer(gl.GL_DRAW_FRAMEBUFFER, 0)
        gl.glDrawBuffer(gl.GL_BACK)
        gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, framebuffer)
        gl.glBlitFramebuffer(0, 0, width, height, 0, 0, width, height, gl.GL_COLOR_BUFFER_BIT, gl.GL_NEAREST)
            
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0) 

def convert_key(key):
    try:
        return getattr(pg_locals, 'K_' + key)
    except:
        return None

class Clock:  # Improved clock for linux, your mileage may vary
    def __init__(self):
        self.prev_time = time.time()
        self.times: List[float] = []

    def get_fps(self) -> float:
        if len(self.times) == 0:
            return -1
        return len(self.times) / sum(self.times)

    def tick(self, framerate=60):
        if len(self.times) > 5:
            self.times.pop(0)

        target = self.prev_time + 1/framerate

        t = time.time()
        if t < target:
            wait = target - t - 0.0005
            if wait > 0:
                time.sleep(wait)
            while time.time() < target:
                pass

        t = time.time()
        self.times.append(t - self.prev_time)
        self.prev_time = t

class Local:
    def __init__(self, fancy, screen, world, players):
        self.players = players
        self.drawer = Drawer(fancy, players, screen, world)

    def update(self):
        for player in self.players:
            player.action = player.get_action()
        self.drawer.update()

    def render(self):
        self.drawer.render()

    def cleanup(self):
        self.drawer.cleanup()

def create_world(level):
    world = wrapper.World(True) # Since level file is available we must be host
    world.gravity = level.get('gravity', (0,0.3))
    world.spawn = level.get('spawn', (0,0))

    for data in level.get('objects',[]):
        world.create_object(data)

    for constraint in level.get('constraints', []):
        obj_a, obj_b = [world.objects[level['objects'].index(data)]
                      for data in constraint['objects']]
        world.add_constraint(obj_a, obj_b, constraint)

    world.load_script(level.get('server_script', ''))#, editor.defaultScript))

    return world

def create_players(world, settings):
    players = []
    for config in settings['players']:
        if config['active']:
            codes = []
            for key in config['controls']:
                code = convert_key(key)
                if code is None:
                    raise RuntimeError('Invalid Key: {}'.format(key))
                codes.append(code)
            player = Player(world, config['colour'], config['name'], [codes[0:2], codes[2:4]])
            world.add_object(player)
            players.append(player)
    return players

class FrameTimer:
    def __init__(self):
        self.times = []
        self.time = None

    def tick(self):
        if self.time is None:
            self.time = time.time()
            return

        t = time.time()
        self.times.append(1 / (t - self.time))
        if len(self.times) > 10000:
            del self.times[0]
        self.time = t

    def print_results(self):
        if len(self.times) == 0:
            return
        sorted_times = sorted(self.times)

        print(f'''Max    : {sorted_times[-1]:.2f}
Min    : {sorted_times[0]:.2f}
Mean   : {sum(self.times)/len(self.times):.2f}
Median : {sorted_times[len(self.times)//2]:.2f}
''')


def draw_square(lower: Tuple[float, float], upper: Tuple[float, float]):
    depth = 1
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex3f(lower[0], lower[1], depth)
    gl.glVertex3f(lower[0], upper[1], depth)
    gl.glVertex3f(upper[0], upper[1], depth)
    gl.glVertex3f(upper[0], lower[1], depth)
    gl.glEnd()

def draw_fuzzy_circle(radius: float, colour):
    gl.glBegin(gl.GL_TRIANGLE_FAN)

    gl.glColor4f(*colour, 0.7)
    gl.glVertex2f(0,0)

    gl.glColor4f(*colour, 0)
    N = 15
    for i in range(N + 1):
        a = 2*math.pi * i / N
        gl.glVertex2f(math.cos(a)*radius, math.sin(a)*radius)

    gl.glEnd()

def configure_opengl():
    gl.glEnable(gl.GL_MULTISAMPLE)
    gl.glClearColor(1,1,1,1)
    gl.glEnable(gl.GL_DEPTH_TEST)

def run(levelname: Optional[str]=None, port: Optional[int]=None, address: Optional[str]=None):
    multiplayer = levelname is None

    with open('settings.json') as f:
        settings = json.load(f)

    if multiplayer:
        world = wrapper.World(False)
    else:
        level = editor.load_file(levelname)
        world = create_world(level)

    players = create_players(world, settings)

    pygame.font.init()
    pygame.display.init()

    #pygame.display.gl_set_attribute(pg_locals.GL_STENCIL_SIZE, 8)
    if settings['multisampling'] > 1:
        pygame.display.gl_set_attribute(pg_locals.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pg_locals.GL_MULTISAMPLESAMPLES, settings['multisampling'])

    fancy: bool = settings.get('fancy', True)

    #pygame.display.gl_set_attribute(pg_locals.GL_CONTEXT_MAJOR_VERSION, 4)
    #pygame.display.gl_set_attribute(pg_locals.GL_CONTEXT_MINOR_VERSION, 5)
    #pygame.display.gl_set_attribute(pg_locals.GL_CONTEXT_PROFILE_MASK, pg_locals.GL_CONTEXT_PROFILE_COMPATIBILITY)

    #print(pygame.display.gl_get_attribute(pg_locals.GL_CONTEXT_PROFILE_MASK))

    display = 1600, 900
    screen = pygame.display.set_mode(display, pg_locals.DOUBLEBUF | pg_locals.OPENGL | pg_locals.RESIZABLE)
    #screen = pygame.display.set_mode(display, pg_locals.DOUBLEBUF | pg_locals.OPENGL)
    #screen = pygame.display.set_mode(display, pg_locals.OPENGL)

    gl.glEnable(gl.GL_MULTISAMPLE)
    gl.glClearColor(0, 0, 0, 1)

    if fancy:
        gl.glEnable(gl.GL_DEPTH_TEST)

        #gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glClearDepth(0.0)
        gl.glEnable(gl.GL_FRAMEBUFFER_SRGB)

    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    gl.glEnable(gl.GL_LINE_SMOOTH)
    gl.glHint(gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)

    #gl.glEnable(gl.GL_ALPHA_TEST)
        # $ x+y=z $

    gl.glLineWidth(1.5)

    if multiplayer:
        for timeout in (3, 5, 5):
            try:
                connection = networking.make_client_connection(address, port, packets.PROTOCOL, timeout, packets.InitConnectionPacketServer(players), True)
                break
            except Exception as e:
                print('Failed to connect to {}:{} because {}'.format(address, port, e))
        else:
            return
        #connection.trace = []
        updater = Client(fancy, screen, world, players, connection)
    else:
        updater = Local(fancy, screen, world, players)


    '''agent = ai.RandAgent((256,256), 4, 6)
    ai_player = ai.AIPlayer(agent, world, (0,255,0), 'AI')
    players.append(ai_player)
    world.add_object(ai_player)'''

    profiler = util.Profiler()

    updater.drawer.resize()

    pygame.display.set_caption('Platformer')

    frame_timer = FrameTimer()

    clock = pygame.time.Clock()

    #ticking = True

    fuzzy_displaylist = gl.glGenLists(1)
    gl.glNewList(fuzzy_displaylist, gl.GL_COMPILE)
    draw_fuzzy_circle(1.0, (0.1,0.1,1.0))
    gl.glEndList()
    
    debug = False
    ticking = True
    try:
        running = True
        while running:
            profiler('Events')
            for event in pygame.event.get():
                if event.type == pg_locals.QUIT:
                    running = False
                elif event.type == pg_locals.VIDEORESIZE:
                    if sys.platform != 'win32':
                        # On Windows if we set_mode we get a new Opengl.GL context
                        # Given that we don't update the screen size properly, pygame won't know the actual window size
                        pygame.display.set_mode(event.size, pg_locals.DOUBLEBUF|pg_locals.OPENGL|pg_locals.RESIZABLE)
                    updater.drawer.resize(event.size)

                elif event.type == pg_locals.KEYDOWN:
                    if not multiplayer:
                        if event.key == convert_key(settings.get('reset_button', None)):
                            updater.cleanup()
                            level = editor.load_file(levelname)
                            world = create_world(level)
                            players = create_players(world, settings)
                            updater = Local(fancy, screen, world, players)
                            updater.drawer.resize()
                        elif event.key == convert_key('b'):
                            debug = not debug
                        elif event.key == convert_key('p'):
                            ticking = not ticking
                        elif event.key == convert_key('t'):
                            updater.update()
            if multiplayer:
                pygame.display.set_caption('Platformer: {:.2f} {:.2f}±{:.2f}ms'.format(clock.get_fps(), updater.connection.rtt*1000, updater.connection.rtt_dev*1000))
            else:
                pygame.display.set_caption('Platformer: {:.2f}'.format(clock.get_fps()))
            profiler('Updating')
            if ticking:
                updater.update()
            profiler('Render')
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            updater.render()

            if False: # Debug contacts
                gl.glDepthFunc(gl.GL_ALWAYS)
                gl.glPointSize(5.0)
                gl.glColor3f(0,1,0)
                gl.glBegin(gl.GL_POINTS)
                for contact in world.contacts:
                    for point in contact.points:
                        gl.glVertex2fv(point.global_a)
                gl.glEnd()

                gl.glColor3f(1,0,0)
                gl.glBegin(gl.GL_LINES)
                for contact in world.contacts:
                    for point in contact.points:
                        gl.glVertex2fv(point.global_a)
                        gl.glVertex2fv(np.add(point.global_a, np.multiply(point.normal,5)))
                gl.glEnd()

            if False: # Debug AABB tree
                root = world.AABBTree.root
                def traverse(node):
                    draw_square(*node.bounds)

                    if hasattr(node, 'children'):
                        for child in node.children:
                            traverse(child)
                if root is not None:
                    traverse(root)

            profiler('Flipping')
            pygame.display.flip()
            profiler('Waiting')
            clock.tick(60)
            #clock.tick()
            frame_timer.tick()
        print('Profiler:')
        print(profiler)
        print()
        print('FPS:')
        frame_timer.print_results()

        if multiplayer:
            '''print('Writing trace')
            with open('clientTrace.pickle', 'wb') as f:
                pickle.dump(connection.trace, f)'''
            updater.connection.send(packets.DisconnectPacket('Logged Off'))
    finally:
        #updater.drawer.cache.dump_texture()
        #updater.drawer.cache.dump_depth_texture()

        updater.cleanup()
        pygame.quit()

def run_server(levelname, port):
    commands = True

    if commands:
        input_queue = util.async_input()

    level = editor.load_file(levelname)
    world = create_world(level)

    server = Server(world, level.get('client_script', None), port)

    clock = [pygame.time.Clock, Clock][sys.platform.startswith('linux')]()

    did_crash = True
    try:
        while True:
            if commands:
                try:
                    line = input_queue.get_nowait()
                except queue.Empty:
                    pass
                else:
                    line = line.strip()

                    contents = line.split()
                    if line == 'r':
                        world = create_world(level)
                        server.set_world(world, level.get('client_script', None))
                        print('Refreshing level')
                    elif line == 'q':
                        break
                    elif len(contents) > 0 and contents[0] == 'l':
                        if len(contents) != 2:
                            print('Invalid number of arguments')
                        else:
                            levelname = contents[1]
                            try:
                                level = editor.load_file(levelname)
                            except FileNotFoundError:
                                print('Level doesn\'t exist')
                            else:
                                world = create_world(level)
                                server.set_world(world, level.get('client_script', None))
                    elif line == 'p':
                        if server.paused:
                            print('Unpausing Server')
                        else:
                            print('Pausing Server')
                        server.paused = not server.paused
                    elif line == 's':
                        if len(server.connections) != 0:   
                            for connection, players in server.connections.items():
                                print(', '.join(player.name for player in players) + ': ping={:.2f}±{:.2f}ms loss={:.1f}%'.format(connection.rtt*1000, connection.rtt_dev*1000, connection.packet_loss*100))
                        else:
                            print('No players')
                    else:
                        print('Invalid command')
            server.update()
            #clock.tick()
            clock.tick(60)
        did_crash = False
    finally:
        if did_crash:
            server.stop('Server crashed')
        else:
            print('Stopping server')
            server.stop('Server stopped')

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode not in ('local', 'client', 'server'):
        print('Invalid mode {}, must be client/server/local'.format(mode))
    elif mode == 'local':
        if len(sys.argv) < 3:
            print('Level not specified')
        else:
            level = sys.argv[2]
            run(levelname=level)
    else:
        if len(sys.argv) < 3:
            print(('Level' if mode == 'server' else 'Address') + ' not specified')
        elif len(sys.argv) < 4:
            print('Port not specified')
        else:
            port = int(sys.argv[3])
            if mode == 'server':
                level = sys.argv[2]
                run_server(level, port)
            elif mode == 'client':
                address = sys.argv[2]
                run(address=address, port=port)
