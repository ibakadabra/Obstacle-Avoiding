"""SHIFT modunda T_horizon suprumesi: optimal ufuk T* var mi, fazlasi zarar mi?

Kullanim:  cd tez_cbf/sim && python sweep_T.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cbf import Mode
from metrics import compute_metrics
from params import Config
from scenario import run_once


def run_shift(T, v_o):
    cfg = Config()
    cfg.obstacle.speed = v_o
    cfg.filter.T_horizon = T
    log = run_once(cfg, Mode.SHIFT)
    return compute_metrics(log, cfg)


def main():
    T_values = np.arange(0.0, 3.01, 0.25)   # 0 (=reaktif) ... 3.0 s
    speeds = [0.22, 0.44, 0.88]              # 1x, 2x, 4x robot hizi

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    print(f"{'v_o':>5} {'T':>5} {'collided':>9} {'d_min':>7} {'inf_rate':>9} {'reached':>8}")
    print("-" * 55)

    for v_o in speeds:
        d_mins, collisions, inf_rates = [], [], []
        for T in T_values:
            m = run_shift(T, v_o)
            d_mins.append(m.d_min)
            collisions.append(1 if m.collided else 0)
            inf_rates.append(m.infeasible_rate)
            print(f"{v_o:5.2f} {T:5.2f} {str(m.collided):>9} {m.d_min:7.3f} "
                  f"{m.infeasible_rate:9.3f} {str(m.reached_goal):>8}")
        print("-" * 55)

        ratio = v_o / 0.22
        axes[0].plot(T_values, d_mins, "o-", label=f"v_o={v_o} ({ratio:.0f}x)")
        axes[1].plot(T_values, collisions, "o-", label=f"v_o={v_o} ({ratio:.0f}x)")
        axes[2].plot(T_values, inf_rates, "o-", label=f"v_o={v_o} ({ratio:.0f}x)")

    contact = Config().robot.radius + Config().obstacle.radius
    axes[0].axhline(contact, color="r", ls="--", lw=0.8, label="temas esigi")
    axes[0].set_title("d_min vs T"); axes[0].set_xlabel("T_horizon [s]"); axes[0].set_ylabel("d_min [m]")
    axes[1].set_title("carpisma vs T"); axes[1].set_xlabel("T_horizon [s]"); axes[1].set_ylabel("collided")
    axes[2].set_title("infeasible_rate vs T"); axes[2].set_xlabel("T_horizon [s]"); axes[2].set_ylabel("oran")
    for ax in axes:
        ax.legend(fontsize=8); ax.grid(True)

    plt.tight_layout()
    plt.savefig("faz0_sweep_T.png", dpi=120)
    print("\nKaydedildi: faz0_sweep_T.png")


if __name__ == "__main__":
    main()
