import math, time, sys, os, subprocess, functools, types, threading, queue
import numpy as np

from OpenGL.GLU import *

class Profiler:
    def __init__(self, parent=None):
        self.current = None
        self.data = {}
        self.time = None
        self.parent = parent
        self.runningChild = None

    def __call__(self,name):
        if self.parent is not None:
            if self.parent.runningChild is not self:
                if self.parent.runningChild is not None:
                    self.parent.runningChild(None)
                self.parent.runningChild = self

        if self.runningChild is not None:
            self.runningChild(None)
            self.runningChild = None

        if self.current is not None:
            if self.current in self.data:
                self.data[self.current] += time.time() - self.time
            else:
                self.data[self.current] = time.time() - self.time

        self.current = name
        self.time = time.time()

    def getChild(self,name):
        if name not in self.data:
            self.data[name] = Profiler()
        else:
            assert type(self.data[name]) == Profiler
        return self.data[name]

    def _getLines(self):
        def getTime(value):
            if type(value) == Profiler:
                return sum(getTime(val) for val in value.data.values())
            else:
                return value

        total = getTime(self) / 100
        length = max(map(lambda v: len(str(v)), filter(lambda v: type(v) != Profiler, self.data))) + 1

        lines = []
        for name, val in self.data.items():
            lines.append(str(name) + ' ' * (length - len(str(name))) + ': ' + '%.5f' % (getTime(val) / total))
            if type(val) == Profiler:
                for innerLine in val._getLines():
                    lines.append('  ' + innerLine)
        return lines

    def __repr__(self):
        return '\n'.join(self._getLines())
    __str__ = __repr__

def findKey(dictionary, val):
    for key, other in dictionary.items():
        if other == val:
            return key
    raise ValueError

def normalise(vec):
    return vec / math.sqrt(sum(vec**2))

def length2(vec):
    return sum(vec**2)

def length(vec):
    return math.sqrt(sum(vec**2))

def getNormal(a,b):
    d = a-b
    n = d[::-1]
    n[0] *= -1
    return normalise(n)

def genNormals(polygon):
    nextP = np.roll(polygon, 1, 0)
    deltas = nextP - polygon

    normals = deltas[:,::-1] / np.repeat(np.sqrt((deltas**2).sum(1)),2).reshape(-1,2)
    normals[:,1] *= -1

    return normals

def isConvex(a, b, c):
    area = a[0] * (c[1] - b[1]) +\
           b[0] * (a[1] - c[1]) +\
           c[0] * (b[1] - a[1])
    return area <= 0

def lineBoundIntersection(L1,L2): # TODO combine with util method
    p1, p2 = np.array(L1)
    p3, p4 = np.array(L2)
    divisor = (p1[0]-p2[0])*(p3[1]-p4[1])-(p1[1]-p2[1])*(p3[0]-p4[0])
    if divisor == 0:
        return False
    pos = np.array([(p1[0]*p2[1]-p1[1]*p2[0])*(p3[i]-p4[i]) - (p1[i]-p2[i])*(p3[0]*p4[1]-p3[1]*p4[0]) for i in (0,1)])

    if divisor < 0:
        divisor *= -1
        pos *= -1

    d1 = p2 - p1
    if not (0 < np.dot(pos - p1*divisor, d1) < np.dot(d1,d1)*divisor):
        return False

    d2 = p4 - p3
    if not (0 < np.dot(pos - p3*divisor, d2) < np.dot(d2,d2)*divisor):
        return False

    return True

def isEar(polygon, a,b,c):
    if not isConvex(a,b,c):
        return False

    for line in zip(polygon, np.roll(polygon, 1, 0)):
        if any(v is line[0] for v in (a,b,c)) or any(v is line[1] for v in (a,b,c)):
            continue

        if lineBoundIntersection((a,b), line):
            return False
        if lineBoundIntersection((a,c), line):
            return False
        if lineBoundIntersection((b,c), line):
            return False

    for point in polygon:
        if point is a or point is b or point is c:
            continue
        if pointInTri(a, b, c, point) == 2:
            return False

    return True

'''def triangulate(polygon):
   polygon = [tuple(point) for point in polygon]
   if not checkWinding(polygon):
      polygon.reverse()
   n = len(polygon)

   concave = set()
   for i, (a,b,c) in enumerate(zip(np.roll(polygon, 1, 0), polygon, np.roll(polygon, -1, 0))):
      if not isConvex(a,b,c):
         concave.add(tuple(b))

   #ears = [isEar(polygon, a,b,c) for (a,b,c) in zip(np.roll(polygon, 1, 0), polygon, np.roll(polygon, -1, 0))]

   while len(polygon) > 3:
      for i, (a,b,c) in enumerate(zip(np.roll(polygon,1,0), polygon, np.roll(polygon,-1,0))):
         if isEar(polygon, a,b,c):
            break
      else:
         raise ValueError
      #i = ears.index(True)
      yield polygon[(i-1)%n], polygon[i], polygon[(i+1)%n]

      point = polygon[i]
      concave.discard(point)

      del polygon[i]
      #ears.pop(i)
      n -= 1

      for j in ((i-1)%n, i):
         if polygon[j] in concave:
               if isConvex(polygon[(j-1)%n], polygon[j], polygon[(j+1)%n]):
                  concave.remove(polygon[j])
               else:
                  continue

         #ears[j] = isEar(polygon, polygon[(j-1)%n],polygon[j],polygon[(j+1)%n])

   if len(polygon) == 3:
      yield polygon'''

