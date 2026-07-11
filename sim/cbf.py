"""Görev 1b (İbrahim): CBF-QP güvenlik filtresi — tezin çekirdeği.

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


class Mode(Enum):
    REACTIVE = auto()
    DCBF = auto()
    SHIFT = auto()


@dataclass
class FilterInfo:
    """Her çağrının teşhis çıktısı — metrikler bunlardan hesaplanır."""
    feasible: bool
    h: float                 # kısıt kurulurken kullanılan h değeri
    intervention: float      # ‖u_safe − u_nom‖
    active: bool             # kısıt aktif miydi (u değişti mi)


def h_value(p_eff: np.ndarray, p_obs_eff: np.ndarray, d_safe: float) -> float:
    """h = ‖p_eff − p_obs_eff‖² − d_safe²

    TODO(İbrahim): implement et.
    """
    raise NotImplementedError


def safety_filter(
    u_nom: np.ndarray,
    x_r: np.ndarray,
    x_o: np.ndarray,
    mode: Mode,
    cfg: Config,
) -> tuple[np.ndarray, FilterInfo]:
    """u_nom'u güvenli hale getir (minimum müdahale).

    Adımlar:
      1. Moda göre efektif engel konumu ve ḣ ek terimini belirle:
         - REACTIVE: p_o_eff = x_o[:2],              ek terim = 0
         - SHIFT   : p_o_eff = x_o[:2] + x_o[2:]*T,  ek terim = 0
         - DCBF    : p_o_eff = x_o[:2],              ek terim = -2·Δpᵀ·x_o[2:]
           (ek terim güvenlik kısıtının SOL tarafına sabit olarak eklenir:
            2·Δpᵀ·G·u + ek_terim ≥ −α·h)
      2. Lookahead noktası ve G matrisi (dynamics.py'den).
      3. QP'yi kur ve çöz (ilk sürüm: cvxpy + OSQP backend).
      4. Çözümsüzse u_safe=[0,0], feasible=False.
      5. Engel sensör menzili dışındaysa (‖p_r−p_o‖ > cfg.sim.sensor_range):
         filtre devre dışı → u_nom aynen geçer, h=inf, active=False.

    TODO(İbrahim): implement et. Önce REACTIVE'i testlerden geçir,
    sonra DCBF ve SHIFT'i ekle (fark sadece 1. adımda).
    """
    raise NotImplementedError
