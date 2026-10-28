#!/usr/bin/env python3
"""Cria o mapa (plotmap) a partir da percepção e analisa as sessões gravadas pelo dv-edge.
   python3 dv-analysis/plotmap.py sessions/*.jsonl -o relatorio_mapeamento
   python3 dv-analysis/plotmap.py --demo -o relatorio_demo          # sem carro, dados sintéticos
Saída: <out>/index.html (dashboard secundário), resumo.json e mapa_<sessão>.png"""
import argparse, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dv_analysis import analysis, dashboard, loader


def png(s, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {0: "gray", 1: "#d9a400", 2: "#1c6dd0", 3: "#ff8a3d", 4: "#ff5a1f"}
    fig, ax = plt.subplots(figsize=(7, 6))
    if s["traj"]:
        ax.plot(*zip(*s["traj"]), color="#7c4dd6", alpha=.5, lw=1.2, label="trajetória")
    if s["ref"]:
        ax.scatter(*zip(*[c[:2] for c in s["ref"]]), s=90, facecolors="none", edgecolors="gray", label=s["ref_label"])
    if s["built"]:
        ax.scatter([c[0] for c in s["built"]], [c[1] for c in s["built"]], c=[col.get(c[2], "gray") for c in s["built"]], s=18, label="mapa da percepção")
    if s["ghosts"]:
        ax.scatter(*zip(*[c[:2] for c in s["ghosts"]]), marker="x", c="red", s=20, label="fantasmas")
    ax.set_aspect("equal"); ax.set_title(f"Mapa · {s['name']}"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sessions", nargs="*")
    p.add_argument("-o", "--out", default="relatorio_mapeamento")
    p.add_argument("--latency", type=float, default=0.1, help="s entre captura e chegada da percepção (sem stamp)")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--no-png", action="store_true")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    paths = a.sessions
    if a.demo:
        from dv_analysis import demo
        paths = demo.make_all(os.path.join(a.out, "sessoes_demo"))
    if not paths:
        p.error("passe arquivos .jsonl ou use --demo")
    out = []
    for path in paths:
        meta, recs = loader.load(path)
        if len(recs) < 10:
            print("ignorada (poucos dados):", path); continue
        out.append(analysis.analyze(pathlib.Path(path).stem, meta, recs, a.latency))
        print(f"{path}: {len(recs)} amostras, {len(out[-1]['lap_times'])} voltas, "
              f"precisão {out[-1]['map_final']['precision']:.0%}, RMSE {out[-1]['map_final']['rmse']}")
    html = dashboard.render(out, dict(latency=a.latency, confirm=3))
    pathlib.Path(a.out, "index.html").write_text(html, encoding="utf-8")
    slim = [{k: v for k, v in s.items() if k not in ("series", "traj", "built", "ghosts", "ref")} for s in out]
    pathlib.Path(a.out, "resumo.json").write_text(json.dumps(slim, indent=1, ensure_ascii=False))
    if not a.no_png:
        try:
            for s in out:
                png(s, os.path.join(a.out, f"mapa_{s['name']}.png"))
        except ImportError:
            print("matplotlib ausente: PNGs não gerados")
    print("pronto:", os.path.join(a.out, "index.html"))


if __name__ == "__main__":
    main()
