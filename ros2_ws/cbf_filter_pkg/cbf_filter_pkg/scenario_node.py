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
    durdurma icin Oncelik 2'nin (/safety_filter/h_value) node icinde
    ABONE OLUNMASI gerekiyor (henuz yapilmadi, sadece disaridan kaydediliyor).

Öncelik 3 (bu sürüm): her koşu rosbag2 ile kaydedilir; Öncelik 2'nin teşhis
topic'leri (h_value, qp_status, qp_solve_time_ms, cmd_vel_nominal) olmadan
sonuç bag'inden h(x)/QP durumu analiz edilemezdi.

Kullanım:
    ros2 run cbf_filter_pkg scenario_node <config.yaml> [bag_output_dir]
    (bag_output_dir verilmezse ~/tez_cbf/results/<isim>_<zaman damgasi>)
"""
import os
import subprocess
import sys
import time

import numpy as np
import rclpy
import yaml
from geometry_msgs.msg import Twist
from rclpy.node import Node

OBSTACLE_SDF_PATH = '/home/tusaslab7/tez_cbf/moving_obstacle.sdf'

BAG_TOPICS = [
    '/odom',
    '/moving_obstacle/odom',
    '/safety_filter/cmd_vel_nominal',
    '/cmd_vel',
    '/safety_filter/h_value',
    '/safety_filter/qp_status',
    '/safety_filter/qp_solve_time_ms',
]


class ScenarioNode(Node):
    def __init__(self, config_path: str, bag_dir: str = None):
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

        if bag_dir is None:
            ts = time.strftime('%Y-%m-%d_%H-%M-%S')
            bag_dir = os.path.expanduser(
                f"~/tez_cbf/results/{sc.get('name', 'run')}_{ts}")
        self.bag_proc = subprocess.Popen(
            ['ros2', 'bag', 'record', '-o', bag_dir] + BAG_TOPICS,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'rosbag kaydi basladi: {bag_dir}')

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
            self._stop_bag()
            rclpy.shutdown()

    def _stop_bag(self) -> None:
        self.bag_proc.terminate()
        try:
            self.bag_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.bag_proc.kill()
        self.get_logger().info('rosbag kaydi durduruldu.')


def main():
    rclpy.init()
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'configs/lateral_offset.yaml'
    bag_dir = sys.argv[2] if len(sys.argv) > 2 else None
    node = ScenarioNode(config_path, bag_dir)
    # rclpy.spin(node) bir timer callback'i icinden gelen rclpy.shutdown()'i
    # her zaman hemen fark etmiyor (surec asilı kaliyor, PID canli kaliyor).
    # spin_once + rclpy.ok() dongusu her iterasyonda taze kontrol eder.
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()


if __name__ == '__main__':
    main()
