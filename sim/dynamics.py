"""Görev 1a (İbrahim): unicycle ve engel kinematiği.

Durum ve girdi gösterimi (tüm projede sabit):
    x_r = np.array([px, py, theta])   # robot durumu (dünya çerçevesi)
    u   = np.array([v, w])            # girdi: ileri hız, dönüş hızı
    x_o = np.array([ox, oy, vx, vy])  # engel durumu (sabit hız modeli)
"""
import numpy as np


def unicycle_step(x_r: np.ndarray, u: np.ndarray, dt: float) -> np.ndarray:
    """Bir adım ilerlet: Euler entegrasyonu yeterli (dt=0.02).

    px' = px + v·cos(theta)·dt
    py' = py + v·sin(theta)·dt
    th' = theta + w·dt   (isteğe bağlı: [-pi, pi] aralığına sar)

    TODO(İbrahim): implement et. Girdiyi BURADA kırpma — sınır uygulaması
    filtrenin işi; dynamics saf kinematik kalsın.
    """
    raise NotImplementedError


def obstacle_step(x_o: np.ndarray, dt: float) -> np.ndarray:
    """Sabit hız modeli: konum += hız·dt, hız sabit.

    TODO(İbrahim): implement et.
    """
    raise NotImplementedError


def lookahead_point(x_r: np.ndarray, l: float) -> np.ndarray:
    """Lookahead noktası: p_l = p + l·[cos(theta), sin(theta)].

    Neden var: h'yi robot merkezine yazarsan ḣ'de w görünmez (relative degree
    sorunu). h'yi bu noktaya yazınca ṗ_l = R(theta)·[v, l·w] olur ve her iki
    girdi de kısıtta belirir → QP anlamlı.

    TODO(İbrahim): implement et.
    """
    raise NotImplementedError


def lookahead_velocity_matrix(theta: float, l: float) -> np.ndarray:
    """ṗ_l = G(theta) @ u olacak şekilde 2x2 G matrisi:

        G = [[cos(theta), -l·sin(theta)],
             [sin(theta),  l·cos(theta)]]

    TODO(İbrahim): implement et. (cbf.py'de kısıtı lineer yazmak için gerekli.)
    """
    raise NotImplementedError
