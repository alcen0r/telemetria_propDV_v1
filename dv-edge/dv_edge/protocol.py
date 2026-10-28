"""Protocolo da V2.0 (igual ao telemetry-edge): TCP, little-endian, 24 B/frame:
[len=20: u32][can_id: u32][timestamp: f64][payload: 8 B]  +  NTP simplificado (porta 9999)."""
import socket, struct, time, statistics

FRAME = struct.Struct("<IId8s")  # 4 + 4 + 8 + 8 = 24 bytes


def pack_frame(can_id: int, ts: float, data: bytes) -> bytes:
    return FRAME.pack(20, can_id, ts, bytes(data[:8]).ljust(8, b"\0"))


def unpack_frame(buf: bytes):
    ln, can_id, ts, data = FRAME.unpack(buf)
    assert ln == 20, f"tamanho inesperado: {ln}"
    return can_id, ts, data


def measure_clock_offset(host: str, port: int = 9999, samples: int = 10, timeout=1.0) -> float:
    """offset > 0 -> servidor adiantado. timestamp_corrigido = timestamp_local + offset."""
    offs = []
    for _ in range(samples):
        try:
            with socket.create_connection((host, port), timeout=timeout) as s:
                t1 = time.time()
                s.sendall(struct.pack("<d", t1))
                buf = b""
                while len(buf) < 16:
                    chunk = s.recv(16 - len(buf))
                    if not chunk:
                        raise OSError("fechou")
                    buf += chunk
                t4 = time.time()
            t2, t3 = struct.unpack("<dd", buf)
            offs.append(((t2 - t1) + (t3 - t4)) / 2)
        except OSError:
            continue
    return statistics.median(offs) if offs else 0.0
