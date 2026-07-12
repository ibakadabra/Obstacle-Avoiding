import numpy as np

px, py, theta = 0.0, 0.0, 0.0 # robot başlangıç durumu 
ox, oy, vx, vy = 1.0, 1.0, 0.0, 0.0 # engel başlangıç durumu
v, w = 0.5, 0.1 # robot girdi durumu (ileri hız, dönüş hızı)
dt = 0.02 # zaman adımı
    
x_r = np.array([px, py, theta])   # robot durumu (dünya çerçevesi)
u   = np.array([v, w])            # girdi: ileri hız, dönüş hızı
x_o = np.array([ox, oy, vx, vy])  # engel durumu (sabit hız modeli)



def unicycle_step(x_r: np.ndarray, u: np.ndarray, dt: float) -> np.ndarray:

    px, py, theta = x_r
    v, w = u

    pxi = px + v * np.cos(theta)*dt
    pyi = py + v * np.sin(theta) * dt
    thi = theta + w * dt

    return np.array([pxi, pyi, thi], dtype=float)



def obstacle_step(x_o: np.ndarray, dt: float) -> np.ndarray:
    ox, oy, vx, vy = x_o                      # diziyi 4 değişkene aç ("unpacking")
    return np.array([ox + vx*dt, oy + vy*dt, vx, vy])


def lookahead_point(x_r: np.ndarray, l: float) -> np.ndarray:
    px, py, theta = x_r
    px_l = px + l * np.cos(theta)
    py_l = py + l * np.sin(theta)
    return np.array([px_l, py_l])

def lookahead_velocity_matrix(theta: float, l: float) -> np.ndarray:
    G = np.array([
        [np.cos(theta), -l * np.sin(theta)],
        [np.sin(theta),  l * np.cos(theta)]
    ])
    return G
