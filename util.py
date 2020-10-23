from __future__ import annotations
from typing import *

import math, time, sys, os, subprocess, functools, types, threading, queue
import numpy as np


from OpenGL import GLU as glu

Vec = np.ndarray

class Profiler:
    def __init__(self):
        self.current = None
        self.data: Dict[str, Union[float, Profiler]] = {}
        self.time: Optional[float] = None
        self.parent: Optional[Profiler] = None
        self.running_child: Optional[Profiler] = None

    def get_child(self, name: str):
        if name in self.data:
            child = self.data[name]
            assert isinstance(child, Profiler)
        else:
            child = Profiler()
            child.parent = self
            self.data[name] = child
        return child

    def __call__(self, name: Optional[str]):
        if self.parent is not None:
            if self.parent.running_child is not self:
                if self.parent.running_child is not None:
                    self.parent.running_child(None)
                self.parent.running_child = self

        if self.running_child is not None:
            self.running_child(None)
            self.running_child = None

        if self.current is not None:
            if self.current in self.data:
                self.data[self.current] += time.time() - self.time
            else:
                self.data[self.current] = time.time() - self.time

        self.current = name
        self.time = time.time()

    def _get_lines(self) -> List[str]:
        def get_tile(value: Union[Profiler, float]) -> float:
            if isinstance(value, Profiler):
                return sum(get_tile(val) for val in value.data.values())
            else:
                return value

        total = get_tile(self) / 100
        length = max(map(lambda v: len(str(v)), self.data)) + 1

        lines: List[str] = []
        for name, val in self.data.items():
            lines.append(str(name) + ' ' * (length - len(str(name))) + ': ' + '%.5f' % (get_tile(val) / total))
            if isinstance(val, Profiler):
                for innerLine in val._get_lines():
                    lines.append('  ' + innerLine)
        return lines

    def __repr__(self):
        return '\n'.join(self._get_lines())
    __str__ = __repr__

K = TypeVar('K')
V = TypeVar('V')
def find_key(dictionary: Dict[K, V], val: V) -> K:
    for key, other in dictionary.items():
        if other == val:
            return key
    raise ValueError('Value not found')

def normalise(vec: Vec) -> Vec:
    return vec / math.sqrt(sum(vec**2))

def length2(vec: Vec) -> float:
    return sum(vec**2)

def length(vec: Vec) -> float:
    return math.sqrt(sum(vec**2))

def get_normal(a: Vec, b: Vec) -> Vec:
    d = a-b
    n = d[::-1]
    n[0] *= -1
    return normalise(n)

def gen_normals(polygon: List[Vec]) -> List[Vec]:
    nextP = np.roll(polygon, 1, 0)
    deltas = nextP - polygon

    normals = deltas[:,::-1] / np.repeat(np.sqrt((deltas**2).sum(1)),2).reshape(-1,2)
    normals[:,1] *= -1

    return normals

def is_convex(a: Vec, b: Vec, c: Vec) -> bool:
    area = a[0] * (c[1] - b[1]) +\
           b[0] * (a[1] - c[1]) +\
           c[0] * (b[1] - a[1])
    return area <= 0

def line_bound_intersection(L1: Vec, L2: Vec) -> bool: # TODO combine with util method
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

def is_ear(polygon: List[Vec], a: Vec, b: Vec, c: Vec) -> bool:
    if not is_convex(a,b,c):
        return False

    for line in zip(polygon, np.roll(polygon, 1, 0)):
        if any(v is line[0] for v in (a,b,c)) or any(v is line[1] for v in (a,b,c)):
            continue

        if line_bound_intersection((a,b), line):
            return False
        if line_bound_intersection((a,c), line):
            return False
        if line_bound_intersection((b,c), line):
            return False

    for point in polygon:
        if point is a or point is b or point is c:
            continue
        if point_in_triangle(a, b, c, point) == 2:
            return False

    return True

'''def triangulate(polygon):
   polygon = [tuple(point) for point in polygon]
   if not check_winding(polygon):
      polygon.reverse()
   n = len(polygon)

   concave = set()
   for i, (a,b,c) in enumerate(zip(np.roll(polygon, 1, 0), polygon, np.roll(polygon, -1, 0))):
      if not is_convex(a,b,c):
         concave.add(tuple(b))

   #ears = [is_ear(polygon, a,b,c) for (a,b,c) in zip(np.roll(polygon, 1, 0), polygon, np.roll(polygon, -1, 0))]

   while len(polygon) > 3:
      for i, (a,b,c) in enumerate(zip(np.roll(polygon,1,0), polygon, np.roll(polygon,-1,0))):
         if is_ear(polygon, a,b,c):
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
               if is_convex(polygon[(j-1)%n], polygon[j], polygon[(j+1)%n]):
                  concave.remove(polygon[j])
               else:
                  continue

         #ears[j] = is_ear(polygon, polygon[(j-1)%n],polygon[j],polygon[(j+1)%n])

   if len(polygon) == 3:
      yield polygon'''

def triangulate_single(loop: List[Vec]) -> List[List[Vec]]:
    if not check_winding(loop):
        loop = loop[::-1]
    return triangulate([loop])

