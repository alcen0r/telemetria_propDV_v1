"""Simulador simples (pista elíptica) usado pelo --mock e pelo gerador de sessões de demo.
Convenção: ENU, x à frente, y à esquerda no frame do carro. Percepção sai no FRAME DO CARRO."""
import math, random


class Track:
    def __init__(self, seed=1):
        self.rng = random.Random(seed)
        self.gt = []                                   # cones reais (x, y, cor) no frame do mapa
        for i in range(48):
            a = 2 * math.pi * i / 48
            self.gt.append((48 * math.cos(a), 28 * math.sin(a), 1))
            self.gt.append((72 * math.cos(a), 42 * math.sin(a), 2))
        r = random.Random(seed + 1)                    # mapa publicado pelo mapeamento: gt + erro 0.1 m
        self.published = [(x + r.gauss(0, .1), y + r.gauss(0, .1), c) for x, y, c in self.gt]

    def car(self, t):
        a = t * 0.3
        x, y = 60 * math.cos(a), 35 * math.sin(a)
        yaw = math.atan2(35 * math.cos(a), -60 * math.sin(a))
        return dict(x=x, y=y, yaw=yaw, speed=10 + 2 * math.sin(t)), a

    def perception(self, t):
        """Cones no frame do carro, como o lidar_node: alcance 0.9-20 m, FOV ±55°, ruído e 5% de cor errada."""
        p, _ = self.car(t)
        c, s = math.cos(p["yaw"]), math.sin(p["yaw"])
        out = []
        for gx, gy, col in self.gt:
            dx, dy = gx - p["x"], gy - p["y"]
            x, y = dx * c + dy * s, -dx * s + dy * c
            d = math.hypot(x, y)
            if 0.9 < d < 20 and abs(math.atan2(y, x)) < math.radians(55) and self.rng.random() < 1 - d / 40:
                if self.rng.random() < 0.05:
                    col = 3 - col
                out.append((x + self.rng.gauss(0, .05 + d * .004), y + self.rng.gauss(0, .05 + d * .004), col))
        return out

    def control(self, t):
        _, a = self.car(t)
        cmd = 25 * math.sin(2 * a)
        return dict(
            control=dict(steer_cmd=cmd, speed_target=11),
            steer=dict(angle=25 * math.sin(2 * a - 0.1) + self.rng.gauss(0, .15), rpm=300 * math.cos(2 * a),
                       current=4 + 2 * abs(math.sin(2 * a)), temp=40 + 4 * math.sin(t / 9)),
            mission=dict(lap=int(a / (2 * math.pi)) + 1, as_state=3, mission=2, map_locked=1),
            status=dict(map_lat=12 + 3 * math.sin(t), perc_lat=30 + 8 * math.sin(2 * t)))
