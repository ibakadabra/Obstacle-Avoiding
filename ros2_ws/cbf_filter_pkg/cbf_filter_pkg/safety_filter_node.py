import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

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

        self.get_logger().info('CBF safety filter node basladi (gercek engel modu)')

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
        u_safe, info = safety_filter(u_nom, self.x_r, self.x_o, self.mode, self.cfg)

        self.get_logger().info(
            f'x_o={self.x_o[:2]} h={info.h:.3f} feasible={info.feasible} '
            f'u_nom={u_nom} u_safe={u_safe}')

        out = Twist()
        out.linear.x = float(u_safe[0])
        out.angular.z = float(u_safe[1])
        self.pub.publish(out)


def main():
    rclpy.init()
    node = SafetyFilterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
