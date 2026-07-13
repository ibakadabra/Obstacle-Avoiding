"""Yol-kesme senaryosu ve sim döngüsü (Claude — altyapı).

Senaryo: robot (0,0)'dan (goal_x, 0)'a +x yönünde gider. Engel, robotun yolunu
dik kesecek şekilde yandan gelir; kesişme noktası ve zamanlaması, "müdahale
yoksa çarpışma olacak" biçimde kurulur (worst-case buluşma).

Nominal planlayıcı burada kasıtlı olarak aptal: sabit v_nom ile hedefe düz git
(pure pursuit'e bile gerek yok — filtrenin işini izole ölçüyoruz). Nav2/DWB
gerçekçiliği Faz 1'in işi.
"""
from dataclasses import dataclass, field

import numpy as np

import dynamics
from cbf import Mode, safety_filter, FilterInfo
from ekf import EKFParams, ObstacleEKF
from params import Config


@dataclass
class RunLog:
    """Tek koşunun ham kaydı — metrics.py bunu tüketir."""
    t: list = field(default_factory=list)
    x_r: list = field(default_factory=list)       # robot durumları
    x_o: list = field(default_factory=list)       # engel durumları (GERÇEK)
    x_o_filter_input: list = field(default_factory=list)  # filtrenin GÖRDÜĞÜ engel
    u_nom: list = field(default_factory=list)
    u_safe: list = field(default_factory=list)
    info: list = field(default_factory=list)      # FilterInfo listesi
    reached_goal: bool = False

    def as_arrays(self):
        return (np.array(self.t), np.array(self.x_r), np.array(self.x_o),
                np.array(self.u_nom), np.array(self.u_safe))


def make_crossing_scenario(cfg: Config, goal_x: float = 4.0):
    """Başlangıç durumlarını kur: engel, robotla aynı anda kesişme noktasına
    varacak şekilde yandan (+y'den) gelir.

    Kesişme noktası: robotun yolu üstünde x_c = goal_x/2.
    Robotun oraya varış süresi (nominal): t_c = x_c / v_max.
    Engel başlangıcı: (x_c, v_o·t_c), hızı (0, −v_o).
    """
    v_o = cfg.obstacle.speed
    x_c = goal_x / 2.0
    t_c = x_c / cfg.robot.v_max
    x_r0 = np.array([0.0, 0.0, 0.0])
    x_o0 = np.array([x_c, v_o * t_c, 0.0, -v_o])
    goal = np.array([goal_x, 0.0])
    return x_r0, x_o0, goal


def nominal_controller(x_r: np.ndarray, goal: np.ndarray, cfg: Config) -> np.ndarray:
    """Aptal nominal: hedefe dön ve tam gaz git (P kontrollü heading)."""
    dp = goal - x_r[:2]
    heading_err = np.arctan2(dp[1], dp[0]) - x_r[2]
    heading_err = np.arctan2(np.sin(heading_err), np.cos(heading_err))
    w = np.clip(2.0 * heading_err, -cfg.robot.w_max, cfg.robot.w_max)
    return np.array([cfg.robot.v_max, w])


def run_once(cfg: Config, mode: Mode, goal_x: float = 4.0,
             goal_tol: float = 0.10, use_ekf: bool = False,
             ekf_params: EKFParams = None) -> RunLog:
    """Tek koşu. Gecikme (tau_delay), filtreye ESKİ engel durumunu göstererek
    modellenir (ölçüm gecikmesi ≈ toplam zincir gecikmesi varsayımı, Faz 0).

    use_ekf=False (varsayılan): filtre GERÇEK (gecikmeli) engel durumunu görür
        — "mükemmel kestirim" ablasyon kolu.
    use_ekf=True: filtre yerine gürültülü KONUM ölçümünden EKF ile kestirilen
        [ox,oy,vx,vy] görür — gerçekçi kol. rng, cfg.sim.seed'den türetilir
        (tekrarlanabilir gürültü).
    """
    x_r0, x_o0, goal = make_crossing_scenario(cfg, goal_x)
    x_r, x_o = x_r0.copy(), x_o0.copy()
    log = RunLog()
    rng = cfg.rng()

    ekf = None
    if use_ekf:
        ekf = ObstacleEKF(params=ekf_params or EKFParams(dt=cfg.sim.dt))
        z0 = x_o0[:2] + rng.normal(0.0, ekf.params.sigma_z, 2)
        ekf.initialize(z0)

    delay_steps = int(round(cfg.sim.tau_delay / cfg.sim.dt))
    obs_buffer = [x_o0.copy()] * (delay_steps + 1)

    n_steps = int(cfg.sim.t_end / cfg.sim.dt)
    for k in range(n_steps):
        t = k * cfg.sim.dt
        obs_buffer.append(x_o.copy())
        x_o_seen = obs_buffer.pop(0)              # GERÇEK durumun gecikmeli hali

        if use_ekf:
            ekf.predict()
            z = x_o_seen[:2] + rng.normal(0.0, ekf.params.sigma_z, 2)
            ekf.update(z)
            x_o_filter_input = ekf.state()
        else:
            x_o_filter_input = x_o_seen

        u_nom = nominal_controller(x_r, goal, cfg)
        u_safe, info = safety_filter(u_nom, x_r, x_o_filter_input, mode, cfg)

        log.t.append(t)
        log.x_r.append(x_r.copy())
        log.x_o.append(x_o.copy())                # metrikler GERÇEK engelle hesaplanır
        log.x_o_filter_input.append(x_o_filter_input.copy())
        log.u_nom.append(u_nom)
        log.u_safe.append(u_safe)
        log.info.append(info)

        x_r = dynamics.unicycle_step(x_r, u_safe, cfg.sim.dt)
        x_o = dynamics.obstacle_step(x_o, cfg.sim.dt)

        if np.linalg.norm(goal - x_r[:2]) < goal_tol:
            log.reached_goal = True
            break

    return log
