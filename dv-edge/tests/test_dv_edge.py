import math, pathlib, re, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dv_edge import messages as M
from dv_edge.hub import Hub
from dv_edge.protocol import pack_frame, unpack_frame

DBC = pathlib.Path(__file__).resolve().parents[2] / "telemetry-server" / "dbc_data" / "DV.dbc"


def rust_like_decode(dbc_text, can_id, data):
    """Reimplementa o parser/decoder do telemetry-server (decoder.rs) para validar o DV.dbc."""
    cur, out = None, {}
    raw = int.from_bytes(bytes(data), "little")
    for line in dbc_text.splitlines():
        t = line.strip()
        if t.startswith("BO_ "):
            cur = int(t.split()[1]) & 0x1FFFFFFF
        elif t.startswith("SG_ ") and cur == can_id:
            left, right = t[4:].split(":", 1)
            name = left.split()[0]
            m = re.match(r"\s*(\d+)\|(\d+)@1([+-]) \(([^,]+),([^)]+)\)", right)
            sb, ln, sg, f, o = int(m[1]), int(m[2]), m[3], float(m[4]), float(m[5])
            r = (raw >> sb) & ((1 << ln) - 1)
            if sg == "-" and r & (1 << (ln - 1)):
                r -= 1 << ln
            out[name] = r * f + o
    return out


class Tests(unittest.TestCase):
    def test_car_frame_to_map(self):
        h = Hub(); h.set(pose=dict(x=10, y=5, yaw=math.pi / 2), perc_cones=[(2, 1, 1)])
        x, y, c = h.perc_in_map()[0]
        self.assertAlmostEqual(x, 9); self.assertAlmostEqual(y, 7); self.assertEqual(c, 1)

    def test_roundtrip_all_messages_against_dbc(self):
        text = DBC.read_text()
        for cid, (_, sigs) in M.MESSAGES.items():
            vals = {s[0]: (s[7] * 0.4 if s[3] else s[7] * 0.3) for s in sigs}
            d = rust_like_decode(text, cid, M.encode(cid, vals))
            for n, v in vals.items():
                tol = [s for s in sigs if s[0] == n][0][4]
                self.assertAlmostEqual(d[n], v, delta=tol, msg=f"{hex(cid)} {n}")

    def test_negative_and_saturation(self):
        d = M.decode(M.ID_POSE, M.encode(M.ID_POSE, {"DV_POSE_X": -12.34, "DV_POSE_Y": 9999}))
        self.assertAlmostEqual(d["DV_POSE_X"], -12.34, places=2)
        self.assertAlmostEqual(d["DV_POSE_Y"], 327.67, places=2)

    def test_wire_format(self):
        buf = pack_frame(0x600, 123.5, b"\x01\x02")
        self.assertEqual(len(buf), 24)
        self.assertEqual(unpack_frame(buf), (0x600, 123.5, b"\x01\x02" + b"\0" * 6))

    def test_hub_cones_cover_all_and_throttle(self):
        h = Hub()
        h.set(map_cones=[(i, -i, 1 + i % 2) for i in range(40)])
        seen = set()
        for t in range(0, 4 * 5, 4):
            for cid, data in h.frames(t):
                if M.ID_MAP_BASE <= cid < M.ID_MAP_BASE + M.SLOTS:
                    k = cid - M.ID_MAP_BASE
                    seen.add(int(M.decode(cid, data)[f"DV_MAP_{k:02d}_IDX"]))
        self.assertEqual(seen, set(range(40)))

    def test_ids_do_not_collide_with_existing_dbcs(self):
        ids = set()
        for f in (DBC.parent).glob("*.dbc"):
            if f.name == "DV.dbc":
                continue
            for l in f.read_text(errors="ignore").splitlines():
                m = re.match(r"BO_ (\d+) ", l.strip())
                if m:
                    ids.add(int(m[1]) & 0x1FFFFFFF)
        self.assertFalse(ids & set(M.MESSAGES), ids & set(M.MESSAGES))


if __name__ == "__main__":
    unittest.main()
