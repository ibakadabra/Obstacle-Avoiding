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

Öncelik 5 (bu sürüm): her koşu başında dünya /reset_world ile sıfırlanır,
böylece robot orijine döner. Çözülen gerçek sorun: metrics_extractor'da
(Öncelik 4) ard arda koşuların d_min/h_min değerleri MONOTON ARTIYORDU --
robot hiç sıfırlanmadığı için her koşuya bir öncekinin bittiği yerden
başlıyor, engelden gitgide uzaklaşıyordu (7 koşuda d_min 0.36 -> 16.5 m).

Neden /reset_world (ölçülmüş karşılaştırma):
  - /gazebo/set_entity_state bu kurulumda YOK, ama /reset_world VAR
    (gazebo_ros_init eklentisi) -- ilk teşhiste sadece set_entity_state'e
    bakılıp bu atlanmıştı.
  - Ölçüldü: 0.37 s, sıfırlama hassasiyeti ~5e-5 m (yerleşme sonrası).
  - Denenen ve TERK EDİLEN alternatif: Gazebo'yu her koşuda pkill+yeniden
    başlatmak. Hem pahalı (~10-30 s/koşu, 640 koşuda saatler), hem de
    TEHLİKELİ: `pkill -f turtlebot3_gazebo` tmux SUNUCUSUNUN kendi komut
    satırıyla eşleşti (sunucu ilk kez o komutu içeren oturumla doğmuştu)
    ve tüm düzeneği (Gazebo + filtre node'u + senaryo) tek seferde öldürdü.
    Bu dosyada bir daha pkill KULLANILMAMALI.

Engel konumu sil+yeniden-oluştur ile ayarlanıyor (kanıtlanmış yöntem);
reset_world engeli de başlangıç noktasına döndürür ama biz yine de
yeniden oluşturuyoruz, çünkü başlangıç konumu senaryodan senaryoya değişir.

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
from nav_msgs.msg import Odometry
from cbf_filter_pkg import nominal_controller as nomctl
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.srv import SetParameters
from std_srvs.srv import Empty
from cbf_filter_pkg.params import Config as _Config

OBSTACLE_SDF_PATH = '/home/tusaslab7/tez_cbf/moving_obstacle.sdf'

BAG_TOPICS = [
    '/odom',
    '/moving_obstacle/odom',
    '/safety_filter/cmd_vel_nominal',
    '/cmd_vel',
    '/safety_filter/h_value',
    '/safety_filter/qp_status',
    '/safety_filter/qp_solve_time_ms',
    '/safety_filter/delta',   # İŞ 1 (Agu 2026): slack degeri
]


class ScenarioNode(Node):
    def __init__(self, config_path: str, bag_dir: str = None):
        super().__init__('scenario_node')

        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        sc = cfg['scenario']

        self.done = False

        self.robot_cmd = np.array([sc['robot']['cmd']['v'], sc['robot']['cmd']['omega']])
        self.obstacle_vel = np.array(sc['obstacle']['velocity'])
        self.duration = float(sc['duration'])
        self.rate_hz = float(cfg.get('filter', {}).get('control_rate', 20.0))
        settle_time = float(sc.get('settle_time', 2.0))

        # İŞ 5.4-B on kosulu 1 (Ağu 2026): nominal.type='goal_seeking' ise
        # sabit komut yerine engelden HABERSIZ, sadece hedefe donen oransal
        # kontrolcu kullanilir (nominal_controller.py). Varsayilan 'constant'
        # ESKI davranisla TAM UYUMLU (geriye donuk karsilastirma icin).
        self.nominal_cfg = cfg.get('nominal', {'type': 'constant'})
        self.x_r = None  # /odom'dan gelen [x,y,theta], sadece goal_seeking icin
        if self.nominal_cfg.get('type') == 'goal_seeking':
            self.sub_odom = self.create_subscription(Odometry, '/odom', self._on_odom, 10)

        self.pub_robot_cmd = self.create_publisher(Twist, '/cmd_vel_nom', 10)
        self.pub_obstacle_cmd = self.create_publisher(Twist, '/moving_obstacle/cmd_vel', 10)

        # Oncelik 5: dunya + filtre ic durumu sifirlanir. Engel yeniden
        # olusturulmadan ONCE yapilir (reset_world engeli de tasir).
        self._reset_state()

        # mode/alpha/prediction_horizon: YAML'daki filter: blogu daha once
        # SADECE metrics_extractor icin metadata idi, filtre node'unu
        # GERCEKTEN etkilemiyordu (kodda Mode.REACTIVE + alpha=1.0 hardcoded
        # idi). Standart /safety_filter_node/set_parameters servisiyle her
        # kosu bu degerleri gercekten uyguluyor -- mode sweep'inin anlamli
        # olmasi icin sart.
        filt = cfg.get('filter', {})
        lookahead_L = float(filt.get('lookahead_L', _Config().robot.lookahead))
        self._set_filter_params(
            mode=filt.get('mode', 'REACTIVE'),
            alpha=float(filt.get('alpha', 1.0)),
            t_horizon=float(filt.get('prediction_horizon', 0.0)),
            v_min=float(filt.get('v_min', 0.0)),
            cost_normalized=bool(filt.get('cost_normalized', False)),
            w_v=float(filt.get('w_v', 1.0)),
            w_w=float(filt.get('w_w', 1.0)),
            lookahead_L=lookahead_L,
            slack_enabled=bool(filt.get('slack_enabled', False)),
            slack_rho=float(filt.get('slack_rho', 500.0)),
            d_safe_mode=filt.get('d_safe_mode', 'derived'),
            d_safe_fixed=float(filt.get('d_safe_fixed', 0.5237)))

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
        #
        # d_safe/contact_distance/lookahead_offset ise YAML'da HICBIR ZAMAN
        # gercekten set edilmiyordu (metadata idi) -- burada params.py'nin
        # AYNI formuluyle (Config sinifi) YENIDEN HESAPLANIP yaziliyor,
        # boylece dump her zaman o kosuda GERCEKTEN kullanilan degeri
        # yansitir. Onceden bunu filtreden CANLI SORGULUYORDUK
        # (get_parameters) ama İŞ 5.4-D'de lookahead_L da settable oldugunda
        # d_safe'i SALT-OKUNUR bir ROS parametresi olarak tutmak (L
        # degisince bayatlar) yerine burada yerel hesap tercih edildi --
        # ayni formul, sorgu round-trip'i yok.
        geom_cfg = _Config()
        geom_cfg.robot.lookahead = lookahead_L
        geom_cfg.filter.d_safe_mode = filt.get('d_safe_mode', 'derived')
        geom_cfg.filter.d_safe_fixed = float(filt.get('d_safe_fixed', 0.5237))
        cfg.setdefault('filter', {}).update({
            'lookahead_offset': lookahead_L,
            'contact_distance': geom_cfg.filter.contact_distance(geom_cfg.robot, geom_cfg.obstacle),
            'd_safe': geom_cfg.filter.d_safe(geom_cfg.robot, geom_cfg.obstacle),
        })

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

    def _call_empty_service(self, name: str, timeout: float = 10.0) -> bool:
        """std_srvs/Empty servisini cagirir. __init__ icinden guvenli:
        spin_until_future_complete BURADA bir callback'in icinde DEGIL."""
        client = self.create_client(Empty, name)
        if not client.wait_for_service(timeout_sec=timeout):
            self.get_logger().warn(f'{name} servisi {timeout:.0f}s icinde bulunamadi.')
            return False
        future = client.call_async(Empty.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        if not future.done():
            self.get_logger().warn(f'{name} cagrisi zaman asimina ugradi.')
            return False
        return True

    def _set_filter_params(self, mode: str, alpha: float, t_horizon: float, v_min: float = 0.0,
                            cost_normalized: bool = False, w_v: float = 1.0, w_w: float = 1.0,
                            lookahead_L: float = 0.10, slack_enabled: bool = False,
                            slack_rho: float = 500.0, d_safe_mode: str = 'derived',
                            d_safe_fixed: float = 0.5237) -> None:
        client = self.create_client(SetParameters, '/safety_filter_node/set_parameters')
        if not client.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn(
                'safety_filter_node bulunamadi -- mode/alpha/t_horizon/v_min/cost/'
                'lookahead_L/slack parametreleri eski degerinde kaliyor (bu kosu METADATA '
                'ile GERCEK filtre davranisi arasinda TUTARSIZ olabilir!).')
            return
        req = SetParameters.Request()
        req.parameters = [
            Parameter('mode', Parameter.Type.STRING, mode).to_parameter_msg(),
            Parameter('alpha', Parameter.Type.DOUBLE, alpha).to_parameter_msg(),
            Parameter('t_horizon', Parameter.Type.DOUBLE, t_horizon).to_parameter_msg(),
            Parameter('v_min', Parameter.Type.DOUBLE, v_min).to_parameter_msg(),
            Parameter('cost_normalized', Parameter.Type.BOOL, cost_normalized).to_parameter_msg(),
            Parameter('w_v', Parameter.Type.DOUBLE, w_v).to_parameter_msg(),
            Parameter('w_w', Parameter.Type.DOUBLE, w_w).to_parameter_msg(),
            Parameter('lookahead_L', Parameter.Type.DOUBLE, lookahead_L).to_parameter_msg(),
            Parameter('slack_enabled', Parameter.Type.BOOL, slack_enabled).to_parameter_msg(),
            Parameter('slack_rho', Parameter.Type.DOUBLE, slack_rho).to_parameter_msg(),
            Parameter('d_safe_mode', Parameter.Type.STRING, d_safe_mode).to_parameter_msg(),
            Parameter('d_safe_fixed', Parameter.Type.DOUBLE, d_safe_fixed).to_parameter_msg(),
        ]
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if not future.done() or future.result() is None:
            self.get_logger().warn('set_parameters cagrisi zaman asimina ugradi.')
            return
        for result, p in zip(future.result().results, req.parameters):
            if not result.successful:
                self.get_logger().warn(f'{p.name} ayarlanamadi: {result.reason}')
        self.get_logger().info(
            f'Filtre parametreleri: mode={mode} alpha={alpha} t_horizon={t_horizon} '
            f'v_min={v_min} cost_normalized={cost_normalized} w_v={w_v} w_w={w_w} '
            f'lookahead_L={lookahead_L} slack_enabled={slack_enabled} slack_rho={slack_rho} '
            f'd_safe_mode={d_safe_mode} d_safe_fixed={d_safe_fixed}')

    def _reset_state(self) -> None:
        # Robotu once durdur: reset_world konumu sifirlar ama govdedeki
        # artik hiz sifirlanmadan reset yapilirsa robot orijinden birkac cm
        # kayarak duruyor (olculdu: ~2.8 cm). Sifir komut + kisa bekleme
        # ile bu kalinti ~5e-5 m'ye iniyor.
        self.pub_robot_cmd.publish(Twist())
        time.sleep(0.5)

        if self._call_empty_service('/reset_world'):
            self.get_logger().info('Dunya sifirlandi (/reset_world).')

        # Filtre node'unun IC durumu (son bilinen robot/engel pozu) ayri bir
        # sey: reset_world onu temizlemez, onceki koşunun bayat pozisyonlari
        # yeni koşunun ilk tick'lerine sizabilir.
        if self._call_empty_service('/safety_filter/reset', timeout=3.0):
            self.get_logger().info('Filtre ic durumu sifirlandi.')

        time.sleep(1.0)  # fizik motorunun oturmasi icin

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

    def _on_odom(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        theta = np.arctan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.x_r = np.array([p.x, p.y, theta])

    def _nominal_cmd(self) -> np.ndarray:
        """goal_seeking: engelden HABERSIZ, sadece /odom + sabit hedeften
        hesaplanir. constant (varsayilan): eski sabit komut."""
        if self.nominal_cfg.get('type') != 'goal_seeking':
            return self.robot_cmd
        if self.x_r is None:
            return np.array([0.0, 0.0])  # /odom henuz gelmedi, guvenli varsayilan
        gx, gy = self.nominal_cfg['goal']
        v_nom, w_nom = nomctl.goal_seeking_nominal(
            self.x_r[0], self.x_r[1], self.x_r[2], gx, gy,
            k_p=float(self.nominal_cfg.get('k_p', 1.5)),
            slowdown_radius=float(self.nominal_cfg.get('slowdown_radius', 0.5)),
            v_max=float(self.nominal_cfg.get('v_max', 0.22)),
            omega_max=float(self.nominal_cfg.get('omega_max', 2.84)))
        return np.array([v_nom, w_nom])

    def _tick(self) -> None:
        self.n_ticks += 1

        cmd = self._nominal_cmd()
        robot_msg = Twist()
        robot_msg.linear.x = float(cmd[0])
        robot_msg.angular.z = float(cmd[1])
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
