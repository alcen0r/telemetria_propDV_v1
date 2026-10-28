import math
import numpy as np
from . import mapbuilder as MB

AS_NAMES = {0: "—", 1: "AS Off", 2: "AS Ready", 3: "AS Driving", 4: "AS Finished", 5: "AS Emergency"}
LIM = dict(perc_lat_p95=100.0, precision=0.90, recall=0.90, rmse=0.25, color=0.95, steer_rms=2.0,
           steer_current=15.0, steer_temp=80.0)  # limites usados nos alertas (ajuste à vontade)


def _stats(v):
    v = np.asarray([x for x in v if x is not None], float)
    return dict(p50=float(np.percentile(v, 50)), p95=float(np.percentile(v, 95)), max=float(v.max())) if v.size else None


def _ds(a, n=600):
    a = list(a)
    if len(a) <= n:
        return a
    idx = np.linspace(0, len(a) - 1, n).astype(int)
    return [a[i] for i in idx]


def laps(recs):
    """(tempos de volta, instante do fim da volta 1). Usa mission.lap; se não mudar, usa o retorno à largada."""
    t0 = recs[0]["t"]
    marks, cur = [], recs[0]["mission"]["lap"]
    for r in recs:
        if r["mission"]["lap"] != cur:
            marks.append(r["t"]); cur = r["mission"]["lap"]
    if not marks:  # geométrico
        sx, sy, away = recs[0]["pose"]["x"], recs[0]["pose"]["y"], False
        for r in recs:
            d = math.hypot(r["pose"]["x"] - sx, r["pose"]["y"] - sy)
            away = away or d > 20
            if away and d < 6 and (not marks or r["t"] - marks[-1] > 5):
                marks.append(r["t"]); away = False
    times, prev = [], t0
    for m in marks:
        times.append(m - prev); prev = m
    return times, (marks[0] if marks else None)


def analyze(name, meta, recs, latency=0.1):
    t0 = recs[0]["t"]
    lap_times, lap1_end = laps(recs)
    (conf, ghost), (conf1, _), frames = MB.build(recs, meta, latency, lap1_end)
    ref, ref_label = meta.get("gt_cones") or [], "ground truth"
    if not ref:
        for r in reversed(recs):
            if r.get("map_cones"):
                ref, ref_label = r["map_cones"], "mapa publicado"; break
    mfin, mv1 = MB.match(conf, ref), MB.match(conf1, ref)
    perc_ms = [r["status"].get("perc_lat") for r in recs]
    measured = any((x or 0) > 0 for x in perc_ms)
    n_perc = [len(r["perc_cones"]) for r in recs]
    speed = [r["pose"]["speed"] for r in recs]
    st = [r for r in recs if r.get("steer")]
    steer = None
    if st:
        err = [r["control"]["steer_cmd"] - r["steer"]["angle"] for r in st]
        steer = dict(max_angle=max(abs(r["steer"]["angle"]) for r in st),
                     rms_err=float(np.sqrt(np.mean(np.square(err)))), p95_err=float(np.percentile(np.abs(err), 95)),
                     max_current=max(r["steer"]["current"] for r in st), max_temp=max(r["steer"]["temp"] for r in st))
    later = lap_times[1:] if len(lap_times) > 1 else []
    s = dict(
        name=name, duration=recs[-1]["t"] - t0, records=len(recs), frames=frames, latency_assumed=latency,
        lap_times=lap_times, lap1=lap_times[0] if lap_times else None, best_lap=min(lap_times) if lap_times else None,
        median_2plus=float(np.median(later)) if later else None,
        speed_mean=float(np.mean(speed)), speed_max=float(np.max(speed)),
        cones_per_frame=float(np.mean(n_perc)), perc_lat=_stats(perc_ms) if measured else None,
        map_lat=_stats([r["status"].get("map_lat") for r in recs]),
        as_state=AS_NAMES.get(recs[-1]["mission"]["as_state"], "—"),
        ref_label=ref_label, map_final=mfin, map_v1=mv1, n_ghost=len(ghost),
        n_confirmed=len(conf), steer=steer,
        series=dict(t=_ds([r["t"] - t0 for r in recs]), speed=_ds(speed),
                    cmd=_ds([r["control"]["steer_cmd"] for r in recs]),
                    angle=_ds([r["steer"]["angle"] if r.get("steer") else None for r in recs])),
        traj=_ds([(r["pose"]["x"], r["pose"]["y"]) for r in recs], 1200),
        built=[list(c) for c in conf], ghosts=[list(c) for c in ghost], ref=[list(c) for c in ref],
    )
    s["findings"] = findings(s, measured)
    return s


def findings(s, measured):
    f, mf = [], s["map_final"]
    def add(ok, title, body, metric):
        f.append(dict(status="ok" if ok else "open", title=title, body=body, metric=metric))
    add(bool(s["lap_times"]), "Contagem de voltas", "Voltas detectadas pelo estado da missão (ou retorno à largada).",
        f"{len(s['lap_times'])} voltas · melhor {s['best_lap']:.1f} s" if s["lap_times"] else "nenhuma volta fechada")
    if mf["rmse"] is not None:
        add(mf["precision"] >= LIM["precision"] and mf["recall"] >= LIM["recall"], "Mapa de cones vs " + s["ref_label"],
            "Cones confirmados com ≥3 detecções, casados em 1 m com a referência.",
            f"precisão {mf['precision']:.0%} · recall {mf['recall']:.0%} · RMSE {mf['rmse']:.2f} m · fantasmas {s['n_ghost']}")
        v1 = s["map_v1"]
        if v1["rmse"] is not None:
            add(v1["rmse"] <= LIM["rmse"], "Mapa da volta 1", f"Meta de referência (AMZ real): RMSE {LIM['rmse']:.2f} m.",
                f"RMSE v1 {v1['rmse']:.2f} m → final {mf['rmse']:.2f} m")
        if mf["color_acc"] is not None:
            add(mf["color_acc"] >= LIM["color"], "Cor dos cones", "Voto de cor ponderado por distância.", f"{mf['color_acc']:.0%}")
    if s["perc_lat"]:
        add(s["perc_lat"]["p95"] <= LIM["perc_lat_p95"], "Latência da percepção", "Medida pelo stamp da mensagem.",
            f"p50 {s['perc_lat']['p50']:.0f} ms · p95 {s['perc_lat']['p95']:.0f} ms")
    else:
        add(False, "Stamp nos cones da percepção", f"Sem header o mapa assume {s['latency_assumed']*1000:.0f} ms de latência "
            "(+0,2 m de RMSE no relatório do mapeamento). Pedir stamp de captura à Percepção.", "latência não medida")
    if s["steer"]:
        st = s["steer"]
        add(st["rms_err"] <= LIM["steer_rms"], "Seguimento do comando de steering", "RMS de (comando − ângulo real).",
            f"RMS {st['rms_err']:.2f}° · p95 {st['p95_err']:.2f}° · máx {st['max_angle']:.0f}°")
        add(st["max_current"] <= LIM["steer_current"] and st["max_temp"] <= LIM["steer_temp"], "Corrente e temperatura do steering",
            "Limites de alerta em analysis.py (LIM).", f"{st['max_current']:.1f} A máx · {st['max_temp']:.0f} °C máx")
    return f
