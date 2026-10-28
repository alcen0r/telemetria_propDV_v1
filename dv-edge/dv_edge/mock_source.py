"""Fonte simulada em tempo real (veja sim.py)."""
import threading, time
from .sim import Track


def run(hub, stop: threading.Event):
    tr = Track()
    hub.set(perc_frame="car", map_cones=tr.published, gt_cones=tr.gt)
    t0, n = time.time(), 0
    while not stop.is_set():
        t = time.time() - t0
        pose, _ = tr.car(t)
        hub.set(pose=pose, **tr.control(t))
        if n % 5 == 0:                       # percepção a 10 Hz
            hub.set(perc_cones=tr.perception(t))
        n += 1
        time.sleep(0.02)
