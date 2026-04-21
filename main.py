import sys
import numpy as np
import json

sys.path.insert(0, 'optimizer')

from data_loader import load_loi, build_campaigns, load_changeover
from runner import run_nsga3, pick_best_per_objective, pick_balanced
from evaluator import evaluate

# ── Config ────────────────────────────────────────────────
LOI_PATH = 'data/LOI_Jan_2026.xlsx'
CO_PATH  = 'data/Section___Thickness_change_over_cost.xlsx'

SM_CAP      = 140    # MT/day
LM_CAP      = 250    # MT/day
N_GEN       = 300
POP_SIZE    = 200
SEED        = 42

OBJ_LABELS  = [
    'Sec CO Time (hrs)',
    'Sec CO Cost (Rs)',
    'Thk CO Cost (Rs)',
    'Late (MT x days)',
    'Storage (MT x days)',
    'Storage Days'
]

SOLUTION_LABELS = [
    'Best Sec CO Time',
    'Best Sec CO Cost',
    'Best Thk CO Cost',
    'Best Late Delivery',
    'Best Storage MT',
    'Best Storage Days',
    'Balanced'
]


def build_schedule(perm, camps, cap, mill, co):
    """
    Builds a detailed rolling schedule from a permutation.
    Returns list of dicts, one per campaign.
    """
    from evaluator import (SHIFT_HRS, SEC_COST,
                           get_sec_time, get_thk_cost,
                           advance_clock, compute_changeover_clock)

    schedule = []
    clock    = 0.0
    prev_sec = None
    prev_thk = None

    for pos in range(len(perm)):
        idx = int(perm[pos])
        c   = camps.iloc[idx]

        sec = c['section']
        thk = c['thickness']
        qty = float(c['qty'])
        due = float(c['max_due'])

        co_type    = 'None'
        co_hrs     = 0.0
        co_cost    = 0.0
        hrs_lost   = 0.0

        # ── Changeover ────────────────────────────────────
        if prev_sec is not None:
            if prev_sec != sec:
                co_type  = 'Section'
                co_hrs   = get_sec_time(co, prev_sec, sec)
                new_clock, hrs_lost = compute_changeover_clock(clock, co_hrs)
                clock    = new_clock
                co_cost  = SEC_COST

            elif prev_thk != thk:
                thk_c = get_thk_cost(co, prev_thk, thk, mill)
                if thk_c and thk_c > 0:
                    co_type  = 'Thickness'
                    co_hrs   = 0.5
                    new_clock, hrs_lost = compute_changeover_clock(clock, co_hrs)
                    clock    = new_clock
                    co_cost  = thk_c

        # ── Rolling ───────────────────────────────────────
        start_day  = clock / SHIFT_HRS
        roll_hrs   = (qty / cap) * SHIFT_HRS
        new_clock, _ = advance_clock(clock, roll_hrs)
        clock        = new_clock
        finish_day   = clock / SHIFT_HRS

        late_days  = max(0.0, finish_day - due)
        early_days = max(0.0, due - finish_day)

        schedule.append({
            'pos'        : pos + 1,
            'section'    : sec,
            'thickness'  : thk,
            'qty'        : round(qty, 3),
            'due_day'    : int(due),
            'start_day'  : round(start_day, 2),
            'finish_day' : round(finish_day, 2),
            'co_type'    : co_type,
            'co_hrs'     : round(co_hrs, 1),
            'co_hrs_lost': round(hrs_lost, 1),
            'co_cost'    : round(co_cost, 0),
            'late_days'  : round(late_days, 2),
            'late_mt'    : round(qty * late_days, 2),
            'early_days' : round(early_days, 2),
            'storage_mt' : round(qty * early_days, 2),
        })

        prev_sec = sec
        prev_thk = thk

    return schedule


def main():
    print("Loading data...")
    loi = load_loi(LOI_PATH)
    co  = load_changeover(CO_PATH)

    sm_camps = build_campaigns(loi, 'SM')
    lm_camps = build_campaigns(loi, 'LM')

    print(f"SM campaigns: {len(sm_camps)} | LM campaigns: {len(lm_camps)}")

    # ── Run NSGA-III ──────────────────────────────────────
    print("\n=== Running SM Mill ===")
    res_sm = run_nsga3(sm_camps, SM_CAP, 'SM', co,
                       n_gen=N_GEN, pop_size=POP_SIZE, seed=SEED)

    print("\n=== Running LM Mill ===")
    res_lm = run_nsga3(lm_camps, LM_CAP, 'LM', co,
                       n_gen=N_GEN, pop_size=POP_SIZE, seed=SEED)

    # ── Select solutions ──────────────────────────────────
    def get_solutions(res, camps, cap, mill):
        F    = res.F
        X    = res.X
        best = pick_best_per_objective(F)
        bal  = pick_balanced(F)
        idxs = best + [bal]

        solutions = []
        for i, idx in enumerate(idxs):
            perm  = X[idx]
            f_val = F[idx]
            sched = build_schedule(perm, camps, cap, mill, co)
            solutions.append({
                'label'    : SOLUTION_LABELS[i],
                'objectives': {
                    OBJ_LABELS[j]: round(float(f_val[j]), 2)
                    for j in range(len(OBJ_LABELS))
                },
                'schedule' : sched
            })
        return solutions, F.tolist()

    sm_solutions, sm_pareto = get_solutions(res_sm, sm_camps, SM_CAP, 'SM')
    lm_solutions, lm_pareto = get_solutions(res_lm, lm_camps, LM_CAP, 'LM')

    # ── Save results to JSON ──────────────────────────────
    output = {
        'obj_labels'   : OBJ_LABELS,
        'sol_labels'   : SOLUTION_LABELS,
        'sm': {
            'solutions': sm_solutions,
            'pareto_f' : sm_pareto
        },
        'lm': {
            'solutions': lm_solutions,
            'pareto_f' : lm_pareto
        }
    }

    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    with open('outputs/results.json', 'w') as f:
        json.dump(output, f, indent=2, cls=NumpyEncoder)

    print("\nDone. Results saved to outputs/results.json")

    # ── Print summary ─────────────────────────────────────
    for mill_label, solutions in [('SM', sm_solutions), ('LM', lm_solutions)]:
        print(f"\n{'='*50}")
        print(f"{mill_label} MILL — Solution Summary")
        print(f"{'='*50}")
        for sol in solutions:
            print(f"\n  {sol['label']}")
            for k, v in sol['objectives'].items():
                print(f"    {k:<25} {v:>12.2f}")


if __name__ == '__main__':
    main()