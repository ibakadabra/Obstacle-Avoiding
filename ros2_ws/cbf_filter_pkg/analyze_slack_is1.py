import csv
from collections import defaultdict

rows = []
with open('/home/tusaslab7/tez_cbf/results/metrics.csv', newline='') as f:
    for r in csv.DictReader(f):
        if r['run_name'].startswith('slack_is1_validation_'):
            rows.append(r)

print(f'toplam satir: {len(rows)}')

def fnum(r, key):
    v = r.get(key, '')
    try:
        return float(v)
    except (ValueError, TypeError):
        return float('nan')

groups = defaultdict(list)
for r in rows:
    slack = r['run_name'].split('slack_enabled')[1].split('_velocity')[0]
    vel = r['run_name'].split('velocity0')[1].split('_r')[0]
    groups[(slack, vel)].append(r)

print()
header = ['slack', 'v', 'n', 'contact', 'margin_viol', 'qp_infeas_any', 'infeas_count_mean',
          'interv_integral_mean', 'delta_max_mean', 'delta_integral_mean',
          'delta_active_ratio_mean', 'run_valid']
print(' | '.join(f'{h:>18}' for h in header))
for slack in ['False', 'True']:
    for vel in ['-0.8', '-1.2', '-1.4']:
        rs = groups.get((slack, vel), [])
        n = len(rs)
        if n == 0:
            continue
        contact = sum(int(r['contact']) for r in rs if r['contact'] != '') / n
        margin = sum(int(r['margin_violation']) for r in rs if r['margin_violation'] != '') / n
        infeas_any = sum(int(r['qp_infeasible_any']) for r in rs) / n
        infeas_count = sum(fnum(r, 'qp_infeasible_count') for r in rs) / n
        interv = [fnum(r, 'intervention_integral') for r in rs]
        interv = [x for x in interv if x == x]
        interv_mean = sum(interv) / len(interv) if interv else float('nan')
        dmax = [fnum(r, 'delta_max') for r in rs]
        dmax = [x for x in dmax if x == x]
        dmax_mean = sum(dmax) / len(dmax) if dmax else float('nan')
        dint = [fnum(r, 'delta_integral') for r in rs]
        dint = [x for x in dint if x == x]
        dint_mean = sum(dint) / len(dint) if dint else float('nan')
        dact = [fnum(r, 'delta_active_ratio') for r in rs]
        dact = [x for x in dact if x == x]
        dact_mean = sum(dact) / len(dact) if dact else float('nan')
        valid = sum(int(r['run_valid']) for r in rs)
        row = [slack, vel, str(n), f'{contact:.2f}', f'{margin:.2f}', f'{infeas_any:.2f}',
               f'{infeas_count:.1f}', f'{interv_mean:.3f}', f'{dmax_mean:.4f}',
               f'{dint_mean:.4f}', f'{dact_mean:.3f}', f'{valid}/{n}']
        print(' | '.join(f'{v:>18}' for v in row))
