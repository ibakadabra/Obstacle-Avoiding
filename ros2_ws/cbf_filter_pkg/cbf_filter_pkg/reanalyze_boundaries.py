"""Sinir yeniden analizi (BOUNDARY_ANALYSIS_FIX_SPEC, 7 Ağu 2026).

DUZELTME 1: uc sinir (carpisma / marj / feasibility) TEK KOSU HAVUZUNDAN
cikarilir. Eski boundary_search her metrik icin ayri ikili arama yapip
farkli bracket araliklarindan interpolasyon uretiyordu -- bu, uc metrigin
YAPISAL iliskisini (margin_rate >= contact_rate, L<=0.15 iken) bozan
mantiksal-imkansiz sonuclar veriyordu (or. alpha=0.3'te marj v_crit >
carpisma v_crit). Bu script her (hucre, v) noktasindaki TUM kosulardan
uc metrigi birden hesaplar ve v_crit'leri AYNI (v->oran) tablosundan
interpolasyonla turetir -- yapisal iliski otomatik korunur.

DUZELTME 2/3: metrics_extractor'in yeni metrikleri kullanilir --
body_margin_violation (L'den bagimsiz) ve delta_active_ratio_{001,005,010}
(kisit-olcegine normalize, uc esikte).

YENI KOSU YOK: mevcut bnd_* bag'lerini okur.

Kullanim:
    ros2 run cbf_filter_pkg reanalyze_boundaries [camp1 camp2 ...]
    (varsayilan: bnd_w_w bnd_alpha bnd_L)
"""
import csv
import glob
import os
import re
import sys

from cbf_filter_pkg.metrics_extractor import (
    DEFAULT_CONTACT_DISTANCE, DEFAULT_D_SAFE, extract_one)

RESULTS_DIR = os.path.expanduser('~/tez_cbf/results')
OUT_CSV = os.path.join(RESULTS_DIR, 'boundary_reanalyzed.csv')
TARGET = 0.5
CONTACT_DIST = DEFAULT_CONTACT_DISTANCE   # 0.3737
D_SAFE = DEFAULT_D_SAFE                    # 0.5237 (nominal; hucrede degisebilir)

# Cikarilacak metrikler: (isim, CSV alani). delta_active uc esikte.
METRICS = [
    ('contact', 'contact'),
    ('margin', 'margin_violation'),
    ('body_margin', 'body_margin_violation'),
    ('feas_001', 'delta_active_ratio_001'),
    ('feas_005', 'delta_active_ratio_005'),
    ('feas_010', 'delta_active_ratio_010'),
]


def parse_run(name, campaign):
    """'bnd_w_w_w_w0.25_v0.6_r3_2026-...' -> (cell='w_w0.25', v=0.6)."""
    rest = name[len(campaign) + 1:]
    m = re.search(r'_v([0-9.]+)_r\d+', rest)
    if not m:
        return None, None
    v = float(m.group(1))
    cell = rest[:m.start()]
    return cell, v


def rate_at(runs, field):
    """Bir (hucre,v) noktasindaki kosulardan bir metrigin orani.
    run_valid=0 kosular DISLANIR (İŞ 4). delta_active_ratio SUREKLI bir
    deger (0..1) oldugu icin: 'o kosuda aktif oldu mu' = ratio > 0 sayilir,
    sonra kosular arasi ORTALAMA alinir (kac kosuda aktif oldu)."""
    valid = [r for r in runs if str(r.get('run_valid', '1')) == '1']
    if not valid:
        return float('nan'), 0
    if field.startswith('delta_active_ratio'):
        cnt = tot = 0
        for r in valid:
            raw = r.get(field, '')
            if raw in ('', None):
                continue
            tot += 1
            try:
                if float(raw) > 1e-9:
                    cnt += 1
            except ValueError:
                tot -= 1
        return (cnt / tot if tot else float('nan')), len(valid)
    vals = [r[field] for r in valid if r.get(field) not in ('', None)]
    if not vals:
        return float('nan'), len(valid)
    return sum(int(v) for v in vals) / len(vals), len(valid)


def interp_vcrit(points, target=TARGET):
    """points: [(v, rate), ...]. rate hedefi (0.5) yukari-gecen ilk aralikta
    lineer interpolasyon. Doner: (v_crit|nan, status, bracket)."""
    pts = sorted((v, r) for v, r in points if r == r)  # NaN ele
    if not pts:
        return float('nan'), 'NO_DATA', None
    rates = [r for _, r in pts]
    if all(r < target for r in rates):
        return float('nan'), 'ALL_BELOW', None    # sinir araligin USTUNDE
    if all(r >= target for r in rates):
        return float('nan'), 'ALL_ABOVE', None     # sinir araligin ALTINDA
    for (v0, r0), (v1, r1) in zip(pts, pts[1:]):
        if (r0 < target <= r1) or (r0 >= target > r1):
            if r1 == r0:
                vc = 0.5 * (v0 + v1)
            else:
                vc = v0 + (target - r0) * (v1 - v0) / (r1 - r0)
            return vc, 'OK', (v0, v1)
    # monoton degil (gurultu): ilk gecisi yine de yakala
    for (v0, r0), (v1, r1) in zip(pts, pts[1:]):
        if (r0 - target) * (r1 - target) < 0:
            vc = v0 + (target - r0) * (v1 - v0) / (r1 - r0)
            return vc, 'OK_NONMONO', (v0, v1)
    return float('nan'), 'NO_CROSSING', None


