"""Minimal hedefe-yonelme nominal kontrolcusu (İŞ 5.4-B on kosulu 1, Ağu 2026).

Nav2/DWB DEGIL -- bilerek. Nav2 kendi engelden kacinmasini getirir, bu da
CBF filtresinin katkisiyla ayristirilamaz karisir. Bunun yerine engelden
TAMAMEN HABERSIZ, sadece sabit bir hedefe donen basit bir oransal kontrolcu:
kacinmanin TAMAMI filtreden gelir, nominal katman onu hic bilmez.

Onceki sabit-komut nominal ("hep v=0.22, omega=0") ile kars,ilastirinca fark:
robot kacindiktan sonra rotaya GERI DONEBILIR (bkz. İŞ5.2/5.4-A'da bulunan
"180 derece donup ters yone suruklenme" artefakti -- kokeni bu eksiklikti).
"""
import numpy as np


def wrap_to_pi(angle: float) -> float:
    return (angle + np.pi) % (2 * np.pi) - np.pi


def goal_seeking_nominal(x: float, y: float, theta: float,
                          x_goal: float, y_goal: float,
                          k_p: float, slowdown_radius: float,
                          v_max: float, omega_max: float) -> tuple[float, float]:
    """Engelden HABERSIZ, sadece (x_goal,y_goal)'a oransal yonelim.
    Donus: (v_nom, omega_nom)."""
    theta_err = wrap_to_pi(np.arctan2(y_goal - y, x_goal - x) - theta)
    omega_nom = float(np.clip(k_p * theta_err, -omega_max, omega_max))
    dist_to_goal = float(np.hypot(x_goal - x, y_goal - y))
    v_nom = v_max * float(np.clip(dist_to_goal / slowdown_radius, 0.0, 1.0))
    v_nom *= max(0.0, np.cos(theta_err))  # buyuk yonelim hatasinda yerinde don
    return v_nom, omega_nom
