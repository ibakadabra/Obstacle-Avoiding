"""Senaryo düğümü — deterministik senkronizasyon (Öncelik 1).

Tek node, robot ve engel komutlarını AYNI timer callback'inden, aynı t0'dan
itibaren yayınlar. İki ayrı `ros2 topic pub` komutunu SSH üzerinden art arda
başlatmanın senkronizasyon garantisi VERMEDİĞİ (gözlenen gecikme: saniyeler-
dakikalar) sorununu yapısal olarak çözer.

v1 kısıtları (bilinçli, sonraki önceliklerde genişleyecek):
  - /gazebo/set_entity_state servisi bu kurulumda YOK (sadece init/factory/
    force_system eklentileri yüklü) -> robot konumu sıfırlanmıyor, Gazebo'nun
    HER KOŞU ÖNCESİ TAZE başlatılmış olduğu varsayılıyor (dogal spawn = orijin).
  - Engel konumu sil+yeniden-oluştur ile ayarlanıyor (kanıtlanmış yöntem).
  - Sonlanma kriteri şimdilik sadece `duration` (zaman aşımı). h(x)<0 anlık
    durdurma, teşhis topic'leri (Öncelik 2, /safety_filter/h_value) eklenince
    gelecek — o olmadan node'un h değerini bilmesinin yolu yok.

Kullanım:
    ros2 run cbf_filter_pkg scenario_node <config.yaml>
"""
import subprocess
import sys
import time

import numpy as np
import rclpy
import yaml
from geometry_msgs.msg import Twist
from rclpy.node import Node

OBSTACLE_SDF_PATH = '/home/tusaslab7/tez_cbf/moving_obstacle.sdf'


class ScenarioNode(Node):
    def __init__(self, config_path: str):
        super().__init__('scenario_node')

        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        sc = cfg['scenario']

        self.robot_cmd = np.array([sc['robot']['cmd']['v'], sc['robot']['cmd']['omega']])
        self.obstacle_vel = np.array(sc['obstacle']['velocity'])
        self.duration = float(sc['duration'])
        self.rate_hz = float(cfg.get('filter', {}).get('control_rate', 20.0))
        settle_time = float(sc.get('settle_time', 2.0))

        self.pub_robot_cmd = self.create_publisher(Twist, '/cmd_vel_nom', 10)
        self.pub_obstacle_cmd = self.create_publisher(Twist, '/moving_obstacle/cmd_vel', 10)

        obs_start = sc['obstacle']['start']
        self.get_logger().info(f'Engel yeniden konumlandiriliyor: {obs_start}')
        self._respawn_obstacle(obs_start)

        self.get_logger().info(f'{settle_time:.1f}s sistem oturmasi bekleniyor...')
        time.sleep(settle_time)

        self.n_ticks = 0
        self.max_ticks = int(round(self.duration * self.rate_hz))
        self.t0 = self.get_clock().now()
        self.get_logger().info(
            f'SENKRON BASLADI  t0={self.t0.nanoseconds / 1e9:.3f}s  '
            f'sure={self.duration}s  hiz={self.rate_hz}Hz  '
            f'robot_cmd={self.robot_cmd}  obstacle_vel={self.obstacle_vel}')

        self.timer = self.create_timer(1.0 / self.rate_hz, self._tick)

    def _respawn_obstacle(self, start) -> None:
        subprocess.run(
            ['ros2', 'service', 'call', '/delete_entity', 'gazebo_msgs/srv/DeleteEntity',
             "{name: 'moving_obstacle'}"],
            capture_output=True, timeout=10)
        time.sleep(0.5)
        subprocess.run(
            ['ros2', 'run', 'gazebo_ros', 'spawn_entity.py',
             '-entity', 'moving_obstacle',
             '-file', OBSTACLE_SDF_PATH,
             '-x', str(start[0]), '-y', str(start[1]), '-z', '0.25'],
            capture_output=True, timeout=15)

    def _tick(self) -> None:
        self.n_ticks += 1

        robot_msg = Twist()
        robot_msg.linear.x = float(self.robot_cmd[0])
        robot_msg.angular.z = float(self.robot_cmd[1])
        self.pub_robot_cmd.publish(robot_msg)

        obs_msg = Twist()
        obs_msg.linear.x = float(self.obstacle_vel[0])
        obs_msg.linear.y = float(self.obstacle_vel[1])
        self.pub_obstacle_cmd.publish(obs_msg)

        if self.n_ticks >= self.max_ticks:
            self.get_logger().info(f'SENARYO BITTI (timeout, {self.n_ticks} tick)')
            self.pub_obstacle_cmd.publish(Twist())
            self.pub_robot_cmd.publish(Twist())
            self.timer.cancel()
            rclpy.shutdown()


def main():
    rclpy.init()
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'configs/lateral_offset.yaml'
    node = ScenarioNode(config_path)
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass


if __name__ == '__main__':
    main()
