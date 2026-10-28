"""Monta o mapa de cones a partir da percepção + pose (mesma ideia do ConeMapper do CarNode):
associação por posição, voto de cor, média ponderada pela distância e confirmação com N detecções."""
import math
import numpy as np


class PoseTrack:
    def __init__(self, recs):
        self.t = np.array([r["t"] for r in recs])
        self.x = np.array([r["pose"]["x"] for r in recs])
        self.y = np.array([r["pose"]["y"] for r in recs])
        self.yaw = np.unwrap(np.array([r["pose"]["yaw"] for r in recs]))

    def at(self, t):
        return (float(np.interp(t, self.t, self.x)), float(np.interp(t, self.t, self.y)),
                float(np.interp(t, self.t, self.yaw)))


class ConeMapper:
    def __init__(self, assoc=0.5, confirm=3):
        self.assoc, self.confirm = assoc, confirm
        self.xy, self.w = np.zeros((0, 2)), np.zeros(0)
        self.n, self.votes = np.zeros(0, int), np.zeros((0, 5))

    def add(self, x, y, color, dist):
        w, color = 1.0 / (1.0 + dist / 10.0), int(min(max(color, 0), 4))
        if len(self.w):
            d = np.hypot(self.xy[:, 0] - x, self.xy[:, 1] - y)
            i = int(d.argmin())
            if d[i] < self.assoc:
                tot = self.w[i] + w
                self.xy[i] = (self.xy[i] * self.w[i] + np.array([x, y]) * w) / tot
                self.w[i], self.n[i] = tot, self.n[i] + 1
                self.votes[i, color] += w
                return
        v = np.zeros(5); v[color] = w
        self.xy = np.vstack([self.xy, [x, y]]); self.w = np.append(self.w, w)
        self.n = np.append(self.n, 1); self.votes = np.vstack([self.votes, v])

    def result(self):
        """(confirmados [(x,y,cor)], fantasmas [(x,y,cor)])"""
        conf, ghost = [], []
        for i in range(len(self.w)):
            v = self.votes[i].copy()
            col = int(v[1:].argmax()) + 1 if v[1:].sum() > 0 else 0
            (conf if self.n[i] >= self.confirm else ghost).append((float(self.xy[i, 0]), float(self.xy[i, 1]), col))
        return conf, ghost


def to_map_frame(cones, pose, frame):
    """Converte cones da percepção para o frame do mapa. frame='car': x à frente, y à esquerda (ENU)."""
    x0, y0, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    out = []
    for x, y, col in cones:
        if frame == "car":
            out.append((x0 + x * c - y * s, y0 + x * s + y * c, col, math.hypot(x, y)))
        else:
            out.append((x, y, col, math.hypot(x - x0, y - y0)))
    return out


def build(recs, meta, latency=0.1, lap1_end=None, assoc=0.5, confirm=3):
    """Percorre as sessões e devolve (mapa_final, mapa_v1, n_frames). latency: s entre captura e chegada."""
    frame = meta.get("perc_frame", "car")
    pt, m = PoseTrack(recs), ConeMapper(assoc, confirm)
    last, frames, v1 = None, 0, None
    for r in recs:
        if lap1_end is not None and v1 is None and r["t"] >= lap1_end:
            v1 = m.result()
        if r["perc_seq"] == last:
            continue
        last = r["perc_seq"]
        frames += 1
        pose = pt.at(r["t"] - latency)
        for x, y, col, d in to_map_frame(r["perc_cones"], pose, frame):
            m.add(x, y, col, d)
    return m.result(), (v1 or m.result()), frames


def match(built, ref, tol=1.0):
    """Casamento 1:1 guloso por distância. Retorna dict de métricas do mapa contra a referência."""
    if not built or not ref:
        return dict(n_built=len(built), n_ref=len(ref), matched=0, precision=0.0, recall=0.0, rmse=None, color_acc=None)
    b, r = np.array([c[:2] for c in built]), np.array([c[:2] for c in ref])
    d = np.hypot(b[:, None, 0] - r[None, :, 0], b[:, None, 1] - r[None, :, 1])
    pairs = sorted((d[i, j], i, j) for i in range(len(b)) for j in range(len(r)) if d[i, j] < tol)
    ub, ur, errs, colok, colN = set(), set(), [], 0, 0
    for dist, i, j in pairs:
        if i in ub or j in ur:
            continue
        ub.add(i); ur.add(j); errs.append(dist)
        if ref[j][2] in (1, 2, 3, 4):
            colN += 1; colok += int(built[i][2] == ref[j][2])
    k = len(errs)
    return dict(n_built=len(built), n_ref=len(ref), matched=k, precision=k / len(built), recall=k / len(ref),
                rmse=float(np.sqrt(np.mean(np.square(errs)))) if k else None,
                color_acc=colok / colN if colN else None)
