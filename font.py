from os.path import dirname, join
import numpy as np

from fontTools import ttLib
from fontTools.pens.basePen import BasePen
from fontTools.encodings.StandardEncoding import StandardEncoding

from OpenGL.GL import *

import util, decomposition

class CustomPen(BasePen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loops = []
        self.loop = None

    def _moveTo(self, pt):
        if self.loop is not None:
            self.loops.append(self.loop)
        self.loop = [pt]

    def _closePath(self):
        if self.loop is not None:
            self.loops.append(self.loop)
        self.loop = None

    def _endPath(self):
        if self.loop is not None:
            self.loops.append(self.loop)
        self.loop = None

    def _lineTo(self, pt1):
        self.loop.append(pt1)

    def _curveToOne(self, pt1, pt2, pt3):
        pt0 = np.array(self._getCurrentPoint())
        pt1 = np.array(pt1)
        pt2 = np.array(pt2)
        pt3 = np.array(pt3)

        n = 2
        for i in range(n):
            t = (i+1) / n

            a = pt0*(1-t) + pt1*t
            b = pt2*(1-t) + pt3*t

            v = (a*(1-t) + b*t).astype(int).tolist()
            self.loop.append(v)

class SizedDrawnCharacter:
    def __init__(self, loops, triangles, convex_polygons, area, area_moment, offset, scale):
        self.loops = [loop * scale for loop in loops]
        self.triangles = [np.array(triangle)*scale for triangle in triangles]
        self.area = area * scale**2
        self.area_moment = area_moment * scale**2
        self.offset = offset * scale
        self.convex_polygons = [np.array(convex) * scale for convex in convex_polygons]

class DrawnCharacter:
    def __init__(self, loops, units_per_em):
        self.units_per_em = units_per_em

        self.area = -sum(sum(util.cross2d(a, b) for a, b in zip(loop, np.roll(loop, 1, 0))) for loop in loops) / 2
        self.offset = -np.array([sum(sum((a[i]+b[i])*util.cross2d(a, b) for a, b in zip(loop, np.roll(loop, 1, 0))) for loop in loops) for i in range(2)]) / (6*self.area)
        self.loops = [np.array(loop) - self.offset for loop in loops]

        self.area_moment = -sum(sum(util.cross2d(a, b)*(sum(a**2)+np.dot(a, b)+sum(b**2)) for a, b in zip(loop, np.roll(loop, 1, 0))) for loop in self.loops) / (6*self.area)

        self.triangles = util.triangulate(self.loops)

        self.convex_polygons = []
        for loop in loops:
            if not util.check_winding(loop):
                try:
                    self.convex_polygons += [np.array(decomposition.convert_from(convex)) - self.offset for convex in decomposition.decompose(decomposition.convert_into(loop))]
                except Exception as e:
                    print('fail', loop)
                    raise e

    def get_size(self, fontsize):
        scale = fontsize / self.units_per_em
        return SizedDrawnCharacter(self.loops, self.triangles, self.convex_polygons, self.area, self.area_moment, self.offset, scale)

cache = {}
def get_unsized_character(char):
    if char not in cache:
        for font in FONTS:
            try:
                glyph_name = font.getBestCmap()[ord(char)]
                glyph = font.getGlyphSet()[glyph_name]
                break
            except KeyError:
                pass
        else:
            raise ValueError("Couldn't find character")

        pen = CustomPen()
        glyph.draw(pen)

        cache[char] = DrawnCharacter([[(x,-y) for x,y in loop] for loop in pen.loops], font['head'].unitsPerEm)
    return cache[char]

def calc_winding(pos, polygon):
    polygon = np.array(polygon) - pos

    test_ray = polygon[0]

    winding = 0

    for a, b in zip(polygon, np.roll(polygon, 1, 0)):
        if np.dot(a, test_ray) < 0 and np.dot(b, test_ray) < 0:
            continue

        winding += util.cross2d(test_ray, a) > 0
        winding -= util.cross2d(test_ray, b) > 0

    return winding

def point_in_char(char, size, pos):
    unsized_character = get_unsized_character(char)
    pos = np.array(pos) * (unsized_character.units_per_em / size)

    pos -= unsized_character.offset

    total_winding = sum(calc_winding(pos, loop) for loop in unsized_character.loops)

    return bool(total_winding % 2)

def create_character(char: str, size: float):
    return get_unsized_character(char).get_size(size)


base = join(dirname(__file__), 'fonts')
FONTS = [ttLib.TTFont(join(base, filename)) for filename in ('NotoSans-Regular.ttf', 'NotoSansSymbols-Regular.ttf', 'NotoSansSymbols2-Regular.ttf', 'NotoEmoji-Regular.ttf')]
del base
