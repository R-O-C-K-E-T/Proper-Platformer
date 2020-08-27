import numpy as np

import util

class Vert:
    __slots__ = ['pos','prev','next']
    def __init__(self, pos):
        self.pos = tuple(pos)

    def __eq__(self, other):
        return self is other or self.pos == other.pos

    def __hash__(self):
        return hash(self.pos)

    def __iter__(self):
        vert = self
        while True:
            yield vert
            vert = vert.next
            if vert is self:
                break

def lineIntersection(L1,L2):
    (x1,y1), (x2,y2) = L1
    (x3,y3), (x4,y4) = L2

    divisor = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
    if divisor == 0:
        return None
    return (((x1*y2-y1*x2)*(x3-x4) - (x1-x2)*(x3*y4-y3*x4)) / divisor, ((x1*y2-y1*x2)*(y3-y4) - (y1-y2)*(x3*y4-y3*x4)) / divisor)

def lineBoundIntersection2(L1,L2):
    pos = lineIntersection(L1,L2)
    if pos is None:
        return None

    d1 = np.subtract(L1[1],L1[0])
    if not (0 < np.dot(np.subtract(pos,L1[0]), d1) < np.dot(d1,d1)):
        return None
    d2 = np.subtract(L2[1], L2[0])
    if not (0 < np.dot(np.subtract(pos,L2[0]), d2) < np.dot(d2,d2)):
        return None

    return pos

def lineBoundIntersection(L1,L2): # TODO combine with util method
    p1, p2 = np.array(L1)
    p3, p4 = np.array(L2)
    divisor = (p1[0]-p2[0])*(p3[1]-p4[1])-(p1[1]-p2[1])*(p3[0]-p4[0])
    if divisor == 0:
        return None
    pos = np.array([(p1[0]*p2[1]-p1[1]*p2[0])*(p3[i]-p4[i]) - (p1[i]-p2[i])*(p3[0]*p4[1]-p3[1]*p4[0]) for i in (0,1)])

    if divisor < 0:
        divisor *= -1
        pos *= -1

    d1 = p2 - p1
    if not (0 < np.dot(pos - p1*divisor, d1) < np.dot(d1,d1)*divisor):
        return None

    d2 = p4 - p3
    if not (0 < np.dot(pos - p3*divisor, d2) < np.dot(d2,d2)*divisor):
        return None

    print('thing', pos / divisor, lineBoundIntersection2(L1,L2))

    return pos / divisor



def area(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-((c[0]-a[0])*(b[1]-a[1]))

def isConvex(a,b,c):
    return area(a,b,c) >= 0

def isVisible(a, b):
    if a.next is b or a.prev is b:
        return False
    if area(a.next.pos, a.pos, b.pos) >= 0 and area(a.prev.pos, a.pos, b.pos) <= 0:
        return False

    edge = a.pos, b.pos
    for test in a:
        if test is a or test is a.next or test is a.prev or test is b or test is b.next or test is b.prev:
            continue
        if lineBoundIntersection((test.pos, test.next.pos), edge) is not None:
            return False
    return True

def split(a,b): # From a to b
    start = prev = Vert(a.pos)
    for vert in a.next:
        nVert = Vert(vert.pos)
        nVert.prev = prev
        prev.next = nVert
        prev = nVert
        if vert is b:
            break
    else:
        raise ValueError
    prev.next = start
    start.prev = prev

    return start

def decompose(start):
    if sum(util.cross2d(vert.pos, vert.next.pos) for vert in start) < 10*2:
        return []
    for a in start:
        if not isConvex(a.prev.pos, a.pos, a.next.pos):
            break
    else:
        return [start]

    for other in sorted(start, key=lambda vert: (a.pos[0]-vert.pos[0])**2 + (a.pos[1]-vert.pos[1])**2):
        if other is a:
            continue
        if isVisible(a, other):
            break
    else:
        #print('dammit', v, [vert.pos for vert in start])
        raise ValueError

    vertA = split(a, other)
    vertB = split(other, a)

    return decompose(vertA) + decompose(vertB)

def convertInto(polygon):
    start = Vert(polygon[0])
    prev = start
    for pos in polygon[1:]:
        vert = Vert(pos)
        vert.prev = prev
        prev.next = vert
        prev = vert
    prev.next = start
    start.prev = prev
    return start

def convertFrom(start):
    return [vert.pos for vert in start]
