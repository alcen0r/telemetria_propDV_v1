"""Servidor falso para testar sem o telemetry-server: TCP :8080 (ingest) + NTP :9999.
Decodifica os frames com o DV.dbc gerado e imprime um resumo por segundo."""
import asyncio, collections, pathlib, struct, sys, time
root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "dv-edge"))
from dv_edge import messages as M
from dv_edge.protocol import FRAME

counts, last = collections.Counter(), {}

async def ingest(r, w):
    try:
        while True:
            buf = await r.readexactly(FRAME.size)
            _, cid, ts, data = FRAME.unpack(buf)
            counts[cid] += 1
            if cid in M.MESSAGES:
                last[M.MESSAGES[cid][0]] = M.decode(cid, data)
    except asyncio.IncompleteReadError:
        pass

async def ntp(r, w):
    await r.readexactly(8)
    t = time.time()
    w.write(struct.pack("<dd", t, time.time()))
    await w.drain(); w.close()

async def report():
    while True:
        await asyncio.sleep(1)
        print(f"{sum(counts.values())} frames/s, {len(counts)} IDs | pose={ {k: round(v, 2) for k, v in last.get('DV_POSE', {}).items()} }")
        counts.clear()

async def main(port=8080):
    await asyncio.start_server(ingest, "0.0.0.0", port)
    await asyncio.start_server(ntp, "0.0.0.0", 9999)
    await report()

asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8080))