def triangulateSingle(loop):
    if not checkWinding(loop):
        loop = loop[::-1]
    return triangulate([loop])

def triangulate(loops):
    tobj = gluNewTess()

    verticies = []
    def new_vertex(pos):
        verticies.append(pos[:2])

    gluTessProperty(tobj, GLU_TESS_WINDING_RULE, GLU_TESS_WINDING_ODD)
    gluTessCallback(tobj, GLU_TESS_EDGE_FLAG_DATA, lambda *args: None)
    gluTessCallback(tobj, GLU_TESS_BEGIN, lambda *args: None)
    gluTessCallback(tobj, GLU_TESS_VERTEX, new_vertex)
    gluTessCallback(tobj, GLU_TESS_COMBINE, lambda *args: args[0])
    gluTessCallback(tobj, GLU_TESS_END, lambda: None)

    gluTessBeginPolygon(tobj, 0)
    for loop in loops:
        gluTessBeginContour(tobj)
        for point in loop:
            point = point[0],point[1], 0
            gluTessVertex(tobj, point, point)
        gluTessEndContour(tobj)
    gluTessEndPolygon(tobj)

    gluDeleteTess(tobj)

    return [verticies[i:i+3] for i in range(0,len(verticies),3)]

def distance(a,b,p):
    d = b-a
    return (d[1]*p[0]-d[0]*p[1] + b[0]*a[1] - b[1]*a[0]) / math.sqrt(sum(d**2))

def pointInTri(p0,p1,p2, p):
    # 0: Outside, 1: On edge, 2: Inside

    #areas = area(p, a, b), area(p, b, c), area(p, c, a)
    #return not (any(a < 0 for a in areas) and any(a > 0 for a in areas))
    #a = area(p1,p2,p3)
    a = -p1[1]*p2[0] + p0[1]*(-p1[0] + p2[0]) + p0[0]*(p1[1] - p2[1]) + p1[0]*p2[1]

    s = p0[1]*p2[0] - p0[0]*p2[1] + (p2[1] - p0[1])*p[0] + (p0[0] - p2[0])*p[1]
    t = p0[0]*p1[1] - p0[1]*p1[0] + (p0[1] - p1[1])*p[0] + (p1[0] - p0[0])*p[1]

    if a < 0:
        a *= -1
        s *= -1
        t *= -1
    elif a == 0:
        l0, l1 = max((line for line in ((p0,p1),(p0,p2),(p1,p2))), key=lambda line: length2(np.subtract(*line)))

        d = np.subtract(l1, l0)

        if tuple(p) == tuple(l0):
            return 1

        if np.dot(np.subtract(p,l0), np.subtract(l1,l0))**2 != length2(np.subtract(p,l0))*length2(np.subtract(l1,l0)):
            return 0

        if np.dot(np.subtract(p,l0), d) >= 0 and np.dot(np.subtract(p,l1), d) <= 0:
            return 1
        else:
            return 0

    if s < 0 or t < 0 or a < s + t:
        return 0
    elif s == 0 or t == 0 or a == s + t:
        return 1
    else:
        return 2

def checkWinding(polygon): # True for correct, False for should change
    total = sum((b[0]-a[0])*(b[1]+a[1]) for a,b in zip(polygon, np.roll(polygon, 1, 0)))
    return total < 0

def genBounds(polygon):
    return [np.amin(polygon,0), np.amax(polygon,0)]

def rotationMatrix(angle):
    a, b = math.cos(angle), math.sin(angle)
    return np.array([[a,-b],[b,a]],dtype=float)

def rotate(vec, angle):
    sin = math.sin(angle)
    cos = math.cos(angle)
    return np.array([vec[0]*cos-vec[1]*sin, vec[0]*sin + vec[1]*cos], dtype=float)

def cross2d(a,b):
    return a[0]*b[1]-a[1]*b[0]

def RGBtoHCL(r,g,b): # 0-255
    a = min(r,g,b) / max(r,g,b) / 100
    y = 3
    q = math.exp(a*y)

    hue = math.atan2(g-b, r-g)
    chroma = q*(abs(r-g)+abs(g-b)+abs(b-r))/3
    luminance =  (q*max(r,g,b) + (1-q)*min(r,g,b)) / 2
    return hue, chroma, luminance

