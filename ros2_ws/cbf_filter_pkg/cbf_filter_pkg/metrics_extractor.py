"""Metrik cikarici (Oncelik 4, deney kosucusu spec'i; ISI 1'de d_safe/contact
duzeltmesiyle genisletildi).

rosbag2 kayitlarindan koşu basina TEK bir metrics.csv satiri uretir.
Onemli: contact, margin_violation ve qp_infeasible BIRBIRINDEN BAGIMSIZ,
farkli seyler olcen 3 ayri metriktir:
  - d_min: robot-engel merkezleri arasi en kucuk mesafe, RAW /odom
    konumlarindan (FIZIKSEL govde-govde mesafesi -- CBF'nin kullandigi
    lookahead noktasindan (p_eff, robot merkezinden ~0.10m ileride) FARKLI;
    fiziksel temas govde ile olur, lookahead noktasiyla degil).
  - contact: d_min < contact_distance (govde+engel yaricaplari toplami,
    URDF/SDF'ten dogrulanmis geometrik sabit -- ISI 1, Agu 2026).
  - margin_violation: h_min < 0, DOGRUDAN /safety_filter/h_value'dan (CBF'nin
    KENDI hesapladigi, lookahead noktasini kullanan otoriter deger). ONCEDEN
    (Agu 2026 ilk surum) bu yanlislikla d_min<d_safe olarak YENIDEN
    turetiliyordu -- d_min raw govde mesafesi oldugu icin lookahead-tabanli
    h_value ile SISTEMATIK OLARAK UYUSMUYORDU. Duzeltildi.
  - qp_infeasible: QP'nin cozulemedigi an oldu mu (aktuasyon kisiti +
    CBF kisitinin CELISMESI, mesafeyle dogrudan ilgisi yok)

Kullanim:
    ros2 run cbf_filter_pkg metrics_extractor <results_dir> [output_csv] [--force]

<results_dir> altindaki TUM bag klasorlerini tarar (idempotent: output_csv'de
zaten bir satiri olan run'lar --force verilmedikce atlanir), her biri icin
yaninda duran <bag_dir>_config.yaml varsa (scenario_node Oncelik 4 oncesi
kayitlar icin olmayabilir) alpha/d_safe/mode/control_rate/prediction_horizon
sutunlarini doldurur.
"""
import csv
import os
import sys

import rosbag2_py
import yaml
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

CSV_FIELDS = [
    'run_name', 'bag_dir', 'n_msgs',
    'alpha', 'd_safe', 'mode', 'control_rate', 'prediction_horizon',
    'd_min', 'contact_distance', 'h_at_contact', 'contact',
    'margin_violation', 'penetration_depth_m',
    'qp_infeasible_count', 'qp_infeasible_any',
    'h_min',
    'solve_time_mean_ms', 'solve_time_max_ms',
    # ISI 2 (Agu 2026): bedel metrikleri -- DCBF'in "guvenli" olmasi tek
    # basina bulgu degil, hangi bedelle guvenli oldugu onemli.
    'goal_x_m', 'final_x_m', 'goal_reached', 'time_to_goal_s',
    'path_length_m',
    'intervention_integral', 'intervention_max', 'intervention_duration_s',
    'v_mean', 'v_min', 'frozen',
]

FROZEN_V_THRESH = 0.01      # m/s   -- bu esigin altinda "durmus" sayilir
FROZEN_MIN_DURATION = 2.0   # s     -- bu sureden uzun surerse "frozen"
INTERVENTION_THRESH = 1e-3  # ‖u_safe-u_nom‖ bu esigin ustundeyse "mudahale aktif"
GOAL_FRACTION = 0.95        # nominal mesafenin bu oranina ulasilirsa "goal_reached"

# params.py (cbf_filter_pkg) ile AYNI, ISI 1'de URDF/SDF'ten dogrulanan
# degerler: robot.radius=0.1237 (govde kutusunun en kotu-durum kose yaricapi),
# obstacle.radius=0.25 (moving_obstacle.sdf silindiri), d_margin=0.05.
DEFAULT_ROBOT_RADIUS = 0.1237
DEFAULT_OBSTACLE_RADIUS = 0.25
DEFAULT_D_MARGIN = 0.05
DEFAULT_CONTACT_DISTANCE = DEFAULT_ROBOT_RADIUS + DEFAULT_OBSTACLE_RADIUS
DEFAULT_D_SAFE = DEFAULT_CONTACT_DISTANCE + DEFAULT_D_MARGIN


