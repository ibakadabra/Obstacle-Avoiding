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
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.srv import SetParameters, GetParameters
from std_srvs.srv import Empty

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

        self.done = False

        self.robot_cmd = np.array([sc['robot']['cmd']['v'], sc['robot']['cmd']['omega']])
        self.obstacle_vel = np.array(sc['obstacle']['velocity'])
        self.duration = float(sc['duration'])
        self.rate_hz = float(cfg.get('filter', {}).get('control_rate', 20.0))
        settle_time = float(sc.get('settle_time', 2.0))

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
        self._set_filter_params(
            mode=filt.get('mode', 'REACTIVE'),
            alpha=float(filt.get('alpha', 1.0)),
            t_horizon=float(filt.get('prediction_horizon', 0.0)))

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
        # gercekten set edilmiyordu (metadata idi) -- burada filtrenin CANLI
        # parametreleriyle EZILIYOR, boylece dump her zaman o kosuda
        # GERCEKTEN kullanilan degeri yansitir.
        live_geom = self._get_live_filter_geometry()
        if live_geom:
            cfg.setdefault('filter', {}).update(live_geom)

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

    def _set_filter_params(self, mode: str, alpha: float, t_horizon: float) -> None:
        client = self.create_client(SetParameters, '/safety_filter_node/set_parameters')
        if not client.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn(
                'safety_filter_node bulunamadi -- mode/alpha/t_horizon eski '
                'degerinde kaliyor (bu kosu METADATA ile GERCEK filtre '
                'davranisi arasinda TUTARSIZ olabilir!).')
            return
        req = SetParameters.Request()
        req.parameters = [
            Parameter('mode', Parameter.Type.STRING, mode).to_parameter_msg(),
            Parameter('alpha', Parameter.Type.DOUBLE, alpha).to_parameter_msg(),
            Parameter('t_horizon', Parameter.Type.DOUBLE, t_horizon).to_parameter_msg(),
        ]
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if not future.done() or future.result() is None:
            self.get_logger().warn('set_parameters cagrisi zaman asimina ugradi.')
            return
        for result, p in zip(future.result().results, req.parameters):
            if not result.successful:
                self.get_logger().warn(f'{p.name} ayarlanamadi: {result.reason}')
        self.get_logger().info(f'Filtre parametreleri: mode={mode} alpha={alpha} t_horizon={t_horizon}')

    def _get_live_filter_geometry(self) -> dict:
        """d_safe/contact_distance/lookahead_offset'i safety_filter_node'un
        SALT-OKUNUR parametrelerinden CANLI sorgular. Bunlar params.py
        sabitlerinden turer ve YAML'da hic bir zaman gercekten set edilmez
        -- amac, bag'in yanina yazilan config.yaml'in HER ZAMAN o kosuda
        GERCEKTEN kullanilan degeri yansitmasi, YAML dosyasinin (elle
        duzenlenebilen, potansiyel BAYAT) statik metnini degil. params.py
        degisirse (ornegin robot_radius duzeltmesi, Agu 2026) eski bag'ler
        kendi zamanlarindaki dogru degeri korur, yeni kosular yenisini alir
        -- karsilastirmalar bozulmaz."""
        client = self.create_client(GetParameters, '/safety_filter_node/get_parameters')
        if not client.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn(
                'safety_filter_node bulunamadi -- d_safe/contact_distance '
                'canli sorgulanamadi, config.yaml eski/statik degeri koruyacak.')
            return {}
        req = GetParameters.Request()
        req.names = ['d_safe', 'contact_distance', 'lookahead_offset']
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if not future.done() or future.result() is None:
            self.get_logger().warn('get_parameters cagrisi zaman asimina ugradi.')
            return {}
        values = {name: pv.double_value for name, pv in zip(req.names, future.result().values)}
        self.get_logger().info(f'Canli filtre geometrisi: {values}')
        return values

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
