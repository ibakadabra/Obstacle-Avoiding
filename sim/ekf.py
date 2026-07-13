"""Görev 3 (İbrahim): Engel takip filtresi — sabit-hız Kalman filtresi.

Durum:  x = [ox, oy, vx, vy]  (engel konumu + hızı)
Ölçüm:  z = [ox, oy]          (Faz 0: gürültülü konum; Faz 1'de lidar kümesinin
                               merkezi buraya bağlanacak)

Model (ayrık, dt sabit):
    x[k+1] = F @ x[k] + w,   w ~ N(0, Q)     süreç gürültüsü
    z[k]   = H @ x[k] + v,   v ~ N(0, R)     ölçüm gürültüsü

    F = [[1, 0, dt, 0],          H = [[1, 0, 0, 0],
         [0, 1, 0, dt],               [0, 1, 0, 0]]
         [0, 0, 1,  0],
         [0, 0, 0,  1]]

NOT (KF vs EKF): Bu model tamamen LİNEER olduğu için bu dosyadaki filtre
aslında düz bir KF. "EKF" adı, Faz 1'de ölçüm lidar'dan menzil-açı (range,
bearing) olarak gelirse hak edilecek — o zaman update adımındaki H yerine
ölçüm fonksiyonunun Jacobian'ı geçer. Arayüz buna göre tasarlandı.
"""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class EKFParams:
    dt: float = 0.02
    sigma_a: float = 0.5      # süreç gürültüsü: engelin "görünmez ivmesi" [m/s²]
    sigma_z: float = 0.05     # ölçüm gürültüsü std'si [m] (Faz 0 sentetik)
    P0_pos: float = 0.5       # başlangıç konum belirsizliği (kovaryans köşegeni)
    P0_vel: float = 1.0       # başlangıç hız belirsizliği


@dataclass
class ObstacleEKF:
    """predict() ve update() çağrıları arasında durumu (x, P) taşır."""
    params: EKFParams
    x: np.ndarray = field(default=None)   # (4,)  kestirim
    P: np.ndarray = field(default=None)   # (4,4) kovaryans

    def initialize(self, z0: np.ndarray) -> None:
        """İlk ölçümle başlat: konum = z0, hız = 0 (bilinmiyor).

        P0: konum köşegeni P0_pos, hız köşegeni P0_vel — hıza güvenmiyoruz,
        büyük belirsizlik.

        TODO(İbrahim): implement et.
        
        """
        self.x = np.array([z0[0], z0[1], 0.0, 0.0])
        self.P = np.diag([
        self.params.P0_pos, self.params.P0_pos,
        self.params.P0_vel, self.params.P0_vel
    ])
    

    def predict(self) -> None:
        """Zaman güncellemesi (ölçümsüz ilerletme):

            x ← F @ x
            P ← F @ P @ F.T + Q

        Q (süreç gürültüsü, beyaz ivme modeli):
            Q = sigma_a² * [[dt⁴/4, 0,     dt³/2, 0    ],
                            [0,     dt⁴/4, 0,     dt³/2],
                            [dt³/2, 0,     dt²,   0    ],
                            [0,     dt³/2, 0,     dt²  ]]

        """
        
        dt = self.params.dt
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ])
        sigma_a = self.params.sigma_a
        Q = sigma_a**2 * np.array([
            [dt**4/4, 0,       dt**3/2, 0      ],
            [0,       dt**4/4, 0,       dt**3/2],
            [dt**3/2, 0,       dt**2,   0      ],
            [0,       dt**3/2, 0,       dt**2  ],
        ])

        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q


    def update(self, z: np.ndarray) -> None:
        H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ])
        R = self.params.sigma_z**2 * np.eye(2)

        y = z - H @ self.x
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)

        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ H) @ self.P

    def state(self) -> np.ndarray:
        """cbf.safety_filter'ın beklediği x_o formatında döndür: [ox,oy,vx,vy]."""
        return self.x.copy()
