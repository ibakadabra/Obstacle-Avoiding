"""Sinir takibi kosucusu (İŞ 2, "Slack'li QP + Parametre Eksenleri" spec'i).

NEDEN TAM IZGARA DEGIL: dort parametre ekseni (T x alpha x L x w_w) tam
izgarayla carpilinca ~172.000 kosu (~1000+ saat) ediyor. Aranan sey bir
YUZEY degil bir EGRI: sinirin NEREDE oldugu. Bu modul, sabit bir yanal
ofsette hiz eksenini tarayip KRITIK HIZ'i (v_crit) ikili aramayla bulur:
nokta basina ~60 kosu.

sweep_runner'dan TEMEL FARKI: sweep_runner kosulari korlemesine atar,
metrikleri sonradan (ayri bir metrics_extractor cagrisiyla) okur. Burada
GERI BESLEME DONGUSU var -- her nokta kosulduktan sonra metrikleri
HEMEN cikarilir, orana bakilir, SONRAKI noktanin nerede olacagina ona
gore karar verilir. Bu yuzden extract_one() dogrudan import edilir.

Aranan uc AYRI sinir (spec, "IKINCIL SINIR"): bunlar farkli seyler ve
farkli yerlerde olabilir -- ucunun birbirine gore konumu bulgunun kendisi:
  contact_rate          -> CARPISMA siniri     (fiziksel guvenlik)
  margin_violation_rate -> MARJ siniri         (tasarim garantisi, h<0)
  delta_active_rate     -> FEASIBILITY siniri  (aktuator limiti baglayici)

Nokta onbellegi (point cache): ayni v degeri birden fazla metrigin
aramasinda gectiginde YENIDEN KOSULMAZ. Boylece kaba tarama uc metrik
arasinda paylasilir.

Beklenen YAML:
    mode: boundary_search
    search:
      axis: scenario.obstacle.velocity[0]
      sign: -1                  # eksen degeri bu isaretle carpilarak yazilir
      coarse_points: [0.6, 0.9, 1.2, 1.5]
      refine_steps: 2
      target_metrics: [contact_rate, margin_violation_rate, delta_active_rate]
      target_value: 0.5
      runs_per_point: 10
    fixed:
      scenario.obstacle.start[1]: 0.3
      filter.slack_enabled: true
    sweep:                      # her kombinasyon icin AYRI v_crit aranir
      filter.alpha: [0.3, 1.0, 2.0]

Kullanim:
    ros2 run cbf_filter_pkg boundary_search <config.yaml> [--resume] [--dry-run]

Cikti: ~/tez_cbf/results/boundary_results.csv -- her parametre
kombinasyonu x hedef metrik icin BIR satir (v_crit + guven araligi).
"""
import copy
import csv
import glob
import itertools
import os
import subprocess
import sys
import time

import yaml

from cbf_filter_pkg.metrics_extractor import (
    DEFAULT_CONTACT_DISTANCE, extract_one)
from cbf_filter_pkg.sweep_runner import cell_label, set_dotted

RESULTS_DIR = os.path.expanduser('~/tez_cbf/results')
BOUNDARY_CSV = os.path.join(RESULTS_DIR, 'boundary_results.csv')

BOUNDARY_FIELDS = [
    'campaign', 'cell', 'target_metric', 'target_value',
    'v_crit', 'v_lo', 'v_hi', 'rate_lo', 'rate_hi', 'bracket_width',
    'status', 'n_points_evaluated', 'runs_per_point', 'total_runs',
    'points_detail',
]

# delta_active_ratio bu esigin ustundeyse o kosuda "aktuator limiti
# baglayici" sayilir (spec: "delta_active_ratio > 0 baslangici"; tam
# sifir yerine kucuk bir esik, kayan nokta gurultusune karsi).
DELTA_ACTIVE_RUN_THRESH = 1e-6