def HSVtoRGB(hue, sat, val):
    c = val * sat
    hue = (hue % 1) * 6
    x = c * (1 - abs((hue % 2) - 1))
    if   hue > 5:
        out = c, 0, x
    elif hue > 4:
        out = x, 0, c
    elif hue > 3:
        out = 0, x, c
    elif hue > 2:
        out = 0, c, x
    elif hue > 1:
        out = x, c, 0
    else:
        out = c, x, 0
    return np.array(out) + (val - c)

def RGBtoHSV(r,g,b):
    delta = max(r,g,b) - min(r,g,b)
    if r == g == b:
        hue = 0
    else:
        if r > g and r > b:
            hue = (0 + (g-b)/delta) / 6
        elif g > b:
            hue = (2 + (b-r)/delta) / 6
        else:
            hue = (4 + (r-g)/delta) / 6
    hue = hue % 1

    if r == g == b == 0:
        sat = 0
    else:
        sat = delta / max(r,g,b)

    val = max(r,g,b)
    return hue, sat, val


def convertFromLinear(colour):
    return [u*(323/25) if u <= 0.0031308 else (211*u**(5/12) - 11)/200 for u in colour]

def convertToLinear(colour):
    return [u*(25/323) if u <= 0.04045 else ((200*u+11)/211)**(12/5) for u in colour]

def convertColour(colour):
    return '#%02x%02x%02x' % tuple(colour)

def lineIntersection(L1,L2):
    p1, p2 = L1
    p3, p4 = L2
    divisor = (p1[0]-p2[0])*(p3[1]-p4[1])-(p1[1]-p2[1])*(p3[0]-p4[0])
    if divisor == 0:
        return None
    intersect = np.array([(p1[0]*p2[1]-p1[1]*p2[0])*(p3[i]-p4[i]) - (p1[i]-p2[i])*(p3[0]*p4[1]-p3[1]*p4[0]) for i in (0,1)]) / divisor

    '''if (intersect > np.maximum(*L1)).any() or (intersect < np.minimum(*L1)).any():
       return False
    if (intersect > np.maximum(*L2)).any() or (intersect < np.minimum(*L2)).any():
       return False'''
    return intersect

def projectRayPolygon(polygon, a, b):
    result = None
    d = b-a
    l = length2(d)
    for i, line in enumerate(zip(polygon, np.roll(polygon,1,0))):
        if (a == line[0]).all() or (a == line[1]).all():
            continue
        pos = lineIntersection((a,b), line)
        if pos is None:
            continue
        if np.dot(d, pos-a) <= l:
            continue
        if result is None:
            result = pos,i
        else:
            result = min(result, (pos,i), key=lambda v: length2(v[0]-b))
    return result

def splitPolygon(polygon, a, b):
    newA = []
    i = a
    while True:
        newA.append(polygon[i])
        if i == b:
            break
        i = (i+1)%len(polygon)
    newB = []
    i = a
    while True:
        newB.append(polygon[i])
        if i == b:
            break
        i = (i-1)%len(polygon)
    newB.reverse()
    return newA, newB

def sign(val):
    return 1 if val > 0 else -1

def polygonToConvexPolygons(polygon):
    polygons = []
    queue = [list(polygon)]
    while len(queue) > 0:
        polygon = queue.pop()
        if len(polygon) < 3:
            continue
        for notch, (a,b,c) in enumerate(zip(np.roll(polygon,-1,0), polygon, np.roll(polygon,1,0))):
            if distance(a,c,b) < 0:
                break
        else:
            polygons.append(polygon) # Is already convex
            continue
        a,b,c = polygon[notch-1], polygon[notch], polygon[(notch+1)%len(polygon)]
        pointA, indexA = projectRayPolygon(polygon, a,b)
        pointC, indexB = projectRayPolygon(polygon, c,b)
        indexB -= 1

        if indexA - indexB == 1:
            polygon.insert(indexA, (pointA+pointC) / 2)
            if indexA < notch:
                notch += 1
            queue += [*splitPolygon(polygon, notch, indexA)]
        else:
            queue += [*splitPolygon(polygon, notch, (indexA + indexB) // 2)]
    return polygons

def tryDefault(func, default):
    try:
        return func()
    except:
        return default

def clamp(val, min, max):
    return min(max(val, min), max)

def openWithDefaultProgram(filepath):
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open',filepath))

def openWithIDLE(filepath):
    subprocess.call((sys.executable, '-m', 'idlelib', filepath))

def async_input():
    input_queue = queue.Queue()

    def add_input():
        while True:
            input_queue.put(sys.stdin.readline())
    input_thread = threading.Thread(name='Input_Thread', target=add_input)
    input_thread.daemon = True
    input_thread.start()

    return input_queue
