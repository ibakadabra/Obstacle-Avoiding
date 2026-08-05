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
    # 0.1237 m: TB3 Burger'in gercek (dairesel OLMAYAN) govde kutusundan
    # (turtlebot3_description/urdf/turtlebot3_burger.urdf: collision box
    # 0.140x0.140, origin (-0.032,0,0.070)) turetilen EN KOTU DURUM (en uzak
    # kose) cevre-daire yaricapi:
    #   sqrt((0.032+0.070)^2 + 0.070^2) = 0.1237 m
    # Onceki deger (0.105 m, "~105mm" olarak dogrulanmadan yorumlanmisti)
    # gercek govdeden ~19 mm KUCUKTU -- d_safe'i gerekenden az konservatif
    # yapiyordu. Tekerlekler (y=+-0.08m, ustten gorunumde 0.033x0.018m
    # dikdortgen) kutudan daha az cikinti yapiyor, sinirlayici olan govde.
    radius: float = 0.1237       # m
    lookahead: float = 0.10      # m     (l — lookahead noktası ofseti; D1 kararına tabi)


@dataclass
class ObstacleParams:
    # moving_obstacle.sdf'teki silindir collision geometrisinden dogrulandi.
    radius: float = 0.25         # m     (insan bacağı/RC araba eşdeğeri)
    speed: float = 0.44          # m/s   (süpürmede değişir: 0.22/0.44/0.88/1.32)


@dataclass
class FilterParams:
    alpha: float = 1.0           # CBF sınıf-K katsayısı (D2: kalibre edilecek)
    d_margin: float = 0.05       # m     (ek güvenlik marjı — safety_margin)
    T_horizon: float = 0.0       # s     (SHIFT modunda öngörü ufku; 0 = reaktif eşdeğeri)
    # İŞ 5.4-A (Ağu 2026): QP maliyeti J=(v-v_nom)²+(ω-ω_nom)² NORMALIZE
    # EDILMEMISTI -- v araligi 0.22 m/s, ω araligi 5.68 rad/s (~26x fark).
    # Sonuc: tam durmak (Δv=0.22 → J=0.0484) ile 0.22 rad/s donmek (ayni J)
    # ESIT maliyetli, ama 1.0 rad/s donmek 20x pahali -- filtre pratikte hep
    # "dur" secip donusu es geciyordu (Teshis A: ω payi %8; İŞ2: donma
    # 9-10/10; Teshis B: geri-hareket testi bu artefaktla kirlenmis olabilir).
    # cost_normalized=True ise J=w_v·((v-v_nom)/v_range)²+w_w·((ω-ω_nom)/ω_range)²
    cost_normalized: bool = False   # False = eski (normalize edilmemis) davranis
    w_v: float = 1.0
    w_w: float = 1.0

    def contact_distance(self, robot: RobotParams, obs: ObstacleParams) -> float:
        """Merkez-merkez fiziksel temas mesafesi (govde+engel yaricaplari).
        d_safe'ten AYRI: bu tasarim parametresi degil, geometriden gelen sabit."""
        return robot.radius + obs.radius

    def d_safe(self, robot: RobotParams, obs: ObstacleParams) -> float:
        # KRITIK DUZELTME (Agu 2026): CBF kisiti govde merkezini degil,
        # LOOKAHEAD NOKTASINI (p_eff, govde merkezinden robot.lookahead=0.10m
        # ILERIDE) korur: h>=0, ||p_eff-p_o||>=d_safe garantiler. Onceki
        # formul (contact_distance+d_margin) bu ofseti HESABA KATMIYORDU --
        # en kotu durumda govde, kisit hala saglanirken lookahead
        # noktasindan robot.lookahead kadar geri kalabilir, yani temas
        # mumkun olabilir. Dogru formul lookahead ofsetini de payin icine
        # katar:
        #   d_safe = contact_distance + lookahead_offset + safety_margin
        #          = 0.3737 + 0.10 + 0.05 = 0.5237
        # (Olcum: REACTIVE modda ham merkez-merkez d_min=0.3553 iken h_min
        # hala ~0 civariydi -- kisit "saglaniyor" gorunurken govde zaten
        # contact_distance=0.3737'nin altina inmisti. Bu formul o acigi kapatir.)
        return self.contact_distance(robot, obs) + robot.lookahead + self.d_margin


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