def _rate(rows, metric_name: str) -> float:
    """Bir noktadaki kosulardan hedef metrigin ORANINI hesaplar.
    run_valid=0 olan kosular DISLANIR (İŞ 4 karari: aykiri kosular
    ortalamalari bozmasin, ama gizlenmesinler de -- burada dislaniyorlar
    ve sayilari points_detail'de raporlaniyor)."""
    valid = [r for r in rows if str(r.get('run_valid', '1')) == '1']
    if not valid:
        return float('nan')
    n = len(valid)

    if metric_name == 'contact_rate':
        vals = [r['contact'] for r in valid if r['contact'] != '']
        return sum(int(v) for v in vals) / len(vals) if vals else float('nan')

    if metric_name == 'margin_violation_rate':
        vals = [r['margin_violation'] for r in valid if r['margin_violation'] != '']
        return sum(int(v) for v in vals) / len(vals) if vals else float('nan')

    if metric_name == 'delta_active_rate':
        # "delta_active_ratio > 0" olan KOSULARIN orani -- yani kac kosuda
        # aktuator limiti hic baglayici oldu.
        cnt = tot = 0
        for r in valid:
            raw = r.get('delta_active_ratio', '')
            if raw in ('', None):
                continue
            tot += 1
            try:
                if float(raw) > DELTA_ACTIVE_RUN_THRESH:
                    cnt += 1
            except ValueError:
                tot -= 1
        return cnt / tot if tot else float('nan')

    raise ValueError(f'bilinmeyen hedef metrik: {metric_name}')


def _interp_crossing(v_lo, r_lo, v_hi, r_hi, target) -> float:
    """Iki nokta arasinda hedef oranin gectigi hizi LINEER interpolasyonla
    tahmin eder. Oranlar esitse (duz parca) araligin ortasi dondurulur."""
    if r_hi == r_lo:
        return 0.5 * (v_lo + v_hi)
    return v_lo + (target - r_lo) * (v_hi - v_lo) / (r_hi - r_lo)


class PointRunner:
    """Bir (hucre, v) noktasini kosar ve metrik satirlarini dondurur.
    ONBELLEKLI: ayni nokta birden fazla metrigin aramasinda gecerse
    yeniden kosulmaz."""

    def __init__(self, base_cfg, fixed, cell, axis, sign, runs_per_point,
                 campaign_name, tmp_dir, dry_run=False, resume=False):
        self.base_cfg = base_cfg
        self.fixed = fixed
        self.cell = cell
        self.axis = axis
        self.sign = sign
        self.runs_per_point = runs_per_point
        self.campaign_name = campaign_name
        self.tmp_dir = tmp_dir
        self.dry_run = dry_run
        self.resume = resume
        self.cache = {}          # v (yuvarlanmis) -> rows
        self.total_runs = 0

    def _key(self, v):
        return round(float(v), 4)

    def evaluate(self, v):
        key = self._key(v)
        if key in self.cache:
            print(f'    [ONBELLEK] v={key} zaten kosuldu, tekrar kosulmuyor')
            return self.cache[key]

        rows = []
        cell_tag = cell_label(self.cell) if self.cell else 'base'
        for rep in range(1, self.runs_per_point + 1):
            run_prefix = f'{self.campaign_name}_{cell_tag}_v{key}_r{rep}'

            existing = sorted(glob.glob(os.path.join(RESULTS_DIR, run_prefix + '_*')))
            existing = [d for d in existing if os.path.isdir(d)
                        and os.path.exists(os.path.join(d, 'metadata.yaml'))]
            if self.resume and existing:
                print(f'    [ATLA] {run_prefix} zaten var')
                bag_dir = existing[-1]
            elif self.dry_run:
                print(f'    [KURU] {run_prefix}')
                continue
            else:
                cfg = copy.deepcopy(self.base_cfg)
                for k, val in self.fixed.items():
                    set_dotted(cfg, k, val)
                for k, val in self.cell.items():
                    set_dotted(cfg, k, val)
                set_dotted(cfg, self.axis, self.sign * float(v))
                cfg.setdefault('scenario', {})['name'] = run_prefix

                cfg_path = os.path.join(self.tmp_dir, f'{run_prefix}.yaml')
                with open(cfg_path, 'w') as f:
                    yaml.safe_dump(cfg, f)

                print(f'    [{rep}/{self.runs_per_point}] {run_prefix} ...', flush=True)
                result = subprocess.run(
                    ['ros2', 'run', 'cbf_filter_pkg', 'scenario_node', cfg_path],
                    capture_output=True, text=True, timeout=300)
                self.total_runs += 1
                if result.returncode != 0:
                    print(f'      HATA (kod {result.returncode}): '
                          f'{result.stderr.strip()[-200:]}')
                    continue
                time.sleep(2.0)

                found = sorted(glob.glob(os.path.join(RESULTS_DIR, run_prefix + '_*')))
                found = [d for d in found if os.path.isdir(d)]
                if not found:
                    print(f'      UYARI: {run_prefix} icin bag dizini bulunamadi')
                    continue
                bag_dir = found[-1]

            try:
                rows.append(extract_one(bag_dir, DEFAULT_CONTACT_DISTANCE))
            except Exception as e:
                print(f'      METRIK HATASI ({os.path.basename(bag_dir)}): {e!r}')

        self.cache[key] = rows
        return rows


