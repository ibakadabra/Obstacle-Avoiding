"""TB3 Burger ve simülasyon parametreleri — tek doğruluk kaynağı.

Kaynak: ROBOTIS e-Manual (Burger) + tez tanım dokümanı.
"""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class RobotParams:
    v_max: float = 0.22          # m/s   (donanım limiti)
    v_min: float = 0.0           # m/s   (geri gitmek yok — tez varsayımı, gerekirse gevşet)
    w_max: float = 2.84          # rad/s (donanım limiti)
    radius: float = 0.105        # m     (Burger footprint yarıçapı, ~105 mm)
    lookahead: float = 0.10      # m     (l — lookahead noktası ofseti; D1 kararına tabi)


@dataclass
class ObstacleParams:
    radius: float = 0.25         # m     (insan bacağı/RC araba eşdeğeri)
    speed: float = 0.44          # m/s   (süpürmede değişir: 0.22/0.44/0.88/1.32)


@dataclass
class FilterParams:
    alpha: float = 1.0           # CBF sınıf-K katsayısı (D2: kalibre edilecek)
    d_margin: float = 0.05       # m     (ek güvenlik marjı)
    T_horizon: float = 0.0       # s     (SHIFT modunda öngörü ufku; 0 = reaktif eşdeğeri)

    def d_safe(self, robot: RobotParams, obs: ObstacleParams) -> float:
        return robot.radius + obs.radius + self.d_margin


@dataclass
class SimParams:
    dt: float = 0.02             # s     (50 Hz — cmd_vel döngüsünden hızlı, sim için yeterli)
    t_end: float = 40.0          # s
    tau_delay: float = 0.0       # s     (algı+hesap+komut gecikmesi; süpürmede 0–0.4)
    sensor_range: float = 3.5    # m     (LDS-02 efektif menzil varsayımı; süpürme ekseni)
    seed: int = 0


@dataclass
class Config:
    robot: RobotParams = field(default_factory=RobotParams)
    obstacle: ObstacleParams = field(default_factory=ObstacleParams)
    filter: FilterParams = field(default_factory=FilterParams)
    sim: SimParams = field(default_factory=SimParams)

    def rng(self) -> np.random.Generator:
        return np.random.default_rng(self.sim.seed)
