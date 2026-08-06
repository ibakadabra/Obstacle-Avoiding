import time

import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64, String
from std_srvs.srv import Empty
from rcl_interfaces.msg import SetParametersResult

from cbf_filter_pkg.cbf import Mode, safety_filter
from cbf_filter_pkg.params import Config


def yaw_from_quaternion(q):
    return np.arctan2(2.0 * (q.w * q.z + q.x * q.y),
                       1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class SafetyFilterNode(Node):
    def __init__(self):
        super().__init__('safety_filter_node')

        self.cfg = Config()
        self.x_r = None
        self.x_o = None

        # mode/alpha/T_horizon artik ROS parametreleri: daha once koda gomulu
        # (Mode.REACTIVE, alpha=1.0 hardcoded) idi, YAML config'lerdeki
        # filter.mode/alpha/prediction_horizon SADECE metrics_extractor icin
        # metadata olarak kaydediliyordu, filtreyi GERCEKTEN etkilemiyordu.
        # scenario_node artik her kosu oncesi standart /safety_filter_node/
        # set_parameters servisiyle bunlari YAML'daki degerlere gore ayarliyor.
        self.declare_parameter('mode', 'REACTIVE')
        self.declare_parameter('alpha', 1.0)
        self.declare_parameter('t_horizon', 0.0)
        # v_min: params.py'de 0.0 hardcoded idi ("tez varsayimi, gerekirse
        # gevset" yorumuyla) -- ROBOTIS donanim limiti DEGIL, bu projenin
        # kendi tasarim karari. İŞ 5.2 (Ağu 2026): dusuk hizda robot
        # bariyerde donuyor (Teshis A: L*w kacis kanali cok zayif). v_min<0
        # izin verilirse robot geri cekilerek h'yi arttirabilir mi test
        # ediliyor.
        self.declare_parameter('v_min', 0.0)
        # İŞ 5.4-A: QP maliyeti normalize edilebilir (bkz. params.py FilterParams,
        # cbf.py safety_filter). cost_normalized=False -> eski (normalize
        # edilmemis) davranis, geriye donuk karsilastirma icin varsayilan.
        self.declare_parameter('cost_normalized', False)
        self.declare_parameter('w_v', 1.0)
        self.declare_parameter('w_w', 1.0)
        # İŞ 5.4-D: lookahead_L artik SETTABLE (kafa-kafaya senaryoda yanal
        # gradyan uretmek icin kol uzunlugu taraniyor). d_safe = contact_dist
        # + lookahead + margin FORMULU L'ye bagli oldugu icin d_safe'i
        # ARTIK SALT-OKUNUR ROS parametresi olarak TUTMUYORUZ (L degisince
        # bayatlardi) -- scenario_node kendi tarafinda AYNI formulu
        # (params.py Config sinifi) kullanarak hesapliyor, sorguya gerek yok.
        self.declare_parameter('lookahead_L', self.cfg.robot.lookahead)
        # İŞ 1 (Agu 2026, "Slack'li QP" spec'i): guvenlik kisitini gevseten
        # slack degiskeni -- bkz. params.py FilterParams, cbf.py safety_filter.
        self.declare_parameter('slack_enabled', False)
        self.declare_parameter('slack_rho', 500.0)
        # İŞ 5: d_safe_mode='fixed' iken L degisse bile guvenlik tanimi
        # SABIT kalir -- bkz. params.py FilterParams.d_safe_mode.
        self.declare_parameter('d_safe_mode', 'derived')
        self.declare_parameter('d_safe_fixed', 0.5237)
        self.mode = Mode[self.get_parameter('mode').value]
        self.cfg.filter.alpha = self.get_parameter('alpha').value
        self.cfg.filter.T_horizon = self.get_parameter('t_horizon').value
        self.cfg.robot.v_min = self.get_parameter('v_min').value
        self.cfg.filter.cost_normalized = self.get_parameter('cost_normalized').value
        self.cfg.filter.w_v = self.get_parameter('w_v').value
        self.cfg.filter.w_w = self.get_parameter('w_w').value
        self.cfg.robot.lookahead = self.get_parameter('lookahead_L').value
        self.cfg.filter.slack_enabled = self.get_parameter('slack_enabled').value
        self.cfg.filter.slack_rho = self.get_parameter('slack_rho').value
        self.cfg.filter.d_safe_mode = self.get_parameter('d_safe_mode').value
        self.cfg.filter.d_safe_fixed = self.get_parameter('d_safe_fixed').value
        self.add_on_set_parameters_callback(self.on_param_change)

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
        # İŞ 1 (Agu 2026): slack degeri -- slack_enabled=False iken veya
        # kisit zaten saglanabiliyorken daima 0.0 yayinlanir; bu yuzden
        # topic'i her zaman ac (mod farki metrics_extractor tarafinda,
        # slack_enabled config metadata'siyla ayirt edilir).
        self.pub_delta = self.create_publisher(Float64, '/safety_filter/delta', 10)

        # Oncelik 5: kosular arasi temiz durum. Filtre node'u kampanya boyunca
        # AYAKTA KALIYOR (her kosuda yeniden baslatilmiyor), bu yuzden onceki
        # kosunun son robot/engel pozu yeni kosunun ilk tick'lerine sizabilir
        # -- ozellikle engel silinip yeniden olusturulurken /moving_obstacle/odom
        # bir sure yayin yapmadigi icin x_o bayat kalir ve h(x) yanlis hesaplanir.
        self.srv_reset = self.create_service(
            Empty, '/safety_filter/reset', self.on_reset)

        self.get_logger().info('CBF safety filter node basladi (gercek engel modu)')

    def on_param_change(self, params):
        for p in params:
            if p.name == 'mode':
                if p.value not in Mode.__members__:
                    return SetParametersResult(
                        successful=False,
                        reason=f'gecersiz mode: {p.value} (secenekler: {list(Mode.__members__)})')
                self.mode = Mode[p.value]
            elif p.name == 'alpha':
                self.cfg.filter.alpha = p.value
            elif p.name == 't_horizon':
                self.cfg.filter.T_horizon = p.value
            elif p.name == 'v_min':
                self.cfg.robot.v_min = p.value
            elif p.name == 'cost_normalized':
                self.cfg.filter.cost_normalized = p.value
            elif p.name == 'w_v':
                self.cfg.filter.w_v = p.value
            elif p.name == 'w_w':
                self.cfg.filter.w_w = p.value
            elif p.name == 'lookahead_L':
                self.cfg.robot.lookahead = p.value
            elif p.name == 'slack_enabled':
                self.cfg.filter.slack_enabled = p.value
            elif p.name == 'slack_rho':
                self.cfg.filter.slack_rho = p.value
            elif p.name == 'd_safe_mode':
                self.cfg.filter.d_safe_mode = p.value
            elif p.name == 'd_safe_fixed':
                self.cfg.filter.d_safe_fixed = p.value
        return SetParametersResult(successful=True)

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
            f'delta={info.delta:.4f} u_nom={u_nom} u_safe={u_safe}')

        out = Twist()
        out.linear.x = float(u_safe[0])
        out.angular.z = float(u_safe[1])
        self.pub.publish(out)

        self.pub_cmd_nominal.publish(msg)

        h_msg = Float64()
        h_msg.data = float(info.h)
        self.pub_h.publish(h_msg)

        delta_msg = Float64()
        delta_msg.data = float(info.delta)
        self.pub_delta.publish(delta_msg)

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
