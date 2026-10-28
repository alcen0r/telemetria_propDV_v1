"""Grava sessões em JSONL (10 Hz) para a análise offline (dv-analysis/plotmap.py).
Linha 1: {"meta": ...}. Depois, um snapshot por linha; map_cones só quando muda (no máx. a cada 2 s)."""
import json, os, threading, time


def run(hub, stop: threading.Event, log_dir: str, hz: float = 10.0):
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, time.strftime("dv_%Y%m%d_%H%M%S.jsonl"))
    last_map_t, last_map_seq = 0.0, -1
    with open(path, "w") as f:
        meta = {"perc_frame": hub.perc_frame, "gt_cones": hub.gt_cones, "created": time.time(), "hz": hz,
                "note": "perc_frame=car: x à frente, y à esquerda (ENU)"}
        f.write(json.dumps({"meta": meta}) + "\n")
        while not stop.is_set():
            inc = hub.map_seq != last_map_seq and time.time() - last_map_t > 2
            snap = hub.snapshot(include_map=inc)
            if inc:
                last_map_t, last_map_seq = time.time(), snap["map_seq"]
            f.write(json.dumps(snap) + "\n")
            f.flush()
            time.sleep(1 / hz)