def _read_bag(bag_dir: str) -> dict:
    storage_options = rosbag2_py.StorageOptions(uri=bag_dir, storage_id='sqlite3')
    converter_options = rosbag2_py.ConverterOptions('', '')
    reader = rosbag2_py.SequentialReader()
    reader.open(storage_options, converter_options)

    type_map = {t.name: t.type for t in reader.get_all_topics_and_types()}
    msg_types = {name: get_message(t) for name, t in type_map.items()}

    robot_xy, obstacle_xy = [], []
    h_values, qp_statuses, solve_times = [], [], []
    odom_t = []          # (t_s, x, y, v_actual)  -- /odom, v_actual=twist.linear.x
    cmd_actual = []       # (t_s, v, w)            -- /cmd_vel (u_safe, filtreden SONRA)
    cmd_nominal = []      # (t_s, v, w)            -- /safety_filter/cmd_vel_nominal (u_nom)
    n_msgs = 0

    while reader.has_next():
        topic, data, t_ns = reader.read_next()
        n_msgs += 1
        if topic not in msg_types:
            continue
        msg = deserialize_message(data, msg_types[topic])
        t_s = t_ns / 1e9

        if topic == '/odom':
            p = msg.pose.pose.position
            robot_xy.append((p.x, p.y))
            odom_t.append((t_s, p.x, p.y, msg.twist.twist.linear.x))
        elif topic == '/moving_obstacle/odom':
            p = msg.pose.pose.position
            obstacle_xy.append((p.x, p.y))
        elif topic == '/safety_filter/h_value':
            h_values.append(msg.data)
        elif topic == '/safety_filter/qp_status':
            qp_statuses.append(msg.data)
        elif topic == '/safety_filter/qp_solve_time_ms':
            solve_times.append(msg.data)
        elif topic == '/cmd_vel':
            cmd_actual.append((t_s, msg.linear.x, msg.angular.z))
        elif topic == '/safety_filter/cmd_vel_nominal':
            cmd_nominal.append((t_s, msg.linear.x, msg.angular.z))

    return dict(robot_xy=robot_xy, obstacle_xy=obstacle_xy, h_values=h_values,
                qp_statuses=qp_statuses, solve_times=solve_times, n_msgs=n_msgs,
                odom_t=odom_t, cmd_actual=cmd_actual, cmd_nominal=cmd_nominal)


def _d_min(robot_xy, obstacle_xy) -> float:
    # /odom ve /moving_obstacle/odom farkli hizlarda yayinlaniyor; robot ve
    # engel arasindaki mesafeyi ZAMAN DAMGASI olmadan (sadece kayit sirasiyla)
    # kabaca eslestiriyoruz -- iki dizi de benzer orandaki Gazebo publish
    # hizinda oldugu icin (~20-30Hz) indeks-oranli eslestirme yeterli hassasiyette.
    if not robot_xy or not obstacle_xy:
        return float('nan')
    n = min(len(robot_xy), len(obstacle_xy))
    ratio_r = len(robot_xy) / n
    ratio_o = len(obstacle_xy) / n
    best = float('inf')
    for i in range(n):
        rx, ry = robot_xy[int(i * ratio_r)]
        ox, oy = obstacle_xy[int(i * ratio_o)]
        d = ((rx - ox) ** 2 + (ry - oy) ** 2) ** 0.5
        best = min(best, d)
    return best


def _path_metrics(odom_t):
    """path_length, v_mean, v_min, frozen -- /odom'un (t,x,y,v) dizisinden."""
    if len(odom_t) < 2:
        return dict(path_length=float('nan'), v_mean=float('nan'),
                    v_min=float('nan'), frozen=0, final_x=float('nan'), t0=float('nan'))
    t0 = odom_t[0][0]
    path_length = 0.0
    for (_, x0, y0, _), (_, x1, y1, _) in zip(odom_t, odom_t[1:]):
        path_length += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    vs = [v for (_, _, _, v) in odom_t]
    v_mean, v_min = sum(vs) / len(vs), min(vs)

    # frozen: v < esik olan ARDISIK bir zaman penceresi >= FROZEN_MIN_DURATION
    frozen = 0
    window_start = None
    for t, _, _, v in odom_t:
        if v < FROZEN_V_THRESH:
            if window_start is None:
                window_start = t
            elif t - window_start >= FROZEN_MIN_DURATION:
                frozen = 1
                break
        else:
            window_start = None

    final_x = odom_t[-1][1]
    return dict(path_length=path_length, v_mean=v_mean, v_min=v_min,
                frozen=frozen, final_x=final_x, t0=t0)


