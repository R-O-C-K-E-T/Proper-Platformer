import time,math,json,threading,sys,socket,os,tempfile,string,types,functools,pickle,copy,pygame,queue # All the modules
from multiprocessing import Pool
from traceback import print_exc

from pygame.locals import *
#PG_GL_CONTEXT_PROFILE_MASK = GL_CONTEXT_PROFILE_MASK
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

import camera, wrapper, util, objects, ai, editor, actions, packets
import physics.physics as physics
#from util import genBounds, genNormals, convertColour, checkWinding
from objects import Object, OtherPlayer, Player
from draw import Drawer
from client import Client
from server import Server
import networking


def convert_key(key):
    try:
        return getattr(pygame.locals, 'K_' + key)
    except:
        return None

class Clock:  # Improved clock for linux, your mileage may vary
    def __init__(self):
        self.prevTime = time.time()
        self.times = []

    def get_fps(self):
        if len(self.times) == 0:
            return -1
        return len(self.times) / sum(self.times)

    def tick(self, framerate=60):
        if len(self.times) > 5:
            self.times.pop(0)

        target = self.prevTime + 1/framerate

        t = time.time()
        if t < target:
            wait = target - t - 0.0005
            if wait > 0:
                time.sleep(wait)
            while time.time() < target:
                pass

        t = time.time()
        self.times.append(t - self.prevTime)
        self.prevTime = t

class Local:
    def __init__(self, fancy, screen, world, players):
        self.players = players
        self.drawer = Drawer(fancy, players, screen, world)

    def update(self):
        for player in self.players:
            player.action = player.getAction()
        self.drawer.update()

    def render(self):
        self.drawer.render()

    def cleanup(self):
        self.drawer.cleanup()

def createWorld(level):
    world = wrapper.World(True) # Since level file is available we must be host
    world.gravity = level.get('gravity', (0,0.3))
    world.spawn = level.get('spawn', (0,0))

    for data in level.get('objects',[]):
        world.createObject(data)

    for constraint in level.get('constraints', []):
        objA, objB = [world.objects[level['objects'].index(data)]
                      for data in constraint['objects']]
        world.addConstraint(objA, objB, constraint)

    world.loadScript(level.get('serverScript', ''))#, editor.defaultScript))

    return world

def createPlayers(world, settings):
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


def drawSquare(lower, upper):
    depth = 1
    glBegin(GL_LINE_LOOP)
    glVertex3f(lower[0], lower[1], depth)
    glVertex3f(lower[0], upper[1], depth)
    glVertex3f(upper[0], upper[1], depth)
    glVertex3f(upper[0], lower[1], depth)
    glEnd()

def configure_opengl():
    glEnable(GL_MULTISAMPLE)
    glClearColor(1,1,1,1)
    glEnable(GL_DEPTH_TEST)

