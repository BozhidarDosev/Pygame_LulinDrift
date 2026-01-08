from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    # clamp 0..1
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


@dataclass
class TrackSegment:
    length: float
    curve: float  # отрицателно = ляво, положително = дясно


class Track:
    """
    Дава детерминистична функция curve(distance).
    Има "blend" зона в края на сегмента => завоите стават плавни.
    """
    def __init__(
        self,
        level_id: int,
        length: float,
        checkpoint_every: float,
        segments: List[Dict],
        *,
        blend_zone: float = 0.22,
        lookahead: float = 350.0,
        curve_scale_px: float = 280.0,
    ):
        self.level_id = level_id
        self.length = float(length)
        self.checkpoint_every = float(checkpoint_every)
        self.segments: List[TrackSegment] = [TrackSegment(float(s["length"]), float(s["curve"])) for s in segments]

        self.blend_zone = float(blend_zone)          # 0..1 (част от сегмента)
        self.lookahead = float(lookahead)            # units
        self.curve_scale_px = float(curve_scale_px)  # pixels

        # checkpoints list
        cps = []
        d = self.checkpoint_every
        while d < self.length:
            cps.append(d)
            d += self.checkpoint_every
        if not cps or cps[-1] != self.length:
            cps.append(self.length)
        self.checkpoints = cps

    def curve_at(self, dist: float) -> float:
        dist = max(0.0, min(dist, self.length))

        acc = 0.0
        for idx, seg in enumerate(self.segments):
            start = acc
            end = acc + seg.length
            if dist <= end:
                c0 = seg.curve
                c1 = c0
                if idx + 1 < len(self.segments):
                    c1 = self.segments[idx + 1].curve

                t = (dist - start) / max(1.0, seg.length)  # 0..1
                bs = 1.0 - self.blend_zone

                if t < bs or c0 == c1:
                    return c0

                u = (t - bs) / max(1e-6, self.blend_zone)
                u = smoothstep(u)
                return lerp(c0, c1, u)

            acc = end

        return 0.0

    def road_center_x(self, screen_w: int, distance: float, p: float) -> int:
        """
        p: 0..1 (0=далеч, 1=близо до колата)
        """
        p = 0.0 if p < 0.0 else (1.0 if p > 1.0 else p)
        dist_ahead = distance + (1.0 - p) * self.lookahead
        c = self.curve_at(dist_ahead)

        # far -> по-малко offset, near -> повече
        offset = int(c * (p ** 1.2) * self.curve_scale_px)
        return (screen_w // 2) + offset