def _goal_metrics(odom_t, t0, nominal_v, duration):
    """goal_x: engel olmasaydi kat edilecek nominal mesafe (duz cizgi varsayimi,
    senaryolarda omega_nom=0 oldugu icin gecerli). goal_reached: robot bu
    mesafenin >= GOAL_FRACTION'ina ulasti mi. time_to_goal: ilk ulasma ani
    (ilk /odom mesajina gore GORECELI zaman -- t0 senaryonun gercek
    sifiri degil, bag'deki ilk odom ornegi; settle_time kadar sistematik
    bir kaymasi olabilir, bu YAKLASIKTIR)."""
    if nominal_v is None or duration is None or not odom_t:
        return dict(goal_x=float('nan'), goal_reached='', time_to_goal=float('nan'))
    goal_x = nominal_v * duration
    threshold_x = GOAL_FRACTION * goal_x
    time_to_goal = float('nan')
    reached = 0
    for t, x, _, _ in odom_t:
        if x >= threshold_x:
            reached = 1
            time_to_goal = t - t0
            break
    return dict(goal_x=goal_x, goal_reached=reached, time_to_goal=time_to_goal)


def _intervention_metrics(cmd_actual, cmd_nominal):
    """intervention(t) = ||u_safe-u_nom|| (cbf.py'nin FilterInfo.intervention
    ile AYNI tanim: v ve w'yi tek bir Oklid normunda karistirir). cmd_actual
    ve cmd_nominal AYNI callback'ten (on_cmd_nom) art arda yayinlandigi icin
    INDEKSE gore eslestirilir (zaman damgasiyla degil -- robot/engel
    eslestirmesindeki gibi bir belirsizlik YOK, ayni olayin iki cikisidir)."""
    n = min(len(cmd_actual), len(cmd_nominal))
    if n == 0:
        return dict(integral=float('nan'), max_=float('nan'), duration=float('nan'))
    mags, ts = [], []
    for i in range(n):
        t, va, wa = cmd_actual[i]
        _, vn, wn = cmd_nominal[i]
        mags.append(((va - vn) ** 2 + (wa - wn) ** 2) ** 0.5)
        ts.append(t)
    integral = 0.0
    for i in range(1, n):
        dt = ts[i] - ts[i - 1]
        integral += 0.5 * (mags[i] + mags[i - 1]) * dt
    duration = sum(
        (ts[i] - ts[i - 1]) for i in range(1, n) if mags[i] > INTERVENTION_THRESH)
    return dict(integral=integral, max_=max(mags), duration=duration)