def main():
    campaigns = sys.argv[1:] or ['bnd_w_w', 'bnd_alpha', 'bnd_L']
    print(f'Yeniden analiz: {campaigns}')

    out_rows = []
    warnings = []
    gap_report = []

    for camp in campaigns:
        bags = sorted(glob.glob(os.path.join(RESULTS_DIR, camp + '_*')))
        bags = [b for b in bags if os.path.isdir(b)
                and os.path.exists(os.path.join(b, 'metadata.yaml'))]
        if not bags:
            print(f'  {camp}: bag YOK, atlaniyor')
            continue

        # (cell, v) -> [run_row, ...]
        pool = {}
        for b in bags:
            name = os.path.basename(b)
            cell, v = parse_run(name, camp)
            if cell is None:
                continue
            try:
                row = extract_one(b, CONTACT_DIST)
            except Exception as e:
                print(f'    METRIK HATASI ({name}): {e!r}')
                continue
            pool.setdefault((cell, v), []).append(row)

        cells = sorted({c for c, _ in pool})
        print(f'  {camp}: {len(bags)} bag, {len(cells)} hucre')

        for cell in cells:
            vs = sorted({v for c, v in pool if c == cell})
            # her metrik icin (v->oran) tablosu -- AYNI havuzdan
            per_metric = {}
            for mname, field in METRICS:
                pts = []
                for v in vs:
                    r, n = rate_at(pool[(cell, v)], field)
                    pts.append((v, r))
                per_metric[mname] = pts

            # gap kontrolu (DUZELTME 1 eki): temas ile d_safe arasindaki
            # bantta (0.3737 < d_min < 0.5237) kac kosu var? Bu bant
            # "ihlal var ama temas yok" rejimidir; bos olmasi supheli.
            band = 0
            for v in vs:
                for r in pool[(cell, v)]:
                    dm = r.get('d_min', '')
                    if dm in ('', None):
                        continue
                    if CONTACT_DIST < float(dm) < D_SAFE:
                        band += 1
            gap_report.append((camp, cell, band))

            vcrit = {}
            for mname, _ in METRICS:
                vc, st, br = interp_vcrit(per_metric[mname])
                vcrit[mname] = (vc, st)
                out_rows.append({
                    'campaign': camp, 'cell': cell, 'metric': mname,
                    'v_crit': f'{vc:.4f}' if vc == vc else '',
                    'status': st,
                    'n_points': len(per_metric[mname]),
                    'points_detail': ';'.join(
                        f'{v:.3f}:{r:.2f}' for v, r in per_metric[mname] if r == r),
                })

            # DUZELTME 1 yapisal dogrulama: L<=0.15 iken
            # v_crit(marj) <= v_crit(carpisma) OLMALI (ucgen esitsizligi).
            L = _cell_L(cell)
            if L is not None and L <= (D_SAFE - CONTACT_DIST):
                vc_c = vcrit['contact'][0]
                vc_m = vcrit['margin'][0]
                if vc_c == vc_c and vc_m == vc_m and vc_m > vc_c + 0.05:
                    warnings.append(
                        f'YAPISAL IHLAL {camp}/{cell}: marj v_crit={vc_m:.3f} > '
                        f'carpisma v_crit={vc_c:.3f} (L={L}, fark '
                        f'{vc_m - vc_c:.3f}) -- ucgen esitsizligini bozuyor')

    with open(OUT_CSV, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['campaign', 'cell', 'metric', 'v_crit',
                                          'status', 'n_points', 'points_detail'])
        w.writeheader()
        w.writerows(out_rows)

    print(f'\n{len(out_rows)} satir -> {OUT_CSV}')
    print('\n=== YAPISAL DOGRULAMA ===')
    if warnings:
        for wn in warnings:
            print('  ' + wn)
    else:
        print('  Tum L<=0.15 hucrelerde marj v_crit <= carpisma v_crit (+tol). '
              'DUZELTME 1 tutarli.')
    print('\n=== GAP KONTROLU (temas-d_safe bandindaki kosu sayisi) ===')
    for camp, cell, band in gap_report:
        flag = ' <-- BOS (supheli)' if band == 0 else ''
        print(f'  {camp:10} {cell:18} band_kosu={band}{flag}')


def _cell_L(cell):
    m = re.search(r'lookahead_L([0-9.]+)', cell)
    if m:
        return float(m.group(1))
    # L taramasi disindaki kampanyalar varsayilan L=0.10 kullanir
    if cell.startswith('w_w') or cell.startswith('alpha'):
        return 0.10
    return None


if __name__ == '__main__':
    main()
