"""Faz 0 KAPI FIGURU: analitik sinir vs sayisal simulasyon.

Panel A: 1D kafa-kafaya, DCBF — QP infeasibility baslangic mesafesi.
         Analitik (fit'siz!):  d* = v_o/alpha + sqrt((v_o/alpha)^2 + d_safe^2)
         (h = d^2 - d_safe^2 formulasyonundan, v=0'da kisitin sinir hali)
Panel B: capraz senaryoda T-suprumesi — sayisal T* tepeleri (nitel kontrol).

Kullanim:  cd tez_cbf/sim && python faz0_gate_figure.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import dynamics
from cbf import Mode, safety_filter
from metrics import compute_metrics
from params import Config
from scenario import run_once


# ---------------- Panel A: kafa-kafaya infeasibility baslangici ----------------

def head_on_onset_distance(v_o: float, d0: float = None) -> float | None:
    """Engel tam karsidan gelir; ilk infeasible adimda lookahead->engel mesafesi.

    d0, analitik onset'in daima UZAGINDA baslatilmali (yoksa simulasyon
    onset'i degil, baslangic kosulunu olcer). Guvenlik payi +1.5 m.
    """
    cfg = Config()
    cfg.sim.t_end = 60.0
    if d0 is None:
        d_safe = cfg.filter.d_safe(cfg.robot, cfg.obstacle)
        d0 = analytic_onset(np.array([v_o]), cfg.filter.alpha, d_safe)[0] + 1.5
    x_r = np.array([0.0, 0.0, 0.0])
    x_o = np.array([d0, 0.0, -v_o, 0.0])
    u_nom = np.array([cfg.robot.v_max, 0.0])

    n = int(cfg.sim.t_end / cfg.sim.dt)
    for _ in range(n):
        u_safe, info = safety_filter(u_nom, x_r, x_o, Mode.DCBF, cfg)
        if not info.feasible:
            p_l = dynamics.lookahead_point(x_r, cfg.robot.lookahead)
            return float(np.linalg.norm(p_l - x_o[:2]))
        x_r = dynamics.unicycle_step(x_r, u_safe, cfg.sim.dt)
        x_o = dynamics.obstacle_step(x_o, cfg.sim.dt)
    return None


def analytic_onset(v_o: np.ndarray, alpha: float, d_safe: float) -> np.ndarray:
    return v_o / alpha + np.sqrt((v_o / alpha) ** 2 + d_safe ** 2)


# ---------------- Panel B: capraz senaryo T-suprumesi ----------------

def crossing_dmin(v_o: float, T: float) -> float:
    cfg = Config()
    cfg.obstacle.speed = v_o
    cfg.filter.T_horizon = T
    log = run_once(cfg, Mode.SHIFT)
    return compute_metrics(log, cfg).d_min


def main():
    cfg = Config()
    d_safe = cfg.filter.d_safe(cfg.robot, cfg.obstacle)
    alpha = cfg.filter.alpha

    # --- Panel A verisi ---
    speeds_A = np.array([0.11, 0.22, 0.33, 0.44, 0.66, 0.88, 1.10, 1.32])
    measured = []
    print("Panel A: kafa-kafaya infeasibility baslangici")
    print(f"{'v_o':>6} {'olculen d*':>11} {'analitik d*':>12}")
    for v_o in speeds_A:
        d_meas = head_on_onset_distance(v_o)
        d_theo = float(analytic_onset(np.array([v_o]), alpha, d_safe)[0])
        measured.append(d_meas)
        print(f"{v_o:6.2f} {d_meas!s:>11} {d_theo:12.3f}")

    # --- Panel B verisi ---
    T_values = np.arange(0.0, 2.01, 0.25)
    speeds_B = [0.22, 0.44, 0.88]
    curves = {}
    print("\nPanel B: T-suprumesi (capraz)")
    for v_o in speeds_B:
        curves[v_o] = [crossing_dmin(v_o, T) for T in T_values]

    # --- Cizim ---
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5))

    v_fine = np.linspace(0.0, 1.4, 200)
    axA.plot(v_fine, analytic_onset(v_fine, alpha, d_safe), "k-", lw=2,
             label=r"analitik  $d^*=v_o/\alpha+\sqrt{(v_o/\alpha)^2+d_{safe}^2}$")
    axA.plot(speeds_A, measured, "ro", ms=8, label="simulasyon (ilk infeasible ani)")
    axA.axhline(d_safe, color="gray", ls=":", lw=1, label=r"$d_{safe}$")
    axA.set_xlabel(r"engel hizi $v_o$ [m/s]")
    axA.set_ylabel(r"infeasibility baslangic mesafesi $d^*$ [m]")
    axA.set_title("Panel A — kafa-kafaya: analitik vs sayisal (fit YOK)")
    axA.legend(fontsize=9); axA.grid(True)

    for v_o in speeds_B:
        c = np.array(curves[v_o])
        ratio = v_o / 0.22
        line, = axB.plot(T_values, c, "o-", label=f"$v_o$={v_o} ({ratio:.0f}x)")
        k_star = int(np.argmax(c))
        axB.axvline(T_values[k_star], color=line.get_color(), ls="--", lw=1, alpha=0.6)
    contact = cfg.robot.radius + cfg.obstacle.radius
    axB.axhline(contact, color="r", ls=":", lw=1, label="temas esigi")
    axB.set_xlabel(r"onguru ufku $T$ [s]")
    axB.set_ylabel(r"$d_{min}$ [m]")
    axB.set_title(r"Panel B — capraz: sayisal $T^*$ tepeleri (kesikli dikey)")
    axB.legend(fontsize=9); axB.grid(True)

    plt.tight_layout()
    plt.savefig("faz0_gate_figure.png", dpi=130)
    print("\nKaydedildi: faz0_gate_figure.png")


if __name__ == "__main__":
    main()
