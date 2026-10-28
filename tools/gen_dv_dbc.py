"""Gera telemetry-server/dbc_data/DV.dbc a partir de dv-edge/dv_edge/messages.py"""
import pathlib, sys
root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "dv-edge"))
from dv_edge.messages import MESSAGES

def num(x):
    return repr(int(x)) if float(x).is_integer() else repr(float(x))

lines = ['VERSION ""', "", "", "NS_ :", "", "BS_:", "", "BU_: DV", "", ""]
for cid in sorted(MESSAGES):
    name, sigs = MESSAGES[cid]
    lines.append(f"BO_ {cid} {name}: 8 DV")
    for n, sb, ln, signed, f, o, lo, hi, u in sigs:
        lines.append(f' SG_ {n} : {sb}|{ln}@1{"-" if signed else "+"} ({num(f)},{num(o)}) [{num(lo)}|{num(hi)}] "{u}" Vector__XXX')
    lines.append("")
out = root / "telemetry-server" / "dbc_data" / "DV.dbc"
out.write_text("\r\n".join(lines) + "\r\n")
print("gerado", out.relative_to(root), "-", len(MESSAGES), "mensagens")
