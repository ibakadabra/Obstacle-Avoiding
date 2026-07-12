"""Görev 2 (İbrahim): koşu metrikleri.

Üç olay AYRI raporlanır (tez tanımı): infeasibility ≠ çarpışma ≠ mesafe ihlali.
"""
from dataclasses import dataclass

import numpy as np

from params import Config
from scenario import RunLog


@dataclass
class RunMetrics:
    collided: bool           # min mesafe < robot.radius + obstacle.radius (fiziksel temas)
    d_min: float             # merkezler arası minimum mesafe [m]
    infeasible_rate: float   # feasible=False olan adımların oranı [0,1]
    first_infeasible_t: float | None   # ilk infeasibility anı [s], yoksa None
    reached_goal: bool
    time_to_goal: float | None         # ulaştıysa süre [s], yoksa None
    intervention_int: float  # ∑‖u_safe−u_nom‖·dt  (toplam müdahale)
    intervention_peak: float # max ‖u_safe−u_nom‖


def compute_metrics(log: RunLog, cfg: Config) -> RunMetrics:
    """RunLog'dan metrikleri çıkar.

    Dikkat:
    - d_min ve çarpışma GERÇEK engel durumundan (log.x_o), filtrenin gördüğü
      gecikmiş durumdan DEĞİL.
    - Çarpışma eşiği fiziksel temas: robot.radius + obstacle.radius
      (d_safe DEĞİL — d_safe filtrenin hedefi, temas fiziğin gerçeği).

    TODO(İbrahim): implement et.
    """
    n = len(log.t)
    dt = cfg.sim.dt
    contact_thresh = cfg.robot.radius + cfg.obstacle.radius

    d_min = np.inf
    infeasible_count = 0
    first_infeasible_t = None
    intervention_int = 0.0
    intervention_peak = 0.0

    for k in range(n):
        distance = np.linalg.norm(log.x_r[k][:2] - log.x_o[k][:2])
        d_min = min(d_min, distance)
        if not log.info[k].feasible:
            infeasible_count += 1
            if first_infeasible_t is None:
                first_infeasible_t = log.t[k]
        intervention_int += log.info[k].intervention*dt
        intervention_peak = max(intervention_peak, log.info[k].intervention)

    return RunMetrics(
        collided=d_min < contact_thresh,
        d_min=d_min,
        infeasible_rate=infeasible_count / n,
        first_infeasible_t=first_infeasible_t,
        reached_goal=log.reached_goal,
        time_to_goal=log.t[-1] if log.reached_goal else None,
        intervention_int=intervention_int,
        intervention_peak=intervention_peak,
    )


