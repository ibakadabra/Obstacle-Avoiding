import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


class ObstacleChaserNode(Node):
    def __init__(self):
        super().__init__('obstacle_chaser_node')

        self.speed = 0.3
        self.x_r = None
        self.x_o = None

        self.sub_robot = self.create_subscription(
            Odometry, '/odom', self.on_robot_odom, 10)
        self.sub_obstacle = self.create_subscription(
            Odometry, '/moving_obstacle/odom', self.on_obstacle_odom, 10)
        self.pub = self.create_publisher(Twist, '/moving_obstacle/cmd_vel', 10)

        self.timer = self.create_timer(0.1, self.chase)

        self.get_logger().info('Obstacle chaser basladi (hedef: robotun canli konumu)')

    def on_robot_odom(self, msg: Odometry):
        self.x_r = np.array([msg.pose.pose.position.x, msg.pose.pose.position.y])

    def on_obstacle_odom(self, msg: Odometry):
        self.x_o = np.array([msg.pose.pose.position.x, msg.pose.pose.position.y])

    def chase(self):
        if self.x_r is None or self.x_o is None:
            return

        direction = self.x_r - self.x_o
        dist = np.linalg.norm(direction)
        if dist < 0.05:
            return

        unit = direction / dist
        vel = unit * self.speed

        out = Twist()
        out.linear.x = float(vel[0])
        out.linear.y = float(vel[1])
        self.pub.publish(out)


def main():
    rclpy.init()
    node = ObstacleChaserNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
