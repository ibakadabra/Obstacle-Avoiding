"""
Dört mod, TEK fark h ve ḣ'nin nasıl kurulduğu:

  REACTIVE      : engel statik varsayılır  → ∂h/∂t terimi YOK
  DCBF          : zamanla değişen CBF      → ḣ'ye engel hız terimi (-2Δpᵀ·v_o) eklenir
  SHIFT         : engel konumu T ileri kaydırılır (p_o + v_o·T), sonra REACTIVE gibi
                  -- NAİF: Δp kaydırılmış noktaya göre hesaplanır ama ḣ'ye HİÇBİR
                  hız terimi eklenmez. Bu MATEMATİKSEL OLARAK EKSİK bir türev
                  (İŞ 4, Ağu 2026 -- "Sonraki Adımlar" spec'i): p_obs_eff = p_o+v_o·T
                  zamanla hareket ediyor (p_obs_eff_dot = v_o, v_o sabit varsayımıyla),
                  o yüzden Δp_dot = p_eff_dot − v_o olmalı, ama kod bunu atlıyor.
                  SADECE KARŞILAŞTIRMA AMACIYLA tutuluyor (SHIFT_CORRECT ile).
  SHIFT_CORRECT : SHIFT ile AYNI kaydırılmış Δp, ama DOĞRU türev:
                  Δp_dot = p_eff_dot − p_obs_eff_dot = G·u − v_o
                  ḣ = 2·Δp·(G·u − v_o) = 2·Δp·G·u − 2·Δp·v_o
                  Yani h_ek formu DCBF'le AYNI (-2·Δp·v_o), farkı Δp'nin
                  kaydırılmış noktaya göre hesaplanması. T_horizon=0 iken
                  p_obs_eff DCBF'inkiyle özdeşleşir -> SHIFT_CORRECT ve DCBF
                  matematiksel olarak AYNI QP'ye indirgenir (tutarlılık kontrolü,
                  kodun yapısından otomatik sağlanır).

QP (lookahead formülasyonu, D1 kararına kadar):

  min_u  ‖u − u_nom‖²
  s.t.   2·Δpᵀ·G(θ)·u  ≥  −α·h  − (mod terimi)      # güvenlik (lineer!)
         0 ≤ v ≤ v_max,  |w| ≤ w_max                 # kutu kısıtları

  Δp = p_lookahead − p_o_effective
  h  = ‖Δp‖² − d_safe²
Infeasible ise: u_safe = [0, 0] (maks fren) döndür, feasible=False işaretle.

SLACK'Lİ QP (cfg.filter.slack_enabled, İŞ 1, Ağu 2026): hard kısıt
infeasible olduğunda QP hiç çözüm üretmiyor, kritik hızda ölçülen "çöküş"
filtrenin fiziksel sınırını değil bu formülasyon boşluğunu ölçüyordu.
slack_enabled=True iken kısıta δ≥0 gevşeme terimi eklenir, maliyete
slack_rho·δ² cezası eklenir:

  min_u,δ  ‖u−u_nom‖² + ρ·δ²
  s.t.     2·Δpᵀ·G(θ)·u + h_ek  ≥  −α·h − δ
           δ ≥ 0,  box kısıtları (v/w limitleri, δ'dan bağımsız)

Kısıt sağlanabiliyorsa δ=0 ve çözüm hard versiyonla ÖZDEŞ. QP artık HER
ZAMAN çözülür (infeasible durumu ortadan kalkar); δ, ihlalin büyüklüğünü
ikiliden (feasible/infeasible) sürekliye çevirir.
"""
from dataclasses import dataclass
from enum import Enum, auto
import numpy as np
from .params import Config
from . import dynamics
import cvxpy as cp

class Mode(Enum):
    REACTIVE = auto()
    DCBF = auto()
    SHIFT = auto()          # NAİF -- bkz. modül docstring'i, İŞ 4
    SHIFT_CORRECT = auto()  # doğru türev -- bkz. modül docstring'i, İŞ 4


@dataclass
class FilterInfo:
    feasible: bool
    h: float                 # kısıt kurulurken kullanılan h değeri
    intervention: float      # ‖u_safe − u_nom‖
    active: bool             # kısıt aktif miydi (u değişti mi)
    delta: float = 0.0       # slack degeri (Agu 2026, İŞ 1) -- slack_enabled=False
                              # veya kisit zaten saglanabiliyorsa daima 0.0