def extract_one(bag_dir: str, contact_distance: float) -> dict:
    data = _read_bag(bag_dir)

    cfg_path = bag_dir.rstrip('/').rstrip('\\') + '_config.yaml'
    alpha = d_safe = mode = control_rate = prediction_horizon = ''
    nominal_v = duration = None
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
        filt = cfg.get('filter', {})
        alpha = filt.get('alpha', '')
        d_safe = filt.get('d_safe', '')
        mode = filt.get('mode', '')
        control_rate = filt.get('control_rate', '')
        prediction_horizon = filt.get('prediction_horizon', '')
        sc = cfg.get('scenario', {})
        nominal_v = sc.get('robot', {}).get('cmd', {}).get('v')
        duration = sc.get('duration')

    # d_safe bu bag icin bilinmiyorsa (eski kayit / config.yaml yok) DEFAULT_D_SAFE
    # kullanilir -- h_at_contact SADECE bilgilendirici bir referans esik,
    # margin_violation'i etkilemez (o dogrudan h_min'den geliyor).
    d_safe_val = float(d_safe) if d_safe not in ('', None) else DEFAULT_D_SAFE

    dmin = _d_min(data['robot_xy'], data['obstacle_xy'])
    h_min = min(data['h_values']) if data['h_values'] else float('nan')
    infeasible_count = sum(1 for s in data['qp_statuses'] if s == 'infeasible')
    h_at_contact = contact_distance ** 2 - d_safe_val ** 2

    pm = _path_metrics(data['odom_t'])
    gm = _goal_metrics(data['odom_t'], pm['t0'], nominal_v, duration)
    im = _intervention_metrics(data['cmd_actual'], data['cmd_nominal'])

    def _fmt(x, nd=4):
        return f'{x:.{nd}f}' if x == x else ''  # NaN kontrolu

    row = {
        'run_name': os.path.basename(bag_dir.rstrip('/').rstrip('\\')),
        'bag_dir': bag_dir,
        'n_msgs': data['n_msgs'],
        'alpha': alpha,
        'd_safe': d_safe,
        'mode': mode,
        'control_rate': control_rate,
        'prediction_horizon': prediction_horizon,
        'd_min': f'{dmin:.4f}' if dmin == dmin else '',  # NaN kontrolu
        'contact_distance': f'{contact_distance:.4f}',
        'h_at_contact': f'{h_at_contact:.4f}',
        'contact': int(dmin < contact_distance) if dmin == dmin else '',
        # margin_violation: DOGRUDAN h_min'den (otoriter, lookahead-noktasi
        # dahil CBF hesaplamasinin ta kendisi) -- d_min'den YENIDEN turetilmez.
        'margin_violation': int(h_min < 0) if h_min == h_min else '',
        'penetration_depth_m': (f'{max(0.0, contact_distance - dmin):.4f}'
                                 if dmin == dmin else ''),
        'qp_infeasible_count': infeasible_count,
        'qp_infeasible_any': int(infeasible_count > 0),
        'h_min': f'{h_min:.4f}' if h_min == h_min else '',
        'solve_time_mean_ms': (f'{sum(data["solve_times"]) / len(data["solve_times"]):.4f}'
                                if data['solve_times'] else ''),
        'solve_time_max_ms': f'{max(data["solve_times"]):.4f}' if data['solve_times'] else '',
        'goal_x_m': _fmt(gm['goal_x']),
        'final_x_m': _fmt(pm['final_x']),
        'goal_reached': gm['goal_reached'],
        'time_to_goal_s': _fmt(gm['time_to_goal']),
        'path_length_m': _fmt(pm['path_length']),
        'intervention_integral': _fmt(im['integral']),
        'intervention_max': _fmt(im['max_']),
        'intervention_duration_s': _fmt(im['duration']),
        'v_mean': _fmt(pm['v_mean']),
        'v_min': _fmt(pm['v_min']),
        'frozen': pm['frozen'],
    }
    return row


def main():
    if len(sys.argv) < 2:
        print('Kullanim: metrics_extractor <results_dir> [output_csv] [--force] '
              f'[--contact-distance D] (varsayilan D={DEFAULT_CONTACT_DISTANCE:.4f})')
        sys.exit(1)

    results_dir = os.path.expanduser(sys.argv[1])
    args = sys.argv[2:]
    force = '--force' in args
    if '--contact-distance' in args:
        contact_distance = float(args[args.index('--contact-distance') + 1])
    else:
        contact_distance = DEFAULT_CONTACT_DISTANCE
    positional = [a for a in args if not a.startswith('--') and a != str(contact_distance)]
    output_csv = os.path.expanduser(positional[0]) if positional else os.path.join(results_dir, 'metrics.csv')

    bag_dirs = sorted(
        os.path.join(results_dir, d) for d in os.listdir(results_dir)
        if os.path.isdir(os.path.join(results_dir, d))
        and os.path.exists(os.path.join(results_dir, d, 'metadata.yaml'))
    )

    already_done = set()
    existing_rows = []
    if os.path.exists(output_csv) and not force:
        with open(output_csv, newline='') as f:
            for r in csv.DictReader(f):
                existing_rows.append(r)
                already_done.add(r['run_name'])

    new_rows = []
    for bag_dir in bag_dirs:
        run_name = os.path.basename(bag_dir)
        if run_name in already_done:
            continue
        print(f'Isleniyor: {run_name}')
        try:
            new_rows.append(extract_one(bag_dir, contact_distance))
        except Exception as e:
            print(f'  HATA ({run_name}): {e!r} -- atlaniyor')

    all_rows = existing_rows + new_rows
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f'{len(new_rows)} yeni satir eklendi, toplam {len(all_rows)} satir -> {output_csv}')


if __name__ == '__main__':
    main()
