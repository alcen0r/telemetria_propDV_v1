
import threading
from std_msgs.msg import Float32MultiArray, String, Bool
CONE_STRIDE = 3  # [lateral, frente, classe]

TOPICS = {
    "perc_cones": "/lidar_node/cones",
    "map_cones": "/mapping/global_cones",
    "map_mode": "/mapping/mode",
    "lap_closed": "/mapping/lap_closed",
}


def run(hub, stop: threading.Event):
    import rclpy
    from rclpy.node import Node

    class DVNode(Node):
        def __init__(self):
            super().__init__("telemetria_dv_edge")

            # Percepção: cones no referencial do carro
            self.create_subscription(
                Float32MultiArray,
                TOPICS["perc_cones"],
                self.on_perc,
                10
            )

            # Mapeamento: cones no referencial global
            self.create_subscription(
                Float32MultiArray,
                TOPICS["map_cones"],
                self.on_map,
                10
            )

            # Estado do mapeamento
            self.create_subscription(
                String,
                TOPICS["map_mode"],
                self.on_map_mode,
                10
            )

            # Evento de fechamento de volta
            self.create_subscription(
                Bool,
                TOPICS["lap_closed"],
                self.on_lap_closed,
                10
            )

        def on_perc(self, m):
            d = m.data

            if len(d) % CONE_STRIDE != 0:
                self.get_logger().warning(
                    "Formato inválido em /lidar_node/cones"
                )
                return

            cones = [
                (d[i], d[i + 1], int(d[i + 2]))
                for i in range(0, len(d), CONE_STRIDE)
            ]

            hub.set(
                perc_cones=cones,
                perc_frame="car"
            )

        def on_map(self, m):
            d = m.data

            if len(d) % CONE_STRIDE != 0:
                self.get_logger().warning(
                    "Formato inválido em /mapping/global_cones"
                )
                return

            cones = [
                (d[i], d[i + 1], int(d[i + 2]))
                for i in range(0, len(d), CONE_STRIDE)
            ]

            hub.set(map_cones=cones)

        def on_map_mode(self, m):
            hub.set(
                mission=dict(mapping_mode=m.data)
            )

        def on_lap_closed(self, m):
            if m.data:
                hub.set(
                    mission=dict(
                        lap=hub.mission["lap"] + 1
                    )
                )

    hub.set(perc_frame="car")

    rclpy.init()
    node = DVNode()

    try:
        while rclpy.ok() and not stop.is_set():
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()
