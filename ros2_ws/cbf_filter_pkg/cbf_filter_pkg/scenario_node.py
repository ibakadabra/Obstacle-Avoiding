"""Senaryo düğümü — deterministik senkronizasyon (Öncelik 1).

Tek node, robot ve engel komutlarını AYNI timer callback'inden, aynı t0'dan
itibaren yayınlar. İki ayrı `ros2 topic pub` komutunu SSH üzerinden art arda
başlatmanın senkronizasyon garantisi VERMEDİĞİ (gözlenen gecikme: saniyeler-
dakikalar) sorununu yapısal olarak çözer.

v1 kısıtları (bilinçli, sonraki önceliklerde genişleyecek):
  - Sonlanma kriteri şimdilik sadece `duration` (zaman aşımı). h(x)<0 anlık
    durdurma icin Oncelik 2'nin (/safety_filter/h_value) node icinde
    ABONE OLUNMASI gerekiyor (henuz yapilmadi, sadece disaridan kaydediliyor).

Öncelik 3: her koşu rosbag2 ile kaydedilir; Öncelik 2'nin teşhis topic'leri
(h_value, qp_status, qp_solve_time_ms, cmd_vel_nominal) olmadan sonuç
bag'inden h(x)/QP durumu analiz edilemezdi.

Öncelik 5 (bu sürüm): her koşu Gazebo'yu TAMAMEN öldürüp yeniden başlatarak
robotu orijine sıfırlar. /gazebo/set_entity_state bu kurulumda YOK (sadece
init/factory/force_system eklentileri yüklü), bu yüzden ucuz bir "robotu
geri sür" alternatifi yerine kesin ama pahalı (~run başına birkaç saniye)
tam yeniden başlatma seçildi -- metrics_extractor'da (Öncelik 4) d_min/h_min
degerlerinin ard arda kosularda MONOTON ARTTIGI (robotun hic sifirlanmadigi)
gözlemiyle dogrulanan gercek bir kirlenme sorununu cozer. Engel konumu
sil+yeniden-oluştur ile ayarlanıyor (Gazebo restart sonrasi da gecerli
kanıtlanmış yöntem).

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
GAZEBO_LAUNCH_CMD = ['ros2', 'launch', 'turtlebot3_gazebo', 'empty_world.launch.py']
GAZEBO_KILL_PATTERNS = ['gzserver', 'gzclient', 'turtlebot3_gazebo']

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

        self.done = False

        self._restart_gazebo()

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

        # Cozumlenen config'in tam bir kopyasi bag'in YANINA (icine degil --
        # ros2 bag record zaten var olan bos bir dizini bile reddediyor)
        # yaziliyor. Amac: kampanya boyunca configs/*.yaml dosyalari elle
        # duzenlenebilir (nitekim bu oturumda oldu) -> metrics_extractor'in
        # her koşunun HANGI alpha/d_safe/rate ile calistigini config
        # dosyasinin O ANKI (belki degismis) haline degil, o koşu SIRASINDA
        # gecerli olan degerlere gore raporlamasi gerekir.
        with open(bag_dir + '_config.yaml', 'w') as f:
            yaml.safe_dump(cfg, f)

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

    def _restart_gazebo(self) -> None:
        self.get_logger().info(
            'Gazebo tamamen yeniden baslatiliyor (Oncelik 5: robot pozisyonu '
            'sifirlama -- /gazebo/set_entity_state bu kurulumda yok).')
        for pattern in GAZEBO_KILL_PATTERNS:
            subprocess.run(['pkill', '-9', '-f', pattern], capture_output=True)
        time.sleep(2.0)

        env = dict(os.environ)
        env.setdefault('TURTLEBOT3_MODEL', 'burger')
        # detach: parent (bu node) kisa omurlu, Gazebo run boyunca ve
        # sonrasinda BAGIMSIZ yasamali (bir sonraki kosu zaten pkill+relaunch
        # yapacak, o yuzden burada ozel bir kapatma/join mantigina gerek yok).
        self.gz_proc = subprocess.Popen(
            GAZEBO_LAUNCH_CMD, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)

        self._wait_for_odom(timeout=30.0)

    def _wait_for_odom(self, timeout: float) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.count_publishers('/odom') > 0:
                time.sleep(1.5)  # fizik motorunun ve TF'in oturmasi icin ek pay
                self.get_logger().info('Gazebo hazir (/odom yayinlaniyor).')
                return
            time.sleep(0.5)
        self.get_logger().warn(
            f'/odom {timeout:.0f}s icinde gorunmedi, yine de devam ediliyor '
            '(Gazebo baslatma basarisiz olmus olabilir).')

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
            # rclpy.shutdown() BURADA cagrilmiyor: spin_once()'un calistirdigi
            # bir callback'in icinden shutdown() cagirmak executor'un kendi
            # kendini beklemesine (deadlock) yol aciyor -> DEBUG print ile
            # dogrulandi, "shutdown() cagriliyor" sonrasi hicbir zaman geri
            # donmuyordu. Bunun yerine sadece bir bayrak set edilir; asil
            # shutdown() main()'in disaridaki dongusunde (callback CIKTIKTAN
            # SONRA) cagrilir.
            self.done = True

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
    # node.done, _tick() callback'i icinde set edilir. rclpy.shutdown() BURADA,
    # spin_once() cagrisi TAMAMEN DONDUKTEN SONRA (callback frame'inin disinda)
    # cagrilir -- callback'in kendi icinden shutdown() cagirmak executor'un
    # kendi kendini beklemesine (deadlock) yol aciyordu (DEBUG print ile
    # dogrulandi: "shutdown() cagriliyor" sonrasi hicbir zaman geri donmedi).
    while not node.done:
        rclpy.spin_once(node, timeout_sec=0.1)
    rclpy.shutdown()
    # node.destroy_node() BILEREK cagrilmiyor: destroy_node()'un kendisi
    # rmw_fastrtps discovery thread'leriyle iletisime gecmeye calisirken
    # futex'te asili kaliyor (py-spy ile dogrulandi, 22 non-daemon thread
    # sonsuza kadar bekliyor). Butun onemli temizlik (bag durdurma, sifir-
    # komut yayini) _tick()
    # icinde zaten tamamlandi -> os._exit() ile isletim sistemi seviyesinde
    # zorla kapatmak guvenli ve tek calisan cozum.
    os._exit(0)


if __name__ == '__main__':
    main()