def search_boundary(runner, coarse_points, refine_steps, metric, target):
    """Kaba tarama + ikili arama. Dondurulen dict CSV satirina cevrilir."""
    evaluated = []   # (v, rate)

    print(f'  --- {metric} (hedef={target}) ---')
    for v in coarse_points:
        rows = runner.evaluate(v)
        r = _rate(rows, metric)
        evaluated.append((v, r))
        print(f'    v={v}: {metric}={r:.2f}  (n={len(rows)})')

    # Hedefin GECILDIGI ilk araligi bul (rate hedefin altindan ustune cikis)
    bracket = None
    for (v_lo, r_lo), (v_hi, r_hi) in zip(evaluated, evaluated[1:]):
        if r_lo != r_lo or r_hi != r_hi:   # NaN
            continue
        if (r_lo < target <= r_hi) or (r_lo >= target > r_hi):
            bracket = (v_lo, r_lo, v_hi, r_hi)
            break

    if bracket is None:
        rates = [r for _, r in evaluated if r == r]
        if rates and all(r >= target for r in rates):
            status = 'ALL_ABOVE'      # sinir kaba araligin ALTINDA
        elif rates and all(r < target for r in rates):
            status = 'ALL_BELOW'      # sinir kaba araligin USTUNDE
        else:
            status = 'NO_CROSSING'    # monoton degil / NaN
        print(f'    -> gecis bulunamadi ({status})')
        return dict(v_crit=float('nan'), v_lo=float('nan'), v_hi=float('nan'),
                    rate_lo=float('nan'), rate_hi=float('nan'),
                    status=status, evaluated=evaluated)

    v_lo, r_lo, v_hi, r_hi = bracket
    print(f'    -> gecis araligi: [{v_lo}, {v_hi}]  ({r_lo:.2f} -> {r_hi:.2f})')

    for step in range(refine_steps):
        v_mid = 0.5 * (v_lo + v_hi)
        rows = runner.evaluate(v_mid)
        r_mid = _rate(rows, metric)
        evaluated.append((v_mid, r_mid))
        print(f'    [inceltme {step + 1}/{refine_steps}] v={v_mid:.3f}: '
              f'{metric}={r_mid:.2f}')
        if r_mid != r_mid:
            break
        if (r_lo < target <= r_mid) or (r_lo >= target > r_mid):
            v_hi, r_hi = v_mid, r_mid
        else:
            v_lo, r_lo = v_mid, r_mid

    v_crit = _interp_crossing(v_lo, r_lo, v_hi, r_hi, target)
    print(f'    ==> v_crit = {v_crit:.3f}  (aralik [{v_lo:.3f}, {v_hi:.3f}])')
    return dict(v_crit=v_crit, v_lo=v_lo, v_hi=v_hi, rate_lo=r_lo, rate_hi=r_hi,
                status='OK', evaluated=evaluated)