def triangulate(loops: List[List[Vec]]) -> List[List[Vec]]:
    tessalator = glu.gluNewTess()

    vertices = []
    def new_vertex(pos):
        vertices.append(pos[:2])

    glu.gluTessProperty(tessalator, glu.GLU_TESS_WINDING_RULE, glu.GLU_TESS_WINDING_ODD)
    glu.gluTessCallback(tessalator, glu.GLU_TESS_EDGE_FLAG_DATA, lambda *args: None)
    glu.gluTessCallback(tessalator, glu.GLU_TESS_BEGIN, lambda *args: None)
    glu.gluTessCallback(tessalator, glu.GLU_TESS_VERTEX, new_vertex)
    glu.gluTessCallback(tessalator, glu.GLU_TESS_COMBINE, lambda *args: args[0])
    glu.gluTessCallback(tessalator, glu.GLU_TESS_END, lambda: None)

    glu.gluTessBeginPolygon(tessalator, 0)
    for loop in loops:
        glu.gluTessBeginContour(tessalator)
        for point in loop:
            point = point[0],point[1], 0
            glu.gluTessVertex(tessalator, point, point)
        glu.gluTessEndContour(tessalator)
    glu.gluTessEndPolygon(tessalator)

    glu.gluDeleteTess(tessalator)

    return [vertices[i:i+3] for i in range(0,len(vertices),3)]

def distance(a: Vec, b: Vec, p: Vec) -> float:
    d = b-a
    return (d[1]*p[0]-d[0]*p[1] + b[0]*a[1] - b[1]*a[0]) / math.sqrt(sum(d**2))

def point_in_triangle(p0: Vec, p1: Vec, p2: Vec, p: Vec) -> int:
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

def check_winding(polygon: List[Vec]) -> bool: # True for correct, False for should change
    total = sum((b[0]-a[0])*(b[1]+a[1]) for a,b in zip(polygon, np.roll(polygon, 1, 0)))
    return total < 0

def gen_bounds(polygon: List[Vec]) -> Tuple[Vec, Vec]:
    return np.amin(polygon,0), np.amax(polygon,0)

def rotationMatrix(angle: float) -> np.ndarray:
    a, b = math.cos(angle), math.sin(angle)
    return np.array([[a,-b],[b,a]],dtype=float)

def rotate(vec: Vec, angle: float) -> Vec:
    sin = math.sin(angle)
    cos = math.cos(angle)
    return np.array([vec[0]*cos-vec[1]*sin, vec[0]*sin + vec[1]*cos], dtype=float)

def cross2d(a: Vec, b: Vec) -> float:
    return a[0]*b[1]-a[1]*b[0]

def RGBtoHCL(r: float, g: float, b: float) -> Tuple[float, float, float]: # 0-255
    a = min(r,g,b) / max(r,g,b) / 100
    y = 3
    q = math.exp(a*y)

    hue = math.atan2(g-b, r-g)
    chroma = q*(abs(r-g)+abs(g-b)+abs(b-r))/3
    luminance =  (q*max(r,g,b) + (1-q)*min(r,g,b)) / 2
    return hue, chroma, luminance

def HSVtoRGB(hue: float, sat: float, val: float) -> np.ndarray:
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

def RGBtoHSV(r: float, g: float, b: float) -> Tuple[float, float, float]:
    delta = max(r, g, b) - min(r, g, b)
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


def convert_from_linear(colour: Tuple[float, float, float]):
    return [u*(323/25) if u <= 0.0031308 else (211*u**(5/12) - 11)/200 for u in colour]

def convert_to_linear(colour: Tuple[float, float, float]):
    return [u*(25/323) if u <= 0.04045 else ((200*u+11)/211)**(12/5) for u in colour]

def convert_colour(colour: Tuple[int, int, int]):
    return '#%02x%02x%02x' % tuple(colour)

def line_intersection(L1: Tuple[Vec, Vec], L2: Tuple[Vec, Vec]) -> Optional[Vec]:
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

def project_ray_polygon(polygon: List[Vec], a: Vec, b: Vec) -> Optional[Tuple[Vec, int]]:
    result = None
    d = b-a
    l = length2(d)
    for i, line in enumerate(zip(polygon, np.roll(polygon,1,0))):
        if (a == line[0]).all() or (a == line[1]).all():
            continue
        pos = line_intersection((a,b), line)
        if pos is None:
            continue
        if np.dot(d, pos-a) <= l:
            continue
        if result is None:
            result = pos, i
        else:
            result = min(result, (pos,i), key=lambda v: length2(v[0]-b))
    return result

def split_polygon(polygon: List[Vec], a: Vec, b: Vec) -> Tuple[List[Vec], List[Vec]]:
    new_a = []
    i = a
    while True:
        new_a.append(polygon[i])
        if i == b:
            break
        i = (i+1)%len(polygon)
    new_b = []
    i = a
    while True:
        new_b.append(polygon[i])
        if i == b:
            break
        i = (i-1)%len(polygon)
    new_b.reverse()
    return new_a, new_b

def sign(val: float):
    return 1 if val > 0 else -1

def polygon_to_convex_polygons(polygon: List[Vec]) -> List[List[Vec]]:
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
        pointA, indexA = project_ray_polygon(polygon, a,b)
        pointC, indexB = project_ray_polygon(polygon, c,b)
        indexB -= 1

        if indexA - indexB == 1:
            polygon.insert(indexA, (pointA+pointC) / 2)
            if indexA < notch:
                notch += 1
            queue += [*split_polygon(polygon, notch, indexA)]
        else:
            queue += [*split_polygon(polygon, notch, (indexA + indexB) // 2)]
    return polygons

T = TypeVar('T')
def try_default(func: Callable[[], T], default: T) -> T:
    try:
        return func()
    except:
        return default

T = TypeVar('T')
def clamp(val: T, v_min: T, v_max: T) -> T:
    return min(max(val, v_min), v_max)

def open_with_default_program(filepath: str):
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open',filepath))

def open_with_IDLE(filepath: str):
    subprocess.call((sys.executable, '-m', 'idlelib', filepath))

def async_input():
    input_queue: queue.Queue[str] = queue.Queue()

    def add_input():
        while True:
            input_queue.put(sys.stdin.readline())
    input_thread = threading.Thread(name='Input_Thread', target=add_input)
    input_thread.daemon = True
    input_thread.start()

    return input_queue
