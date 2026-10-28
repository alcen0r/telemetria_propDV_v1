"""Estado compartilhado + codificadores periódicos (pose, status, missão, controle, cones)."""
import math, threading, time
from . import messages as M


class Hub:
    def __init__(self):
        self.lock = threading.Lock()
        self.pose = dict(x=0.0, y=0.0, yaw=0.0, speed=0.0)
        self.status = dict(map_lat=0.0, perc_lat=0.0)
        self.mission = dict(lap=0, as_state=0, mission=0, map_locked=0)
        self.control = dict(steer_cmd=0.0, speed_target=0.0)
        self.steer = None  # só preenchido no --mock (em carro real vem do CAN via telemetry-edge)
        self.map_cones, self.perc_cones = [], []   # listas de (x, y, cor)
        self._cur = {"MAP": [0] * M.SLOTS, "PERC": [0] * M.SLOTS}
        self.perc_frame = "car"      # "car": percepção no frame do carro (lidar_node); "map": já no mapa
        self.perc_seq = self.map_seq = 0
        self.gt_cones = []           # só no simulador

    # --- atualizações (chamadas pelas fontes: ROS2 ou mock) ---
    def set(self, **kw):
        with self.lock:
            for k, v in kw.items():
                cur = getattr(self, k)
                if isinstance(v, dict) and isinstance(cur, dict):
                    cur.update(v)
                else:
                    setattr(self, k, v)
            if "perc_cones" in kw:
                self.perc_seq += 1
            if "map_cones" in kw:
                self.map_seq += 1

    def perc_in_map(self):
        if self.perc_frame != "car":
            return self.perc_cones
        p = self.pose
        c, s = math.cos(p["yaw"]), math.sin(p["yaw"])
        return [(p["x"] + x * c - y * s, p["y"] + x * s + y * c, col) for x, y, col in self.perc_cones]

    def snapshot(self, include_map=False):
        """Estado cru (percepção no frame original) para o log de sessão."""
        with self.lock:
            d = dict(t=time.time(), pose=dict(self.pose), perc_seq=self.perc_seq, perc_cones=list(self.perc_cones),
                     status=dict(self.status), mission=dict(self.mission), control=dict(self.control),
                     steer=dict(self.steer) if self.steer else None, map_seq=self.map_seq)
            if include_map:
                d["map_cones"] = list(self.map_cones)
            return d

    # --- codificação ---
    def _cone_frames(self, kind):
        cones = self.map_cones if kind == "MAP" else self.perc_in_map()
        base = M.ID_MAP_BASE if kind == "MAP" else M.ID_PERC_BASE
        cur, frames = self._cur[kind], []
        for k in range(M.SLOTS):
            idxs = list(range(k, len(cones), M.SLOTS))
            if not idxs:
                continue
            i = idxs[cur[k] % len(idxs)]
            cur[k] += 1
            x, y, c = cones[i]
            p = f"DV_{kind}_{k:02d}"
            frames.append((base + k, M.encode(base + k, {f"{p}_IDX": i, f"{p}_X": x, f"{p}_Y": y,
                                                        f"{p}_COLOR": c, f"{p}_FLAGS": 1 if kind == "PERC" else 0})))
        return frames

    def frames(self, tick: int):
        """tick a 20 Hz. Retorna [(can_id, 8 bytes)]."""
        with self.lock:
            p, s, m, c = self.pose, self.status, self.mission, self.control
            out = [(M.ID_POSE, M.encode(M.ID_POSE, {"DV_POSE_X": p["x"], "DV_POSE_Y": p["y"],
                                                   "DV_POSE_YAW": p["yaw"], "DV_SPEED": p["speed"]})),
                   (M.ID_CONTROL, M.encode(M.ID_CONTROL, {"DV_STEER_CMD": c["steer_cmd"],
                                                         "DV_SPEED_TARGET": c["speed_target"]}))]
            if tick % 4 == 0:   # 5 Hz
                out.append((M.ID_STATUS, M.encode(M.ID_STATUS, {
                    "DV_MAP_CONES_N": len(self.map_cones), "DV_PERC_CONES_N": len(self.perc_cones),
                    "DV_MAP_LAT_MS": s["map_lat"], "DV_PERC_LAT_MS": s["perc_lat"]})))
            if tick % 10 == 0:  # 2 Hz
                out.append((M.ID_MISSION, M.encode(M.ID_MISSION, {
                    "DV_LAP": m["lap"], "DV_AS_STATE": m["as_state"], "DV_MISSION": m["mission"],
                    "DV_MAP_LOCKED": m["map_locked"]})))
            if self.steer:
                st = self.steer
                out.append((M.ID_STEER, M.encode(M.ID_STEER, {"STEER_ANGLE": st["angle"], "STEER_RPM": st["rpm"],
                                                              "STEER_CURRENT": st["current"], "STEER_TEMP": st["temp"]})))
            out += self._cone_frames("PERC")          # 20 Hz por slot
            if tick % 4 == 0:                          # mapa: 5 Hz por slot (mapa muda pouco)
                out += self._cone_frames("MAP")
        return out
