"""Fonte real: assina os tópicos ROS2 do PipelineMapping2026 / Controle_DV_2026.
AJUSTAR (TODO): nomes de tópicos e tipos de mensagem. Cor do cone não existe em PoseArray;
se o pipeline publicar cor (ex.: MarkerArray ou msg própria), preencher em _cones()."""
import math, threading

CONE_STRIDE = 3  # TODO confirmar com a Percepção: [x, y, cor] por cone. Se vier [x, y] apenas, use 2 (cor = 0)

TOPICS = {  # TODO conferir com os repositórios da Jetson
    "odom": "/odom",
    "map_cones": "/mapping/cones",
    "perc_cones": "/lidar_node/cones",     # Float32MultiArray, sem header, FRAME DO CARRO (ver Telemetria do Mapeamento)
    "steer_cmd": "/control/steering_cmd",   # std_msgs/Float32 (graus)
    "speed_target": "/control/speed_target",  # std_msgs/Float32 (m/s)
    "lap": "/mission/lap",                   # std_msgs/Int32
    "as_state": "/mission/as_state",         # std_msgs/Int32
}


def run(hub, stop: threading.Event):
    import rclpy
    from rclpy.node import Node
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseArray
    from std_msgs.msg import Float32MultiArray
    from std_msgs.msg import Float32, Int32

    class DVNode(Node):
        def __init__(self):
            super().__init__("telemetria_dv_edge")
            self.create_subscription(Odometry, TOPICS["odom"], self.on_odom, 10)
            self.create_subscription(PoseArray, TOPICS["map_cones"], lambda m: self.on_cones(m, "map"), 10)
            self.create_subscription(Float32MultiArray, TOPICS["perc_cones"], self.on_perc, 10)
            self.create_subscription(Float32, TOPICS["steer_cmd"], lambda m: hub.set(control=dict(steer_cmd=m.data)), 10)
            self.create_subscription(Float32, TOPICS["speed_target"], lambda m: hub.set(control=dict(speed_target=m.data)), 10)
            self.create_subscription(Int32, TOPICS["lap"], lambda m: hub.set(mission=dict(lap=m.data)), 10)
            self.create_subscription(Int32, TOPICS["as_state"], lambda m: hub.set(mission=dict(as_state=m.data)), 10)

        def on_odom(self, m):
            q, p, v = m.pose.pose.orientation, m.pose.pose.position, m.twist.twist.linear
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
            hub.set(pose=dict(x=p.x, y=p.y, yaw=yaw, speed=math.hypot(v.x, v.y)))

        def on_cones(self, m, kind):  # mapa publicado pelo mapeamento (PoseArray, frame do mapa)
            cones = [(p.position.x, p.position.y, 0) for p in m.poses]
            lat = (self.get_clock().now().nanoseconds * 1e-9 - (m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)) * 1000
            hub.set(**{f"{kind}_cones": cones}, status={f"{kind}_lat": max(0.0, lat)})

        def on_perc(self, m):  # percepção: sem header => sem latência medida (a análise assume --latency)
            d, k = m.data, CONE_STRIDE
            cones = [(d[i], d[i + 1], int(d[i + 2]) if k > 2 else 0) for i in range(0, len(d) - k + 1, k)]
            hub.set(perc_cones=cones)

    hub.set(perc_frame="car")
    rclpy.init()
    node = DVNode()
    while rclpy.ok() and not stop.is_set():
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    rclpy.shutdown()
