import math, pathlib, sys, tempfile, unittest
root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from dv_analysis import analysis, demo, loader
from dv_analysis.mapbuilder import ConeMapper, match, to_map_frame


class T(unittest.TestCase):
    def test_frame_transform(self):
        x, y, c, d = to_map_frame([(2, 1, 1)], (10, 5, math.pi / 2), "car")[0]
        self.assertAlmostEqual(x, 9); self.assertAlmostEqual(y, 7); self.assertAlmostEqual(d, math.hypot(2, 1))

    def test_mapper_confirms_and_votes(self):
        m = ConeMapper()
        for col in (1, 1, 2):
            m.add(5.0, 5.0, col, 5)
        m.add(20, 20, 2, 5)
        conf, ghost = m.result()
        self.assertEqual(len(conf), 1); self.assertEqual(conf[0][2], 1); self.assertEqual(len(ghost), 1)

    def test_match(self):
        r = match([(0, 0, 1), (10, 10, 2), (50, 50, 1)], [(0.1, 0, 1), (10, 10.2, 1)])
        self.assertEqual(r["matched"], 2); self.assertAlmostEqual(r["recall"], 1.0); self.assertAlmostEqual(r["precision"], 2 / 3)
        self.assertAlmostEqual(r["color_acc"], 0.5)

    def test_end_to_end_demo_session(self):
        with tempfile.TemporaryDirectory() as d:
            p = demo.make(pathlib.Path(d) / "s.jsonl", seed=2, laps=3)
            meta, recs = loader.load(p)
            ok = analysis.analyze("s", meta, recs, latency=0.1)
            bad = analysis.analyze("s", meta, recs, latency=0.0)   # sem compensar a latência o mapa piora
        self.assertEqual(len(ok["lap_times"]), 2)
        self.assertGreater(ok["map_final"]["precision"], 0.9)
        self.assertGreater(ok["map_final"]["recall"], 0.9)
        self.assertLess(ok["map_final"]["rmse"], bad["map_final"]["rmse"] + 1e-9)
        self.assertLess(ok["steer"]["rms_err"], 2.0)


if __name__ == "__main__":
    unittest.main()
