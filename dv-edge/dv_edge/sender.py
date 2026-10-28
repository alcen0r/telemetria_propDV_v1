"""Envio TCP para o telemetry-server com reconexão e backup em SQLite (WAL) quando o link cai."""
import asyncio, logging, sqlite3, time
from .protocol import pack_frame

log = logging.getLogger("dv_edge.sender")


class Backup:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS pending(id INTEGER PRIMARY KEY, ts REAL, can_id INT, data BLOB)")
        self.db.commit()

    def add(self, rows):
        self.db.executemany("INSERT INTO pending(ts,can_id,data) VALUES(?,?,?)", rows)
        self.db.commit()

    def take(self, n=500):
        rows = self.db.execute("SELECT id,ts,can_id,data FROM pending ORDER BY id LIMIT ?", (n,)).fetchall()
        return rows

    def drop(self, last_id):
        self.db.execute("DELETE FROM pending WHERE id<=?", (last_id,))
        self.db.commit()

    def count(self):
        return self.db.execute("SELECT COUNT(*) FROM pending").fetchone()[0]


class Sender:
    def __init__(self, server: str, backup: Backup, batch=10):
        self.host, self.port = server.rsplit(":", 1)[0], int(server.rsplit(":", 1)[1])
        self.backup, self.batch = backup, batch
        self.sent = 0

    async def run(self, queue: asyncio.Queue):
        """queue recebe (timestamp_corrigido, can_id, data)."""
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                log.info("conectado a %s:%s (backlog=%d)", self.host, self.port, self.backup.count())
                asyncio.create_task(self._drain(reader))
                await self._flush_backup(writer)
                await self._loop(queue, writer)
            except (OSError, asyncio.IncompleteReadError, ConnectionError) as e:
                log.warning("link caiu (%s); gravando em SQLite e tentando de novo em 1 s", e)
                await self._offline(queue, 1.0)

    async def _drain(self, reader):  # o servidor pode mandar comandos; aqui só descartamos
        try:
            while await reader.read(4096):
                pass
        except Exception:
            pass

    async def _flush_backup(self, writer):
        while True:
            rows = self.backup.take()
            if not rows:
                return
            for _id, ts, cid, data in rows:
                writer.write(pack_frame(cid, ts, data))
            await writer.drain()
            self.backup.drop(rows[-1][0])

    async def _loop(self, queue, writer):
        buf = []
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.2)
                buf.append(item)
            except asyncio.TimeoutError:
                pass
            if buf and (len(buf) >= self.batch or queue.empty()):
                try:
                    for ts, cid, data in buf:
                        writer.write(pack_frame(cid, ts, data))
                    await writer.drain()
                    self.sent += len(buf)
                    buf = []
                except Exception:
                    self.backup.add([(ts, cid, bytes(d)) for ts, cid, d in buf])
                    raise

    async def _offline(self, queue, seconds):
        end = time.time() + seconds
        rows = []
        while time.time() < end:
            try:
                ts, cid, data = await asyncio.wait_for(queue.get(), timeout=0.1)
                rows.append((ts, cid, bytes(data)))
            except asyncio.TimeoutError:
                pass
        if rows:
            self.backup.add(rows)