def main():
    if len(sys.argv) < 2:
        print('Kullanim: boundary_search <config.yaml> [--resume] [--dry-run]')
        sys.exit(1)

    cfg_path = os.path.expanduser(sys.argv[1])
    resume = '--resume' in sys.argv
    dry_run = '--dry-run' in sys.argv

    with open(cfg_path) as f:
        full_cfg = yaml.safe_load(f)

    search = full_cfg.pop('search', {})
    fixed = full_cfg.pop('fixed', {}) or {}
    sweep_axes = full_cfg.pop('sweep', {}) or {}
    full_cfg.pop('mode', None)

    axis = search['axis']
    sign = float(search.get('sign', 1.0))
    coarse_points = list(search['coarse_points'])
    refine_steps = int(search.get('refine_steps', 2))
    target_metrics = list(search.get('target_metrics', ['contact_rate']))
    target_value = float(search.get('target_value', 0.5))
    runs_per_point = int(search.get('runs_per_point', 10))
    campaign_name = full_cfg.get('scenario', {}).get('name', 'boundary')

    if sweep_axes:
        keys = list(sweep_axes.keys())
        cells = [dict(zip(keys, combo))
                 for combo in itertools.product(*(sweep_axes[k] for k in keys))]
    else:
        cells = [{}]

    n_pts = len(coarse_points) + refine_steps * len(target_metrics)
    print(f'Kampanya: {campaign_name}')
    print(f'Eksen: {axis} (isaret {sign:+.0f})')
    print(f'Kaba noktalar: {coarse_points}, inceltme: {refine_steps} adim')
    print(f'Hedef metrikler: {target_metrics} (hedef deger {target_value})')
    print(f'{len(cells)} hucre x ~{n_pts} nokta x {runs_per_point} kosu '
          f'= EN FAZLA ~{len(cells) * n_pts * runs_per_point} kosu '
          f'(onbellek sayesinde daha az olacak)')
    for c in cells:
        print(f'  hucre: {c}')

    os.makedirs(RESULTS_DIR, exist_ok=True)
    tmp_dir = os.path.expanduser('~/tez_cbf/.sweep_tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    results = []
    t_start = time.time()

    for cell in cells:
        print(f'\n=== HUCRE: {cell if cell else "(base)"} ===')
        runner = PointRunner(full_cfg, fixed, cell, axis, sign, runs_per_point,
                             campaign_name, tmp_dir, dry_run=dry_run, resume=resume)
        for metric in target_metrics:
            res = search_boundary(runner, coarse_points, refine_steps,
                                  metric, target_value)
            detail = ';'.join(f'{v:.3f}:{r:.2f}' for v, r in sorted(res['evaluated'])
                              if r == r)
            results.append({
                'campaign': campaign_name,
                'cell': cell_label(cell) if cell else 'base',
                'target_metric': metric,
                'target_value': target_value,
                'v_crit': f"{res['v_crit']:.4f}" if res['v_crit'] == res['v_crit'] else '',
                'v_lo': f"{res['v_lo']:.4f}" if res['v_lo'] == res['v_lo'] else '',
                'v_hi': f"{res['v_hi']:.4f}" if res['v_hi'] == res['v_hi'] else '',
                'rate_lo': f"{res['rate_lo']:.3f}" if res['rate_lo'] == res['rate_lo'] else '',
                'rate_hi': f"{res['rate_hi']:.3f}" if res['rate_hi'] == res['rate_hi'] else '',
                'bracket_width': (f"{res['v_hi'] - res['v_lo']:.4f}"
                                  if res['v_hi'] == res['v_hi'] else ''),
                'status': res['status'],
                'n_points_evaluated': len(res['evaluated']),
                'runs_per_point': runs_per_point,
                'total_runs': runner.total_runs,
                'points_detail': detail,
            })

    # BUG DUZELTMESI (7 Ağu 2026): --dry-run modu ONCEDEN de CSV'ye
    # yaziyordu -- bir wiring testi boundary_results.csv'ye 12 adet bos
    # (NaN oranli, NO_CROSSING) satir birakti ve gercek sonuclarla
    # karisti. Kuru kosu SONUC URETMEZ, dosyaya da yazmamali.
    if dry_run:
        print('\n[KURU KOSU] Sonuc dosyasina YAZILMADI (--dry-run).')
        return

    existing = []
    if os.path.exists(BOUNDARY_CSV):
        with open(BOUNDARY_CSV, newline='') as f:
            existing = list(csv.DictReader(f))
    with open(BOUNDARY_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=BOUNDARY_FIELDS)
        writer.writeheader()
        writer.writerows(existing + results)

    dt = time.time() - t_start
    print(f'\nSINIR TAKIBI BITTI ({dt / 60:.1f} dk)')
    print(f'{len(results)} sonuc satiri -> {BOUNDARY_CSV}')
    print('\nOZET:')
    for r in results:
        print(f"  {r['cell']:>20} | {r['target_metric']:>22} | "
              f"v_crit={r['v_crit'] or 'YOK':>8} | {r['status']}")


if __name__ == '__main__':
    main()
