"""İŞ 7 (etkilesim kose testleri) config URETICISI.

NEDEN AYRI BIR SCRIPT: İŞ 7'nin iki cifti (T x alpha, T x L) T* degerine
ihtiyac duyuyor, T* ise İŞ 6 (T taramasi) BITMEDEN bilinemiyor. Bu
script İŞ 6'nin sonucunu (boundary_results.csv) okuyup T*'yi secer ve
uc config'i yazar -- boylece zincir INSAN MUDAHALESI OLMADAN devam eder.

T* SECIMI: 'turn' senaryosunda contact_rate icin v_crit'i EN YUKSEK
yapan T. Beklenti (spec 6c) tepe noktali bir egri; eger monoton
cikarsa en yuksek T secilir ve bu durum LOG'a yazilir (manevra
yeterince siddetli degil demektir, spec'in acik notu).

Kullanim:
    python3 gen_is7_configs.py [--v-test 1.3]
"""
import csv
import os
import sys

RESULTS_DIR = os.path.expanduser('~/tez_cbf/results')
BOUNDARY_CSV = os.path.join(RESULTS_DIR, 'boundary_results.csv')
CONFIG_DIR = os.path.expanduser(
    '~/tez_cbf/ros2_ws/cbf_filter_pkg/configs')

# Kose testleri SABIT BIR HIZDA kosulur (sinir aramasi DEGIL) -- spec:
# "v = v_crit civari, N=20". Varsayilan, İŞ 3/4/5'te olculen tipik
# v_crit (~1.3) civari.
DEFAULT_V_TEST = 1.3
RUNS_PER_CELL = 20

BASE = """# İŞ 7: etkilesim kose testi -- {pair_name}
#
# OTOMATIK URETILDI (gen_is7_configs.py), ELLE DUZENLEME.
# {tstar_note}
#
# AMAC: eksenler BAGIMSIZ mi? v_crit farklari yaklasik TOPLAMSALSA
# eksenleri ayri ayri taramak mesru (İŞ 3/4/5/6'nin yaptigi gibi).
# Guclu etkilesim varsa SADECE o cift icin 2B tarama gerekir.
#
# Sabit hizda (v={v_test}) 2x2 kose, N={runs} -- sinir aramasi DEGIL.
scenario:
  name: {name}
  robot:
    start: [0.0, 0.0, 0.0]
    cmd: {{v: 0.22, omega: 0.0}}
  obstacle:
    start: [3.0, 0.3, 3.14159]
    velocity: [-{v_test}, 0.0]
    trajectory_type: {traj}
    maneuver_t0: 2.0
    maneuver_duration: 1.5
    maneuver_angle_deg: 30.0
  duration: 30.0
  settle_time: 2.0
nominal:
  type: goal_seeking
  goal: [4.0, 0.0]
  k_p: 1.5
  slowdown_radius: 0.5
  v_max: 0.22
  omega_max: 2.84
filter:
  alpha: 1.0
  d_safe: 0.5237
  prediction_horizon: 0.0
  control_rate: 10.0
  mode: {mode}
  v_min: 0.0
  cost_normalized: true
  w_v: 1.0
  w_w: 1.0
  lookahead_L: 0.10
  slack_enabled: true
  slack_rho: 500.0
  d_safe_mode: {d_safe_mode}
  d_safe_fixed: 0.5237

sweep:
{sweep_block}runs_per_cell: {runs}
# 2 x 2 x {runs} = {total} kosu
"""


def pick_t_star():
    """İŞ 6 sonucundan T* sec. (t_star, note) doner."""
    if not os.path.exists(BOUNDARY_CSV):
        return None, 'boundary_results.csv YOK -- T* secilemedi.'
    rows = []
    with open(BOUNDARY_CSV, newline='') as f:
        for r in csv.DictReader(f):
            if r.get('campaign') != 'bnd_T':
                continue
            if r.get('target_metric') != 'contact_rate':
                continue
            if r.get('status') != 'OK' or not r.get('v_crit'):
                continue
            cell = r.get('cell', '')
            if 'turn' not in cell:      # sadece manevrali senaryo
                continue
            # cell ornegi: 'prediction_horizon0.5_trajectory_typeturn'
            try:
                tok = cell.split('prediction_horizon')[1].split('_')[0]
                t = float(tok)
            except (IndexError, ValueError):
                continue
            rows.append((t, float(r['v_crit'])))

    if not rows:
        return None, 'bnd_T/turn/contact_rate icin OK satiri YOK -- T* secilemedi.'

    rows.sort()
    t_star, v_best = max(rows, key=lambda p: p[1])
    detail = ', '.join(f'T={t}:{v:.3f}' for t, v in rows)
    monotonic = all(b[1] >= a[1] for a, b in zip(rows, rows[1:]))
    note = (f'T* = {t_star} (v_crit={v_best:.3f}). Olculen: {detail}.')
    if monotonic:
        note += (' UYARI: v_crit(T) MONOTON ARTIYOR -- tepe noktasi yok, '
                 'yani manevra yeterince siddetli degil (spec 6c). En '
                 'yuksek T secildi; sonuc "T* bulundu" diye YORUMLANMAMALI.')
    return t_star, note


def write_cfg(fname, **kw):
    path = os.path.join(CONFIG_DIR, fname)
    with open(path, 'w') as f:
        f.write(BASE.format(**kw))
    print(f'yazildi: {path}')


def main():
    v_test = DEFAULT_V_TEST
    if '--v-test' in sys.argv:
        v_test = float(sys.argv[sys.argv.index('--v-test') + 1])

    t_star, note = pick_t_star()
    print('T* secimi:', note)

    common = dict(v_test=v_test, runs=RUNS_PER_CELL,
                  total=2 * 2 * RUNS_PER_CELL, tstar_note=note)

    # --- Cift 3: L x w_w (T'ye BAGIMLI DEGIL, her zaman yazilir) ---
    write_cfg('is7_corner_L_w_w.yaml',
              pair_name='L x w_w', name='is7_L_w_w', mode='DCBF',
              traj='straight', d_safe_mode='fixed',
              sweep_block='  filter.lookahead_L: [0.10, 0.30]\n'
                          '  filter.w_w: [0.5, 2.0]\n',
              **common)

    if t_star is None:
        print('T* YOK -> T-bagimli iki cift (T x alpha, T x L) '
              'URETILMEDI. Sadece L x w_w kosulacak.')
        return

    # --- Cift 1: T x alpha ---
    write_cfg('is7_corner_T_alpha.yaml',
              pair_name='T x alpha', name='is7_T_alpha', mode='SHIFT_CORRECT',
              traj='turn', d_safe_mode='derived',
              sweep_block=f'  filter.prediction_horizon: [0.0, {t_star}]\n'
                          '  filter.alpha: [0.3, 2.0]\n',
              **common)

    # --- Cift 2: T x L ---
    write_cfg('is7_corner_T_L.yaml',
              pair_name='T x L', name='is7_T_L', mode='SHIFT_CORRECT',
              traj='turn', d_safe_mode='fixed',
              sweep_block=f'  filter.prediction_horizon: [0.0, {t_star}]\n'
                          '  filter.lookahead_L: [0.10, 0.30]\n',
              **common)


if __name__ == '__main__':
    main()
