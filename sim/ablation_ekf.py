"""Ablasyon: 'mukemmel durum bilgisi' vs 'EKF kestirimi' filtre performansina
ne kadar etki ediyor? + EKF tutarlilik kontrolu (yenilik/NIS).

Kullanim:  cd tez_cbf/sim && python ablation_ekf.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cbf import Mode
from ekf import EKFParams, ObstacleEKF
from metrics import compute_metrics
from params import Config
from scenario import run_once


def run_pair(v_o, mode=Mode.DCBF, seed=0):
    cfg = Config()
    cfg.obstacle.speed = v_o
    cfg.sim.seed = seed

    log_perfect = run_once(cfg, mode, use_ekf=False)
    m_perfect = compute_metrics(log_perfect, cfg)

    log_ekf = run_once(cfg, mode, use_ekf=True)
    m_ekf = compute_metrics(log_ekf, cfg)

    return m_perfect, m_ekf, log_ekf


def nis_consistency_check(log_ekf, cfg):
    """Yenilik tutarliligi: y=z-Hx her adimda ne kadar 'saskin' olmali,
    S bunu ne kadar dogru tahmin ediyor? NIS = y.T @ inv(S) @ y.
    2 boyutlu olcumde (H: 2x4), saglikli bir filtrede NIS'in ortalamasi ~2
    civarinda olmali (serbestlik derecesi = olcum boyutu).
    """
    ekf = ObstacleEKF(params=EKFParams(dt=cfg.sim.dt))
    x_o0 = np.array(log_ekf.x_o[0])
    rng = cfg.rng()
    z0 = x_o0[:2] + rng.normal(0.0, ekf.params.sigma_z, 2)
    ekf.initialize(z0)

    H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
    R = ekf.params.sigma_z ** 2 * np.eye(2)
    nis_values = []

    for k in range(1, len(log_ekf.t)):
        ekf.predict()
        x_o_true = np.array(log_ekf.x_o[k])
        z = x_o_true[:2] + rng.normal(0.0, ekf.params.sigma_z, 2)
        y = z - H @ ekf.x
        S = H @ ekf.P @ H.T + R
        nis = y @ np.linalg.inv(S) @ y
        nis_values.append(nis)
        ekf.update(z)

    return np.array(nis_values)


def main():
    speeds = [0.22, 0.44, 0.88]
    print(f"{'v_o':>5} {'d_min(mukemmel)':>16} {'d_min(EKF)':>12} "
          f"{'collided(mukemmel)':>19} {'collided(EKF)':>14}")
    print("-" * 75)

    results = []
    for v_o in speeds:
        m_p, m_e, log_ekf = run_pair(v_o)
        print(f"{v_o:5.2f} {m_p.d_min:16.3f} {m_e.d_min:12.3f} "
              f"{str(m_p.collided):>19} {str(m_e.collided):>14}")
        results.append((v_o, m_p, m_e, log_ekf))

    # Detayli inceleme: v_o=0.44 icin konum/hiz kestirim hatasi + NIS
    v_o_detail = 0.44
    _, m_p, m_e, log_ekf = [r for r in results if r[0] == v_o_detail][0]

    t = np.array(log_ekf.t)
    x_o_true = np.array(log_ekf.x_o)
    x_o_est = np.array(log_ekf.x_o_filter_input)

    pos_err = np.linalg.norm(x_o_true[:, :2] - x_o_est[:, :2], axis=1)
    vel_err = np.linalg.norm(x_o_true[:, 2:] - x_o_est[:, 2:], axis=1)

    cfg = Config(); cfg.obstacle.speed = v_o_detail
    nis = nis_consistency_check(log_ekf, cfg)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].plot(t, pos_err)
    axes[0].set_title("Konum kestirim hatasi |p_true - p_est|")
    axes[0].set_xlabel("t [s]"); axes[0].set_ylabel("hata [m]"); axes[0].grid(True)

    axes[1].plot(t, vel_err)
    axes[1].set_title("Hiz kestirim hatasi |v_true - v_est|")
    axes[1].set_xlabel("t [s]"); axes[1].set_ylabel("hata [m/s]"); axes[1].grid(True)

    axes[2].plot(nis, ".", alpha=0.5, label="NIS (adim adim)")
    axes[2].axhline(2.0, color="g", ls="--", label="beklenen ortalama (dof=2)")
    axes[2].axhline(np.mean(nis), color="r", ls="-", label=f"gozlenen ort={np.mean(nis):.2f}")
    axes[2].set_title("Yenilik tutarliligi (NIS)")
    axes[2].set_xlabel("adim"); axes[2].set_ylabel("NIS"); axes[2].legend(fontsize=8); axes[2].grid(True)

    plt.tight_layout()
    plt.savefig("faz0_ekf_ablation.png", dpi=120)
    print(f"\nv_o={v_o_detail}: ort. konum hatasi={np.mean(pos_err):.3f} m, "
          f"ort. hiz hatasi={np.mean(vel_err):.3f} m/s, ort. NIS={np.mean(nis):.2f} (beklenen ~2.0)")
    print("Kaydedildi: faz0_ekf_ablation.png")


if __name__ == "__main__":
    main()
