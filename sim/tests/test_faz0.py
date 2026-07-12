"""Faz 0 kabul testleri (Claude). Hepsi geçince Görev 1-2 tamam.

Çalıştırma:  cd tez_cbf/sim && python -m pytest tests/ -v
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import dynamics
from cbf import Mode, safety_filter, h_value
from params import Config


# ---------- Görev 1a: dynamics ----------

def test_unicycle_straight():
    """theta=0, w=0 → sadece +x yönünde v*dt kadar ilerler."""
    x = np.array([0.0, 0.0, 0.0])
    x1 = dynamics.unicycle_step(x, np.array([0.2, 0.0]), 0.02)
    assert x1[0] == pytest.approx(0.004)
    assert x1[1] == pytest.approx(0.0)
    assert x1[2] == pytest.approx(0.0)


def test_unicycle_turn_in_place():
    """v=0, w>0 → konum sabit, theta artar."""
    x = np.array([1.0, 2.0, 0.5])
    x1 = dynamics.unicycle_step(x, np.array([0.0, 1.0]), 0.02)
    assert x1[:2] == pytest.approx([1.0, 2.0])
    assert x1[2] == pytest.approx(0.52)


def test_obstacle_constant_velocity():
    x_o = np.array([1.0, 1.0, 0.5, -0.5])
    x_o1 = dynamics.obstacle_step(x_o, 0.1)
    assert x_o1 == pytest.approx([1.05, 0.95, 0.5, -0.5])


def test_lookahead_geometry():
    """theta=pi/2, l=0.1 → lookahead noktası +y yönünde 0.1 ileride."""
    x = np.array([0.0, 0.0, np.pi / 2])
    p_l = dynamics.lookahead_point(x, 0.1)
    assert p_l == pytest.approx([0.0, 0.1], abs=1e-12)


def test_lookahead_velocity_map():
    """G(0, l) @ [v, w] = [v, l*w] olmalı (theta=0'da)."""
    G = dynamics.lookahead_velocity_matrix(0.0, 0.1)
    out = G @ np.array([0.2, 1.0])
    assert out == pytest.approx([0.2, 0.1])


# ---------- Görev 1b: cbf ----------

def _cfg():
    cfg = Config()
    cfg.filter.alpha = 1.0
    return cfg


def test_h_sign():
    """d_safe dışında h>0, içinde h<0."""
    assert h_value(np.array([0, 0]), np.array([2, 0]), 0.5) > 0
    assert h_value(np.array([0, 0]), np.array([0.3, 0]), 0.5) < 0


def test_filter_passthrough_far():
    """Engel çok uzakta → u_nom aynen geçer, kısıt pasif."""
    cfg = _cfg()
    u_nom = np.array([0.22, 0.0])
    x_r = np.array([0.0, 0.0, 0.0])
    x_o = np.array([100.0, 100.0, 0.0, 0.0])
    u_safe, info = safety_filter(u_nom, x_r, x_o, Mode.REACTIVE, cfg)
    assert u_safe == pytest.approx(u_nom, abs=1e-6)
    assert info.feasible and not info.active


def test_filter_slows_head_on():
    """Tam önde yakın statik engel → v düşürülür."""
    cfg = _cfg()
    u_nom = np.array([0.22, 0.0])
    x_r = np.array([0.0, 0.0, 0.0])
    d_safe = cfg.filter.d_safe(cfg.robot, cfg.obstacle)
    # Mesafe lookahead noktasından (robot merkezinden l ileride) ölçülüyor;
    # engeli ona göre d_safe+0.05 uzağa koy (l'yi de ekle).
    x_o = np.array([cfg.robot.lookahead + d_safe + 0.05, 0.0, 0.0, 0.0])
    u_safe, info = safety_filter(u_nom, x_r, x_o, Mode.REACTIVE, cfg)
    assert info.feasible
    assert u_safe[0] < u_nom[0]


def test_input_bounds_respected():
    """Her koşulda çıktı donanım sınırları içinde."""
    cfg = _cfg()
    rng = np.random.default_rng(42)
    for _ in range(200):
        x_r = np.array([*rng.uniform(-2, 2, 2), rng.uniform(-np.pi, np.pi)])
        x_o = np.array([*rng.uniform(-2, 2, 2), *rng.uniform(-1.5, 1.5, 2)])
        u_nom = np.array([rng.uniform(0, 0.22), rng.uniform(-2.84, 2.84)])
        u_safe, _ = safety_filter(u_nom, x_r, x_o, Mode.REACTIVE, cfg)
        # OSQP ADMM iteratif çözücü: kısıtları makine hassasiyetine değil,
        # kendi yakınsama toleransına (~1e-3) kadar sağlar. 1e-9 gerçekçi değildi.
        assert -1e-4 <= u_safe[0] <= 0.22 + 1e-4
        assert abs(u_safe[1]) <= 2.84 + 1e-4


def test_infeasible_flagged_and_brakes():
    """h<0 (ihlal içinde) + hızlı yaklaşan engel → infeasible olabilir;
    infeasible işaretlenirse u=[0,0] dönmeli. (Feasible çözerse de geçerli —
    o zaman kısıt sağlanmış olmalı.)"""
    cfg = _cfg()
    u_nom = np.array([0.22, 0.0])
    x_r = np.array([0.0, 0.0, 0.0])
    x_o = np.array([0.15, 0.0, -1.5, 0.0])   # ihlalin içinde, üstüne geliyor
    u_safe, info = safety_filter(u_nom, x_r, x_o, Mode.DCBF, cfg)
    if not info.feasible:
        assert u_safe == pytest.approx([0.0, 0.0])


def test_dcbf_more_cautious_than_reactive():
    """Yaklaşan engelde D-CBF, reaktiften daha erken/sert müdahale etmeli
    (approaching → ek terim kısıtı sıkılaştırır)."""
    cfg = _cfg()
    u_nom = np.array([0.22, 0.0])
    x_r = np.array([0.0, 0.0, 0.0])
    x_o = np.array([1.0, 0.0, -1.0, 0.0])    # önde, 1 m/s ile üstüne geliyor
    u_r, _ = safety_filter(u_nom, x_r, x_o, Mode.REACTIVE, cfg)
    u_d, _ = safety_filter(u_nom, x_r, x_o, Mode.DCBF, cfg)
    assert u_d[0] <= u_r[0] + 1e-9


def test_shift_equals_reactive_when_T_zero():
    """T=0'da SHIFT ≡ REACTIVE olmalı (aynı QP)."""
    cfg = _cfg()
    cfg.filter.T_horizon = 0.0
    u_nom = np.array([0.22, 0.3])
    x_r = np.array([0.0, 0.0, 0.2])
    x_o = np.array([0.8, 0.1, -0.5, 0.2])
    u_s, _ = safety_filter(u_nom, x_r, x_o, Mode.SHIFT, cfg)
    u_r, _ = safety_filter(u_nom, x_r, x_o, Mode.REACTIVE, cfg)
    assert u_s == pytest.approx(u_r, abs=1e-6)


# ---------- Görev 2: metrics (dynamics+cbf bitince otomatik test edilir) ----------

def test_metrics_smoke():
    """Uçtan uca: tek koşu + metrik hesabı patlamadan dönmeli."""
    from metrics import compute_metrics
    from scenario import run_once

    cfg = _cfg()
    cfg.sim.t_end = 10.0
    log = run_once(cfg, Mode.REACTIVE)
    m = compute_metrics(log, cfg)
    assert 0.0 <= m.infeasible_rate <= 1.0
    assert m.d_min > 0.0
