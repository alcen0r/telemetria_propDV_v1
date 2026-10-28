"""Telemetria DV (Jetson) -> telemetry-server da V2.0, mesmo protocolo do telemetry-edge.
  python3 -m dv_edge.main --mock --server 127.0.0.1:8080       # teste local (use tools/fake_server.py)
  python3 -m dv_edge.main --server 143.106.207.21:8080          # carro: ROS2 (source do setup.bash antes)
"""
import argparse, asyncio, logging, threading, time
from . import session_log
from .hub import Hub
from .protocol import measure_clock_offset
from .sender import Backup, Sender


async def amain(a):
    hub, stop = Hub(), threading.Event()
    if a.mock:
        from . import mock_source as src
    else:
        from . import ros_source as src
    threading.Thread(target=src.run, args=(hub, stop), daemon=True).start()
    if a.log_dir:
        threading.Thread(target=session_log.run, args=(hub, stop, a.log_dir), daemon=True).start()

    host = a.server.rsplit(":", 1)[0]
    offset = measure_clock_offset(host, a.ntp_port, a.ntp_samples) if a.ntp_port else 0.0
    logging.info("offset de clock: %+.3f ms", offset * 1000)

    queue = asyncio.Queue(maxsize=200_000)
    sender = Sender(a.server, Backup(a.db), a.batch)
    asyncio.create_task(sender.run(queue))

    tick, t_next = 0, time.monotonic()
    while True:
        now = time.time() + offset
        for cid, data in hub.frames(tick):
            if not queue.full():
                queue.put_nowait((now, cid, data))
        tick += 1
        if tick % 100 == 0:
            logging.info("enviados=%d fila=%d", sender.sent, queue.qsize())
        t_next += 0.05
        await asyncio.sleep(max(0.0, t_next - time.monotonic()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--server", default="143.106.207.21:8080", help="IP:porta do telemetry-server (TCP ingest)")
    p.add_argument("--ntp-port", type=int, default=9999, help="0 desliga a sincronização de clock")
    p.add_argument("--ntp-samples", type=int, default=10)
    p.add_argument("--db", default="dv_backup.db")
    p.add_argument("--batch", type=int, default=10)
    p.add_argument("--log-dir", default="sessions", help="grava sessões .jsonl p/ análise offline; '' desliga")
    p.add_argument("--mock", action="store_true")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    try:
        asyncio.run(amain(a))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
