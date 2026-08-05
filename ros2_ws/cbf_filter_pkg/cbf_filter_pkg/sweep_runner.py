"""Parametre süpürme koşucusu (Öncelik 6, deney koşucusu spec'i).

Tek bir YAML'dan tam bir deney matrisi koşar: `sweep:` bloğundaki her
parametre ekseninin kartezyen çarpımı × `runs_per_cell` tekrar.

Beklenen YAML (temel senaryo alanları scenario_node ile aynı, artı):
    sweep:
      filter.control_rate: [10.0, 20.0, 50.0]
    runs_per_cell: 10

Her hücre × tekrar için:
  1. temel config'in üstüne o hücrenin değerleri yazılır (nokta-yollu anahtar,
     ör. `filter.control_rate` -> cfg['filter']['control_rate'])
  2. geçici bir config dosyası yazılır
  3. scenario_node ALT SÜREÇ olarak çalıştırılır (her koşu kendi temiz
     sürecinde: rclpy context'i koşular arası yeniden kullanılamaz, ayrıca
     bir koşunun çökmesi kampanyayı düşürmez)
  4. koşu adı `<isim>_<hücre>_r<tekrar>_<zaman damgası>` olur, böylece
     metrics_extractor'ın ürettiği CSV'de hücreler ayırt edilebilir

Kampanya devam ettirilebilir: tamamlanmış koşular (bag dizini + _config.yaml
mevcut olanlar) atlanır, böylece yarıda kesilen bir matris `--resume` ile
kaldığı yerden sürer.

Kullanım:
    ros2 run cbf_filter_pkg sweep_runner <sweep_config.yaml> [--resume] [--dry-run]
"""
import copy
import itertools
import os
import subprocess
import sys
import time

import yaml

RESULTS_DIR = os.path.expanduser('~/tez_cbf/results')


def _split_index(part: str):
    """'start[1]' -> ('start', 1);  'mode' -> ('mode', None)."""
    if part.endswith(']') and '[' in part:
        name, idx = part[:-1].split('[')
        return name, int(idx)
    return part, None


def set_dotted(cfg: dict, dotted_key: str, value) -> None:
    """cfg['filter']['control_rate'] = value  <-  'filter.control_rate'
    Liste elemanlarina da yazabilir (İŞ 5.3):
    cfg['scenario']['obstacle']['start'][1] = value  <-  'scenario.obstacle.start[1]'
    (ornegin sadece engelin y baslangicini degistirmek, x/theta'ya dokunmadan)."""
    parts = dotted_key.split('.')
    node = cfg
    for p in parts[:-1]:
        name, idx = _split_index(p)
        node = node.setdefault(name, {})
        if idx is not None:
            node = node[idx]
    last_name, last_idx = _split_index(parts[-1])
    if last_idx is not None:
        node[last_name][last_idx] = value
    else:
        node[last_name] = value


def cell_label(cell: dict) -> str:
    """Hucreyi dosya adinda kullanilabilir kisa bir etikete cevirir."""
    bits = []
    for key, value in cell.items():
        short = key.split('.')[-1].replace('[', '').replace(']', '')
        bits.append(f'{short}{value}')
    return '_'.join(bits)


def main():
    if len(sys.argv) < 2:
        print('Kullanim: sweep_runner <sweep_config.yaml> [--resume] [--dry-run]')
        sys.exit(1)

    sweep_path = os.path.expanduser(sys.argv[1])
    resume = '--resume' in sys.argv
    dry_run = '--dry-run' in sys.argv

    with open(sweep_path) as f:
        base_cfg = yaml.safe_load(f)

    sweep_axes = base_cfg.pop('sweep', {})
    runs_per_cell = int(base_cfg.pop('runs_per_cell', 1))
    base_name = base_cfg.get('scenario', {}).get('name', 'run')

    if not sweep_axes:
        print('UYARI: `sweep:` blogu yok -> tek hucre, sadece runs_per_cell tekrari.')
        cells = [{}]
    else:
        keys = list(sweep_axes.keys())
        cells = [dict(zip(keys, combo))
                 for combo in itertools.product(*(sweep_axes[k] for k in keys))]

    total = len(cells) * runs_per_cell
    print(f'Matris: {len(cells)} hucre x {runs_per_cell} tekrar = {total} kosu')
    for c in cells:
        print(f'  hucre: {c}')

    os.makedirs(RESULTS_DIR, exist_ok=True)
    tmp_dir = os.path.expanduser('~/tez_cbf/.sweep_tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    done = failed = skipped = 0
    t_start = time.time()

    for cell in cells:
        label = cell_label(cell) if cell else 'base'
        for rep in range(1, runs_per_cell + 1):
            run_prefix = f'{base_name}_{label}_r{rep}'

            if resume and any(d.startswith(run_prefix + '_')
                              and os.path.isdir(os.path.join(RESULTS_DIR, d))
                              for d in os.listdir(RESULTS_DIR)):
                print(f'[ATLA] {run_prefix} zaten var')
                skipped += 1
                continue

            cfg = copy.deepcopy(base_cfg)
            for key, value in cell.items():
                set_dotted(cfg, key, value)
            # scenario.name'i hucre/tekrar bilgisiyle degistir: bag dizin adi
            # bundan turedigi icin CSV'de hucreler ayirt edilebilir olur.
            cfg.setdefault('scenario', {})['name'] = run_prefix

            cfg_path = os.path.join(tmp_dir, f'{run_prefix}.yaml')
            with open(cfg_path, 'w') as f:
                yaml.safe_dump(cfg, f)

            n = done + failed + skipped + 1
            print(f'[{n}/{total}] {run_prefix} ...', flush=True)

            if dry_run:
                done += 1
                continue

            # Her kosu KENDI surecinde: rclpy context'i tek surecte tekrar
            # tekrar init/shutdown edilemiyor, ayrica bir kosunun cokmesi
            # kampanyayi dusurmemeli.
            result = subprocess.run(
                ['ros2', 'run', 'cbf_filter_pkg', 'scenario_node', cfg_path],
                capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                done += 1
            else:
                failed += 1
                print(f'  HATA (kod {result.returncode}): '
                      f'{result.stderr.strip()[-300:]}')

            time.sleep(2.0)  # kosular arasi nefes payi

    dt = time.time() - t_start
    print(f'\nKAMPANYA BITTI: {done} basarili, {failed} hatali, {skipped} atlandi '
          f'({dt / 60:.1f} dk)')
    print('Metrikleri cikarmak icin:\n'
          '  ros2 run cbf_filter_pkg metrics_extractor ~/tez_cbf/results')


if __name__ == '__main__':
    main()
