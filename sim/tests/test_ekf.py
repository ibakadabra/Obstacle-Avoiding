"""Görev 3 kabul testleri (Claude): sabit-hız Kalman filtresi.

Çalıştırma:  cd tez_cbf/sim && python -m pytest tests/test_ekf.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ekf import EKFParams, ObstacleEKF


def _make_filter(dt=0.02):
    return ObstacleEKF(params=EKFParams(dt=dt))


def test_initialize():
    f = _make_filter()
    f.initialize(np.array([1.0, 2.0]))
    assert f.x == pytest.approx([1.0, 2.0, 0.0, 0.0])
    assert f.P.shape == (4, 4)
    assert f.P[0, 0] == pytest.approx(f.params.P0_pos)
    assert f.P[2, 2] == pytest.approx(f.params.P0_vel)


def test_predict_moves_position_with_velocity():
    """Hız biliniyorsa predict konumu v*dt kadar taşımalı."""
    f = _make_filter(dt=0.1)
    f.initialize(np.array([0.0, 0.0]))
    f.x = np.array([0.0, 0.0, 1.0, -0.5])   # hızı elle ver
    f.predict()
    assert f.x == pytest.approx([0.1, -0.05, 1.0, -0.5])


def test_predict_grows_uncertainty():
    """Ölçüm gelmedikçe kovaryans (belirsizlik) büyümeli."""
    f = _make_filter()
    f.initialize(np.array([0.0, 0.0]))
    trace_before = np.trace(f.P)
    for _ in range(50):
        f.predict()
    assert np.trace(f.P) > trace_before


def test_update_shrinks_uncertainty():
    """Ölçüm, konum belirsizliğini küçültmeli."""
    f = _make_filter()
    f.initialize(np.array([0.0, 0.0]))
    f.predict()
    p_pos_before = f.P[0, 0]
    f.update(np.array([0.01, -0.01]))
    assert f.P[0, 0] < p_pos_before


def test_velocity_convergence():
    """Ana kabul testi: gürültülü konum ölçümlerinden HIZ kestirimi yakınsamalı.

    Gerçek engel: (0,0)'dan v=(0.8, -0.3) ile gidiyor. 3 saniye (150 adım)
    ölçümden sonra hız hatası < 0.1 m/s olmalı.
    """
    rng = np.random.default_rng(7)
    dt = 0.02
    v_true = np.array([0.8, -0.3])
    f = _make_filter(dt=dt)

    pos = np.array([0.0, 0.0])
    f.initialize(pos + rng.normal(0, 0.05, 2))
    for _ in range(150):
        pos = pos + v_true * dt
        f.predict()
        f.update(pos + rng.normal(0, 0.05, 2))

    v_est = f.state()[2:]
    assert np.linalg.norm(v_est - v_true) < 0.1


def test_feeds_safety_filter():
    """Uçtan uca: EKF çıktısı cbf.safety_filter'a x_o olarak girebilmeli."""
    from cbf import Mode, safety_filter
    from params import Config

    f = _make_filter()
    f.initialize(np.array([1.0, 0.5]))
    f.predict()
    f.update(np.array([1.0, 0.49]))

    cfg = Config()
    u_safe, info = safety_filter(
        np.array([0.22, 0.0]), np.array([0.0, 0.0, 0.0]), f.state(), Mode.DCBF, cfg
    )
    assert u_safe.shape == (2,)
