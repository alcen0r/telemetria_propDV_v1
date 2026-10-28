"""Gera sessões sintéticas (mesmo formato do dv-edge) para testar a análise sem o carro.
A percepção é computada 100 ms ANTES da pose registrada, reproduzindo o problema de latência sem stamp."""
import json, math, os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "dv-edge"))
from dv_edge.sim import Track


def make(path, seed=1, laps=4, hz=10, cap_delay=0.1):
    tr, T = Track(seed), 2 * math.pi / 0.3 * laps
    n = int(T * hz)
    with open(path, "w") as f:
        f.write(json.dumps({"meta": {"perc_frame": "car", "gt_cones": tr.gt, "created": 0, "hz": hz}}) + "\n")
        for i in range(n):
            t, seq = i / hz, i
            pose, _ = tr.car(t)
            cap = tr.perception(max(0, t - cap_delay))
            rec = dict(t=1_700_000_000 + t, pose=pose, perc_seq=seq, perc_cones=cap, map_seq=1, **tr.control(t))
            rec["status"]["perc_lat"] = 0.0          # como no carro real: sem stamp, latência não medida
            if i % (2 * hz) == 0:
                rec["map_cones"] = tr.published
            f.write(json.dumps(rec) + "\n")
    return path


def make_all(folder, n=3):
    os.makedirs(folder, exist_ok=True)
    return [make(os.path.join(folder, f"demo_{i + 1}.jsonl"), seed=i + 1, laps=3 + i) for i in range(n)]
