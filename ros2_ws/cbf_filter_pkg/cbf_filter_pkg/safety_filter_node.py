import time

import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64, String
from std_srvs.srv import Empty

from cbf_filter_pkg.cbf import Mode, safety_filter
from cbf_filter_pkg.params import Config


def yaw_from_quaternion(q):
    return np.arctan2(2.0 * (q.w * q.z + q.x * q.y),
                       1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class SafetyFilterNode(Node):
    def __init__(self):
        super().__init__('safety_filter_node')

        self.cfg = Config()
        self.cfg.filter.alpha = 1.0
        self.mode = Mode.REACTIVE
        self.x_r = None
        self.x_o = None

        self.sub_odom = self.create_subscription(
            Odometry, '/odom', self.on_odom, 10)

        self.sub_obstacle = self.create_subscription(
            Odometry, '/moving_obstacle/odom', self.on_obstacle_odom, 10)

        self.sub_cmd = self.create_subscription(
            Twist, '/cmd_vel_nom', self.on_cmd_nom, 10)

        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Teshis topic'leri (Oncelik 2, deney kosucusu spec'i)
        self.pub_h = self.create_publisher(Float64, '/safety_filter/h_value', 10)
        self.pub_qp_status = self.create_publisher(String, '/safety_filter/qp_status', 10)
        self.pub_solve_time = self.create_publisher(
            Float64, '/safety_filter/qp_solve_time_ms', 10)
        self.pub_cmd_nominal = self.create_publisher(
            Twist, '/safety_filter/cmd_vel_nominal', 10)

        # Oncelik 5: kosular arasi temiz durum. Filtre node'u kampanya boyunca
        # AYAKTA KALIYOR (her kosuda yeniden baslatilmiyor), bu yuzden onceki
        # kosunun son robot/engel pozu yeni kosunun ilk tick'lerine sizabilir
        # -- ozellikle engel silinip yeniden olusturulurken /moving_obstacle/odom
        # bir sure yayin yapmadigi icin x_o bayat kalir ve h(x) yanlis hesaplanir.
        self.srv_reset = self.create_service(
            Empty, '/safety_filter/reset', self.on_reset)

        self.get_logger().info('CBF safety filter node basladi (gercek engel modu)')

    def on_reset(self, request, response):
        self.x_r = None
        self.x_o = None
        self.get_logger().info('Ic durum sifirlandi (x_r, x_o = None).')
        return response

    def on_odom(self, msg: Odometry):
        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y
        theta = yaw_from_quaternion(msg.pose.pose.orientation)
        self.x_r = np.array([px, py, theta])

    def on_obstacle_odom(self, msg: Odometry):
        ox = msg.pose.pose.position.x
        oy = msg.pose.pose.position.y
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        self.x_o = np.array([ox, oy, vx, vy])

    def on_cmd_nom(self, msg: Twist):
        if self.x_r is None or self.x_o is None:
            return

        u_nom = np.array([msg.linear.x, msg.angular.z])

        t_start = time.perf_counter()
        u_safe, info = safety_filter(u_nom, self.x_r, self.x_o, self.mode, self.cfg)
        solve_time_ms = (time.perf_counter() - t_start) * 1000.0

        self.get_logger().info(
            f'x_o={self.x_o[:2]} h={info.h:.3f} feasible={info.feasible} '
            f'u_nom={u_nom} u_safe={u_safe}')

        out = Twist()
        out.linear.x = float(u_safe[0])
        out.angular.z = float(u_safe[1])
        self.pub.publish(out)

        self.pub_cmd_nominal.publish(msg)

        h_msg = Float64()
        h_msg.data = float(info.h)
        self.pub_h.publish(h_msg)

        status_msg = String()
        status_msg.data = 'feasible' if info.feasible else 'infeasible'
        self.pub_qp_status.publish(status_msg)

        solve_msg = Float64()
        solve_msg.data = float(solve_time_ms)
        self.pub_solve_time.publish(solve_msg)


def main():
    rclpy.init()
    node = SafetyFilterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