def run(levelname=None, port=None, address=None):
    multiplayer = levelname is None

    with open('settings.json') as f:
        settings = json.load(f)

    if multiplayer:
        world = wrapper.World(False)
    else:
        level = editor.loadFile(levelname)
        world = createWorld(level)

    players = createPlayers(world, settings)

    pygame.font.init()
    pygame.display.init()

    pygame.display.gl_set_attribute(GL_STENCIL_SIZE, 8)
    if settings['multisampling'] > 1:
        pygame.display.gl_set_attribute(GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(GL_MULTISAMPLESAMPLES, settings['multisampling'])

    fancy = settings.get('fancy', True)

    #pygame.display.gl_set_attribute(GL_CONTEXT_MAJOR_VERSION, 4)
    #pygame.display.gl_set_attribute(GL_CONTEXT_MINOR_VERSION, 5)
    #pygame.display.gl_set_attribute(PG_GL_CONTEXT_PROFILE_MASK, GL_CONTEXT_PROFILE_COMPATIBILITY)

    #print(pygame.display.gl_get_attribute(GL_CONTEXT_PROFILE_MASK))

    display = 1600, 900
    screen = pygame.display.set_mode(display, DOUBLEBUF|OPENGL|RESIZABLE)
    #screen = pygame.display.set_mode(display, DOUBLEBUF|OPENGL)
    #screen = pygame.display.set_mode(display, OPENGL)

    glEnable(GL_MULTISAMPLE)
    glClearColor(0, 0, 0, 1)

    if fancy:
        glEnable(GL_DEPTH_TEST)

        #glDepthFunc(GL_LEQUAL)
        glClearDepth(0.0)
        glEnable(GL_FRAMEBUFFER_SRGB)

    #glEnable(GL_BLEND)
    #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    #glEnable(GL_ALPHA_TEST)
        # $ x+y=z $

    glLineWidth(1.5)

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

    frameTimer = FrameTimer()

    clock = pygame.time.Clock()

    #ticking = True

    try:
        running = True
        while running:
            profiler('Events')
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == VIDEORESIZE:
                    if sys.platform != 'win32':
                        # On Windows if we set_mode we get a new OpenGL context
                        # Given that we don't update the screen size properly, pygame won't know the actual window size
                        pygame.display.set_mode(event.size, DOUBLEBUF|OPENGL|RESIZABLE)
                    updater.drawer.resize(event.size)

                elif event.type == KEYDOWN:
                    if not multiplayer:
                        if event.key == convert_key(settings.get('reset_button', None)):
                            updater.cleanup()
                            level = editor.loadFile(levelname)
                            world = createWorld(level)
                            players = createPlayers(world, settings)
                            updater = Local(fancy, screen, world, players)
                            updater.drawer.resize()
                        '''elif event.key == K_p:
                            ticking = not ticking
                        elif event.key == K_t:
                            updater.update()'''
            if multiplayer:
                pygame.display.set_caption('Platformer: {:.2f} {:.2f}±{:.2f}ms'.format(clock.get_fps(), updater.connection.rtt*1000, updater.connection.rtt_dev*1000))
            else:
                pygame.display.set_caption('Platformer: {:.2f}'.format(clock.get_fps()))
            profiler('Updating')
            #if ticking:
            updater.update()
            profiler('Render')
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            updater.render()

            '''glDepthFunc(GL_ALWAYS)
            glPointSize(5.0)
            glColor3f(0,1,0)
            glBegin(GL_POINTS)
            for contact in world.contacts:
                for point in contact.points:
                    glVertex2fv(point.globalA)
            glEnd()

            glColor3f(1,0,0)
            glBegin(GL_LINES)
            for contact in world.contacts:
                for point in contact.points:
                    glVertex2fv(point.globalA)
                    glVertex2fv(np.add(point.globalA, np.multiply(point.normal,5)))
            glEnd()'''


            '''root = world.AABBTree.root
            def traverse(node):
                drawSquare(*node.bounds)

                if hasattr(node, 'children'):
                    for child in node.children:
                        traverse(child)
            if root is not None:
                traverse(root)'''

            profiler('Flipping')
            pygame.display.flip()
            profiler('Waiting')
            clock.tick(60)
            #clock.tick()
            frameTimer.tick()
        print('Profiler:')
        print(profiler)
        print()
        print('FPS:')
        frameTimer.print_results()

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

def runServer(levelname, port):
    commands = True

    if commands:
        input_queue = util.async_input()

    level = editor.loadFile(levelname)
    world = createWorld(level)

    server = Server(world, level.get('clientScript', None), port)

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
                        world = createWorld(level)
                        server.setWorld(world, level.get('clientScript', None))
                        print('Refreshing level')
                    elif line == 'q':
                        break
                    elif len(contents) > 0 and contents[0] == 'l':
                        if len(contents) != 2:
                            print('Invalid number of arguments')
                        else:
                            levelname = contents[1]
                            try:
                                level = editor.loadFile(levelname)
                            except FileNotFoundError:
                                print('Level doesn\'t exist')
                            else:
                                world = createWorld(level)
                                server.setWorld(world, level.get('clientScript', None))
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
                runServer(level, port)
            elif mode == 'client':
                address = sys.argv[2]
                run(address=address, port=port)
