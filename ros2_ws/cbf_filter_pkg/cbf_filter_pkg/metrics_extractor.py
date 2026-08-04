"""Metrik cikarici (Oncelik 4, deney kosucusu spec'i).

rosbag2 kayitlarindan koşu basina TEK bir metrics.csv satiri uretir.
Onemli: collision, qp_infeasible ve d_min BIRBIRINDEN BAGIMSIZ, farkli
seyler olcen 3 ayri metriktir (spec'in kendi vurgusu):
  - d_min: robot-engel merkezleri arasi en kucuk mesafe (fiziksel gerceklik)
  - collision: d_min < --contact-radius (fiziksel temas esigi, d_safe'den
    FARKLI -- d_safe kontrol marjidir, contact-radius govde yaricapi toplamidir)
  - margin_violation: d_min < d_safe (kontrol marji ihlali, CARPMA DEGIL)
  - qp_infeasible: QP'nin cozulemedigi an oldu mu (aktuasyon kisiti +
    CBF kisitinin CELISMESI, mesafeyle dogrudan ilgisi yok)

Kullanim:
    ros2 run cbf_filter_pkg metrics_extractor <results_dir> [output_csv]

<results_dir> altindaki TUM bag klasorlerini tarar (idempotent: output_csv'de
zaten bir satiri olan run'lar --force verilmedikce atlanir), her biri icin
yaninda duran <bag_dir>_config.yaml varsa (scenario_node Oncelik 4 oncesi
kayitlar icin olmayabilir) alpha/d_safe/control_rate/prediction_horizon
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
    'alpha', 'd_safe', 'control_rate', 'prediction_horizon',
    'd_min', 'collision', 'margin_violation',
    'qp_infeasible_count', 'qp_infeasible_any',
    'h_min',
    'solve_time_mean_ms', 'solve_time_max_ms',
]

DEFAULT_CONTACT_RADIUS = 0.30  # govde yaricaplari toplami -- KONTROL ET


def _read_bag(bag_dir: str) -> dict:
    storage_options = rosbag2_py.StorageOptions(uri=bag_dir, storage_id='sqlite3')
    converter_options = rosbag2_py.ConverterOptions('', '')
    reader = rosbag2_py.SequentialReader()
    reader.open(storage_options, converter_options)

    type_map = {t.name: t.type for t in reader.get_all_topics_and_types()}
    msg_types = {name: get_message(t) for name, t in type_map.items()}

    robot_xy, obstacle_xy = [], []
    h_values, qp_statuses, solve_times = [], [], []
    n_msgs = 0

    while reader.has_next():
        topic, data, _t = reader.read_next()
        n_msgs += 1
        if topic not in msg_types:
            continue
        msg = deserialize_message(data, msg_types[topic])

        if topic == '/odom':
            p = msg.pose.pose.position
            robot_xy.append((p.x, p.y))
        elif topic == '/moving_obstacle/odom':
            p = msg.pose.pose.position
            obstacle_xy.append((p.x, p.y))
        elif topic == '/safety_filter/h_value':
            h_values.append(msg.data)
        elif topic == '/safety_filter/qp_status':
            qp_statuses.append(msg.data)
        elif topic == '/safety_filter/qp_solve_time_ms':
            solve_times.append(msg.data)

    return dict(robot_xy=robot_xy, obstacle_xy=obstacle_xy, h_values=h_values,
                qp_statuses=qp_statuses, solve_times=solve_times, n_msgs=n_msgs)


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


def extract_one(bag_dir: str, contact_radius: float) -> dict:
    data = _read_bag(bag_dir)

    cfg_path = bag_dir.rstrip('/').rstrip('\\') + '_config.yaml'
    alpha = d_safe = control_rate = prediction_horizon = ''
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
        filt = cfg.get('filter', {})
        alpha = filt.get('alpha', '')
        d_safe = filt.get('d_safe', '')
        control_rate = filt.get('control_rate', '')
        prediction_horizon = filt.get('prediction_horizon', '')

    dmin = _d_min(data['robot_xy'], data['obstacle_xy'])
    infeasible_count = sum(1 for s in data['qp_statuses'] if s == 'infeasible')

    row = {
        'run_name': os.path.basename(bag_dir.rstrip('/').rstrip('\\')),
        'bag_dir': bag_dir,
        'n_msgs': data['n_msgs'],
        'alpha': alpha,
        'd_safe': d_safe,
        'control_rate': control_rate,
        'prediction_horizon': prediction_horizon,
        'd_min': f'{dmin:.4f}' if dmin == dmin else '',  # NaN kontrolu
        'collision': int(dmin < contact_radius) if dmin == dmin else '',
        'margin_violation': (int(dmin < float(d_safe)) if d_safe != '' and dmin == dmin else ''),
        'qp_infeasible_count': infeasible_count,
        'qp_infeasible_any': int(infeasible_count > 0),
        'h_min': f'{min(data["h_values"]):.4f}' if data['h_values'] else '',
        'solve_time_mean_ms': (f'{sum(data["solve_times"]) / len(data["solve_times"]):.4f}'
                                if data['solve_times'] else ''),
        'solve_time_max_ms': f'{max(data["solve_times"]):.4f}' if data['solve_times'] else '',
    }
    return row


def main():
    if len(sys.argv) < 2:
        print('Kullanim: metrics_extractor <results_dir> [output_csv] [--force] '
              f'[--contact-radius R] (varsayilan R={DEFAULT_CONTACT_RADIUS})')
        sys.exit(1)

    results_dir = os.path.expanduser(sys.argv[1])
    args = sys.argv[2:]
    force = '--force' in args
    if '--contact-radius' in args:
        contact_radius = float(args[args.index('--contact-radius') + 1])
    else:
        contact_radius = DEFAULT_CONTACT_RADIUS
    positional = [a for a in args if not a.startswith('--') and a != str(contact_radius)]
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
            new_rows.append(extract_one(bag_dir, contact_radius))
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
