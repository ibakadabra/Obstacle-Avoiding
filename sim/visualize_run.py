"""Faz 0 gorsel dogrulama: 3 modu ayni senaryoda calistir, gozle kontrol et.

Kullanim:  cd tez_cbf/sim && python visualize_run.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cbf import Mode
from metrics import compute_metrics
from params import Config
from scenario import run_once


def main():
    cfg = Config()
    cfg.obstacle.speed = 0.44  # robotun 2 kati hizli, kesin cakisma senaryosu

    modes = [Mode.REACTIVE, Mode.DCBF, Mode.SHIFT]
    if Mode.SHIFT:
        cfg_shift = Config()
        cfg_shift.obstacle.speed = 0.44
        cfg_shift.filter.T_horizon = 0.5

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))

    for i, mode in enumerate(modes):
        c = cfg_shift if mode == Mode.SHIFT else cfg
        log = run_once(c, mode)
        m = compute_metrics(log, c)

        x_r = np.array(log.x_r)
        x_o = np.array(log.x_o)
        t = np.array(log.t)
        h_vals = np.array([info.h for info in log.info])
        interventions = np.array([info.intervention for info in log.info])
        feasible = np.array([info.feasible for info in log.info])

        ax_traj = axes[0, i]
        ax_traj.plot(x_r[:, 0], x_r[:, 1], "b-", label="robot")
        ax_traj.plot(x_o[:, 0], x_o[:, 1], "r--", label="engel")
        ax_traj.scatter(x_r[0, 0], x_r[0, 1], c="blue", marker="o", s=50, zorder=5)
        ax_traj.scatter(x_o[0, 0], x_o[0, 1], c="red", marker="o", s=50, zorder=5)
        if not feasible.all():
            first_inf = np.argmax(~feasible)
            ax_traj.scatter(x_r[first_inf, 0], x_r[first_inf, 1], c="black",
                             marker="x", s=100, zorder=6, label="ilk infeasible")
        ax_traj.set_title(f"{mode.name}  |  collided={m.collided}  d_min={m.d_min:.3f}")
        ax_traj.set_xlabel("x [m]"); ax_traj.set_ylabel("y [m]")
        ax_traj.legend(fontsize=8); ax_traj.axis("equal"); ax_traj.grid(True)

        ax_h = axes[1, i]
        ax_h.plot(t, h_vals, "g-", label="h(t)")
        ax_h.axhline(0, color="black", linewidth=0.8)
        ax_h2 = ax_h.twinx()
        ax_h2.plot(t, interventions, "m:", alpha=0.6, label="mudahale")
        ax_h.set_xlabel("t [s]"); ax_h.set_ylabel("h", color="g")
        ax_h2.set_ylabel("|u_safe-u_nom|", color="m")
        ax_h.set_title(f"infeasible_rate={m.infeasible_rate:.2f}  "
                        f"int_peak={m.intervention_peak:.3f}")
        ax_h.grid(True)

        print(f"{mode.name:10s}  collided={m.collided!s:5s}  d_min={m.d_min:.3f}  "
              f"infeasible_rate={m.infeasible_rate:.3f}  "
              f"reached_goal={m.reached_goal!s:5s}  time_to_goal={m.time_to_goal}")

    plt.tight_layout()
    out_path = "faz0_run_check.png"
    plt.savefig(out_path, dpi=120)
    print(f"\nKaydedildi: {out_path}")


if __name__ == "__main__":
    main()
