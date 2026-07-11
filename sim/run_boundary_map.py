"""Sınır haritası süpürmesi (Claude — altyapı). Stub'lar dolunca çalışır.

Kullanım:
    python run_boundary_map.py            # varsayılan süpürme → results/*.csv + PNG
"""
import itertools
from pathlib import Path

import numpy as np

from cbf import Mode
from metrics import compute_metrics
from params import Config
from scenario import run_once

RESULTS = Path(__file__).parent / "results"

OBSTACLE_SPEEDS = [0.22, 0.44, 0.88, 1.32]        # oran 1x, 2x, 4x, 6x
MODES = [
    ("reactive", Mode.REACTIVE, 0.0),
    ("dcbf",     Mode.DCBF,     0.0),
    ("shift_05", Mode.SHIFT,    0.5),
    ("shift_10", Mode.SHIFT,    1.0),
    ("shift_20", Mode.SHIFT,    2.0),
]
TAU_DELAYS = [0.0, 0.2, 0.4]
N_SEEDS = 20   # Faz 0'da senaryo deterministik; seed şimdilik gürültü eklenince anlamlanır


def sweep() -> list[dict]:
    rows = []
    combos = list(itertools.product(OBSTACLE_SPEEDS, MODES, TAU_DELAYS, range(N_SEEDS)))
    for i, (v_o, (mode_name, mode, T), tau, seed) in enumerate(combos):
        cfg = Config()
        cfg.obstacle.speed = v_o
        cfg.filter.T_horizon = T
        cfg.sim.tau_delay = tau
        cfg.sim.seed = seed

        log = run_once(cfg, mode)
        m = compute_metrics(log, cfg)
        rows.append({
            "speed_ratio": v_o / cfg.robot.v_max,
            "mode": mode_name, "tau": tau, "seed": seed,
            "collided": m.collided, "d_min": m.d_min,
            "infeasible_rate": m.infeasible_rate,
            "reached_goal": m.reached_goal, "time_to_goal": m.time_to_goal,
            "intervention_int": m.intervention_int,
        })
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(combos)}")
    return rows


def save_csv(rows: list[dict], path: Path) -> None:
    import csv
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_heatmaps(rows: list[dict]) -> None:
    """Mod başına (hız oranı × tau) çarpışma-oranı ısı haritası."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ratios = sorted({r["speed_ratio"] for r in rows})
    taus = sorted({r["tau"] for r in rows})
    mode_names = [m[0] for m in MODES]

    fig, axes = plt.subplots(1, len(mode_names), figsize=(4 * len(mode_names), 3.5),
                             sharey=True)
    for ax, mode_name in zip(np.atleast_1d(axes), mode_names):
        grid = np.zeros((len(taus), len(ratios)))
        for ti, tau in enumerate(taus):
            for ri, ratio in enumerate(ratios):
                sel = [r for r in rows
                       if r["mode"] == mode_name and r["tau"] == tau
                       and r["speed_ratio"] == ratio]
                grid[ti, ri] = np.mean([r["collided"] for r in sel]) if sel else np.nan
        im = ax.imshow(grid, origin="lower", vmin=0, vmax=1, cmap="RdYlGn_r",
                       aspect="auto")
        ax.set_xticks(range(len(ratios)), [f"{r:.0f}x" for r in ratios])
        ax.set_yticks(range(len(taus)), [f"{t:.1f}" for t in taus])
        ax.set_title(mode_name)
        ax.set_xlabel("hız oranı")
    np.atleast_1d(axes)[0].set_ylabel("gecikme τ [s]")
    fig.colorbar(im, ax=axes, label="çarpışma oranı", shrink=0.8)
    fig.suptitle("Faz 0 sınır haritası — çarpışma oranı")
    fig.savefig(RESULTS / "boundary_map.png", dpi=150, bbox_inches="tight")
    print(f"kaydedildi: {RESULTS / 'boundary_map.png'}")


if __name__ == "__main__":
    RESULTS.mkdir(exist_ok=True)
    rows = sweep()
    save_csv(rows, RESULTS / "sweep.csv")
    plot_heatmaps(rows)
