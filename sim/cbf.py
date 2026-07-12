"""
Üç mod, TEK fark h ve ḣ'nin nasıl kurulduğu:

  REACTIVE : engel statik varsayılır  → ∂h/∂t terimi YOK
  DCBF     : zamanla değişen CBF      → ḣ'ye engel hız terimi (-2Δpᵀ·v_o) eklenir
  SHIFT    : engel konumu T ileri kaydırılır (p_o + v_o·T), sonra REACTIVE gibi

QP (lookahead formülasyonu, D1 kararına kadar):

  min_u  ‖u − u_nom‖²
  s.t.   2·Δpᵀ·G(θ)·u  ≥  −α·h  − (mod terimi)      # güvenlik (lineer!)
         0 ≤ v ≤ v_max,  |w| ≤ w_max                 # kutu kısıtları

  Δp = p_lookahead − p_o_effective
  h  = ‖Δp‖² − d_safe²
Infeasible ise: u_safe = [0, 0] (maks fren) döndür, feasible=False işaretle.
"""
from dataclasses import dataclass
from enum import Enum, auto
import numpy as np
from params import Config
import dynamics
import cvxpy as cp

class Mode(Enum):
    REACTIVE = auto()
    DCBF = auto()
    SHIFT = auto()


@dataclass
class FilterInfo:
    feasible: bool
    h: float                 # kısıt kurulurken kullanılan h değeri
    intervention: float      # ‖u_safe − u_nom‖
    active: bool             # kısıt aktif miydi (u değişti mi)
    


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
    if mode == Mode.SHIFT:
      p_obs_eff = np.array([
        x_o[0] + x_o[2] * cfg.filter.T_horizon,
        x_o[1] + x_o[3] * cfg.filter.T_horizon
    ])
    else:
        p_obs_eff = x_o[:2]
    delta_p = p_eff - p_obs_eff 
    if mode == Mode.DCBF:
        h_ek = -2 * delta_p @ x_o[2:]  
    else: 
        h_ek = 0.0
  
    d_safe = cfg.filter.d_safe(cfg.robot, cfg.obstacle)
    h = h_value(p_eff, p_obs_eff, d_safe)
    theta = x_r[2]
    G = dynamics.lookahead_velocity_matrix(theta, cfg.robot.lookahead)
 
    u = cp.Variable(2)
    objective = cp.Minimize(cp.sum_squares(u - u_nom))
    constraints = [
        2 * delta_p @ (G @ u) + h_ek >= -cfg.filter.alpha * h,
        u[0] >= cfg.robot.v_min,
        u[0] <= cfg.robot.v_max,
        cp.abs(u[1]) <= cfg.robot.w_max,
        ]
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.OSQP)

    if problem.status != "optimal":
        u_safe = np.array([0.0, 0.0])
        feasible = False
    else:
        u_safe = u.value
        feasible = True
    intervention = np.linalg.norm(u_safe - u_nom)
    active = intervention > 1e-6
    info = FilterInfo(feasible=feasible, h=h, intervention=intervention, active=active)

    return u_safe, info


