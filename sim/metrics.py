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
    raise NotImplementedError