def h_value(p_eff: np.ndarray, p_obs_eff: np.ndarray, d_safe: float) -> float:
    diff = p_eff - p_obs_eff
    dist_sq = diff @ diff          # dx*dx + dy*dy = dx² + dy²  (skaler!)
    return dist_sq - d_safe**2
  


def safety_filter(
    u_nom: np.ndarray,
    x_r: np.ndarray,
    x_o: np.ndarray,
    mode: Mode,
    cfg: Config) -> tuple[np.ndarray, FilterInfo]:
    
    p_eff = dynamics.lookahead_point(x_r, cfg.robot.lookahead)
    if mode in (Mode.SHIFT, Mode.SHIFT_CORRECT):
      p_obs_eff = np.array([
        x_o[0] + x_o[2] * cfg.filter.T_horizon,
        x_o[1] + x_o[3] * cfg.filter.T_horizon
    ])
    else:
        p_obs_eff = x_o[:2]
    delta_p = p_eff - p_obs_eff
    if mode in (Mode.DCBF, Mode.SHIFT_CORRECT):
        # DCBF: delta_p kaydirilmamis nokta uzerinden (p_obs_eff=x_o[:2]).
        # SHIFT_CORRECT: delta_p KAYDIRILMIS nokta uzerinden (yukarida
        # hesaplandi) -- ayni formul, farkli Δp girdisi.
        h_ek = -2 * delta_p @ x_o[2:]
    else:
        h_ek = 0.0
  
    d_safe = cfg.filter.d_safe(cfg.robot, cfg.obstacle)
    h = h_value(p_eff, p_obs_eff, d_safe)
    theta = x_r[2]
    G = dynamics.lookahead_velocity_matrix(theta, cfg.robot.lookahead)
 
    u = cp.Variable(2)
    if cfg.filter.cost_normalized:
        # İŞ 5.4-A: v ve ω'yu KENDI ARALIKLARINA gore olcekleyip agirlikli
        # topla -- eskiden v ve w mutlak degerleriyle ayni normda
        # karisiyordu (v araligi 0.22, w araligi 5.68 -- ~26x fark),
        # bu da filtreyi sistematik olarak "dur" secmeye itiyordu.
        v_range = cfg.robot.v_max - cfg.robot.v_min
        w_range = 2.0 * cfg.robot.w_max
        scale = np.array([1.0 / v_range, 1.0 / w_range])
        weights = np.array([cfg.filter.w_v, cfg.filter.w_w])
        scaled_diff = cp.multiply(scale, u - u_nom)
        cost_expr = cp.sum(cp.multiply(weights, cp.square(scaled_diff)))
    else:
        cost_expr = cp.sum_squares(u - u_nom)

    box_constraints = [
        u[0] >= cfg.robot.v_min,
        u[0] <= cfg.robot.v_max,
        cp.abs(u[1]) <= cfg.robot.w_max,
    ]

    if cfg.filter.slack_enabled:
        # SLACK'LI QP (İŞ 1, Agu 2026): guvenlik kisiti GEVSETILIR --
        # delta=0 saglanabiliyorsa cozum hard versiyonla OZDES (asagidaki
        # kisit delta=0 icin eskisiyle birebir ayni); saglanamiyorsa QP
        # yine de bir cozum uretir, delta ihlalin BUYUKLUGUNU tasir. Box
        # kisitlari (v/w limitleri) delta'dan BAGIMSIZ kalir -- slack
        # SADECE guvenlik kisitina uygulanir, aktuator limitlerine degil.
        delta = cp.Variable(nonneg=True)
        objective = cp.Minimize(cost_expr + cfg.filter.slack_rho * cp.square(delta))
        constraints = [
            2 * delta_p @ (G @ u) + h_ek >= -cfg.filter.alpha * h - delta,
        ] + box_constraints
    else:
        delta = None
        objective = cp.Minimize(cost_expr)
        constraints = [
            2 * delta_p @ (G @ u) + h_ek >= -cfg.filter.alpha * h,
        ] + box_constraints

    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.OSQP)

    if problem.status != "optimal":
        u_safe = np.array([0.0, 0.0])
        feasible = False
        delta_val = 0.0
    else:
        u_safe = u.value
        feasible = True
        delta_val = float(delta.value) if delta is not None else 0.0
    intervention = np.linalg.norm(u_safe - u_nom)
    active = intervention > 1e-6
    info = FilterInfo(feasible=feasible, h=h, intervention=intervention, active=active,
                       delta=delta_val)

    return u_safe, info


