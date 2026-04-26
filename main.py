"""
main.py
-------
Entry point for the Rolling Mill NSGA-III scheduler.

Usage:
    python main.py --loi path/to/loi.xlsx --co path/to/changeover.xlsx

    Optional:
    --sm-cap   SM mill capacity in MT/shift  (default: 100)
    --lm-cap   LM mill capacity in MT/shift  (default: 150)
    --n-gen    Max generations               (default: 2000)
    --pop      Minimum population size       (default: 252)
    --seed     Random seed                   (default: 42)
    --warm-sm  Path to previous SM best perm (.npy file, optional)
    --warm-lm  Path to previous LM best perm (.npy file, optional)
    --save     Save best perms for next cycle warm start (flag)
"""

import argparse
import sys
import os
import time
import numpy as np
import concurrent.futures

from data_loader import (load_loi, load_changeover, build_campaigns,
                         load_actual_plan, build_actual_permutation)
from runner import run_nsga3, pick_best_per_objective, pick_balanced


# ── Objective labels ──────────────────────────────────────
OBJ_LABELS = [
    "Sec CO time (hrs)",
    "Sec CO cost (Rs)",
    "Thk CO cost (Rs)",
    "Late (MT·days)",
    "Storage (MT·days)",
    "Storage (days)",
]

# ── Normalisation denominators (must match evaluator.py) ──
OBJ_DENOMS = [
    400.0,
    10_000_000.0,
    3_000_000.0,
    60_000.0,
    5_000.0,
    250.0,
]


# ── Per-mill runner (called in thread pool) ───────────────

def run_mill(mill, camps, cap, co, n_gen, pop_size, seed,
             last_best_perm, actual_perm):
    """
    Runs NSGA-III for one mill.
    Returns (mill, result, callback) or (mill, None, None) on error.
    """
    print(f"\n{'='*60}")
    print(f"  Starting optimisation: {mill} mill")
    print(f"  Campaigns to schedule: {len(camps)}")
    print(f"{'='*60}")

    if len(camps) == 0:
        print(f"[{mill}] No campaigns found — skipping.")
        return mill, None, None

    try:
        t0 = time.time()
        result, callback = run_nsga3(
            camps          = camps,
            cap            = cap,
            mill           = mill,
            co             = co,
            n_gen          = n_gen,
            pop_size       = pop_size,
            seed           = seed,
            last_best_perm = last_best_perm,
            actual_perm    = actual_perm
        )
        elapsed = time.time() - t0
        print(f"[{mill}] Completed in {elapsed:.1f}s")
        return mill, result, callback

    except Exception as e:
        print(f"[{mill}] ERROR during optimisation: {e}")
        import traceback
        traceback.print_exc()
        return mill, None, None


# ── Result printer ────────────────────────────────────────

def print_results(mill, result, callback):
    if result is None or result.F is None or len(result.F) == 0:
        print(f"\n[{mill}] No feasible solutions found.")
        return

    F = result.F
    X = result.X

    print(f"\n{'='*60}")
    print(f"  RESULTS: {mill} mill")
    print(f"  Pareto front size: {len(F)} solutions")
    print(f"{'='*60}")

    # ── Best per objective ────────────────────────────────
    print(f"\n  Best solution per objective:")
    print(f"  {'Objective':<24} {'Best Value':>15}  {'Sequence index':>5}")
    print(f"  {'-'*50}")

    best_indices = pick_best_per_objective(F)
    for obj_i, sol_i in enumerate(best_indices):
        raw_val = F[sol_i, obj_i] * OBJ_DENOMS[obj_i]
        print(f"  {OBJ_LABELS[obj_i]:<24} {raw_val:>15.1f}  #{sol_i}")

    # ── Balanced solution ─────────────────────────────────
    bal_i = pick_balanced(F)
    print(f"\n  Balanced solution (TOPSIS): #{bal_i}")
    print(f"  {'Objective':<24} {'Value':>15}")
    print(f"  {'-'*40}")
    for obj_i in range(F.shape[1]):
        raw_val = F[bal_i, obj_i] * OBJ_DENOMS[obj_i]
        print(f"  {OBJ_LABELS[obj_i]:<24} {raw_val:>15.1f}")

    # ── Balanced sequence ─────────────────────────────────
    print(f"\n  Balanced rolling sequence:")
    print(f"  {'Pos':<5} {'Campaign index':>14}")
    print(f"  {'-'*22}")
    for pos, camp_idx in enumerate(X[bal_i]):
        print(f"  {pos+1:<5} {camp_idx:>14}")

    print(f"\n  Convergence history: "
          f"{len(callback.hypervolume)} generations recorded")
    print(f"  Initial HV : {callback.hypervolume[0]:.4f}")
    print(f"  Final HV   : {callback.hypervolume[-1]:.4f}")
    improvement = (
        (callback.hypervolume[-1] - callback.hypervolume[0])
        / max(callback.hypervolume[0], 1e-9) * 100
    )
    print(f"  HV gain    : {improvement:.1f}%")

def build_schedule(perm, camps, mill, co):
    from evaluator import (SHIFT_HRS, THK_CO_HRS, SEC_COST,
                           get_sec_time, get_thk_cost,
                           compute_changeover_clock, advance_clock)
    from data_loader import MILL_CAPACITY

    cap      = MILL_CAPACITY[mill]
    schedule = []
    clock    = 0.0
    prev_sec = prev_thk = None

    for pos, idx in enumerate(perm):
        c   = camps.iloc[int(idx)]
        sec = c['section']
        thk = c['thickness']
        qty = float(c['qty'])
        due = float(c['due'])

        co_type     = 'None'
        co_hrs      = 0.0
        co_hrs_lost = 0.0
        co_cost     = 0.0

        if prev_sec is not None:
            if prev_sec != sec:
                co_type  = 'Section'
                hrs      = get_sec_time(co, prev_sec, sec)
                if hrs is not None:
                    new_clock, lost = compute_changeover_clock(clock, hrs)
                    co_hrs      = hrs
                    co_hrs_lost = lost
                    co_cost     = SEC_COST
                    clock       = new_clock
            elif prev_thk != thk:
                thk_c = get_thk_cost(co, prev_thk, thk, mill)
                if thk_c is not None and thk_c > 0:
                    co_type = 'Thickness'
                    co_hrs  = THK_CO_HRS
                    co_cost = thk_c
                    clock  += THK_CO_HRS

        start_day    = clock / SHIFT_HRS
        roll_hrs     = (qty / cap) * SHIFT_HRS
        new_clock, _ = advance_clock(clock, roll_hrs)
        clock        = new_clock
        finish_day   = clock / SHIFT_HRS

        late_days  = max(0.0, finish_day - due)
        early_days = max(0.0, due - finish_day)

        schedule.append({
            'pos'        : pos + 1,
            'section'    : sec,
            'thickness'  : int(thk),
            'qty'        : round(qty, 2),
            'due_day'    : int(due),
            'start_day'  : round(start_day, 3),
            'finish_day' : round(finish_day, 3),
            'co_type'    : co_type,
            'co_hrs'     : co_hrs,
            'co_hrs_lost': co_hrs_lost,
            'co_cost'    : co_cost,
            'late_days'  : round(late_days, 3),
            'late_mt'    : round(qty * late_days, 2),
            'early_days' : round(early_days, 3),
            'storage_mt' : round(qty * early_days, 2),
        })

        prev_sec = sec
        prev_thk = thk

    return schedule

# ── Warm start save/load ──────────────────────────────────

def save_results_json(mills, results, callbacks, camps_dict, co):
    import json

    output = {}

    for mill in mills:
        mill_key = mill.lower()
        result   = results[mill]
        callback = callbacks[mill]
        camps    = camps_dict[mill]

        if result is None or result.F is None or len(result.F) == 0:
            output[mill_key] = None
            continue

        F = result.F
        X = result.X

        solutions = []

        # Best per objective
        best_indices = pick_best_per_objective(F)
        for obj_i, sol_i in enumerate(best_indices):
            perm       = X[sol_i]
            schedule   = build_schedule(perm, camps, mill, co)
            objectives = {
                label: round(F[sol_i, j] * OBJ_DENOMS[j], 2)
                for j, label in enumerate(OBJ_LABELS)
            }
            solutions.append({
                'label'     : f'Best {OBJ_LABELS[obj_i]}',
                'index'     : int(sol_i),
                'objectives': objectives,
                'schedule'  : schedule
            })

        # Balanced solution
        bal_i      = pick_balanced(F)
        perm       = X[bal_i]
        schedule   = build_schedule(perm, camps, mill, co)
        objectives = {
            label: round(F[bal_i, j] * OBJ_DENOMS[j], 2)
            for j, label in enumerate(OBJ_LABELS)
        }
        solutions.append({
            'label'     : 'Balanced (TOPSIS)',
            'index'     : int(bal_i),
            'objectives': objectives,
            'schedule'  : schedule
        })

        # Actual plan campaigns for comparison tab
        actual_camps = []
        for _, row in camps.iterrows():
            actual_camps.append({
                'section'  : row['section'],
                'thickness': int(row['thickness']),
                'qty'      : round(float(row['qty']), 2),
                'maxDue'   : int(row['due'])
            })

        output[mill_key] = {
            'solutions'   : solutions,
            'actual_camps': actual_camps,
            'convergence' : {
                'generations': callback.gen_numbers,
                'hypervolume': [round(h, 6) for h in callback.hypervolume],
                'diversity'  : [round(d, 4) for d in callback.diversity],
            }
        }

    with open('results.json', 'w') as f:
        json.dump(output, f, indent=2)
    print("\nResults saved → results.json")
    
def load_warm_perm(path):
    if path and os.path.exists(path):
        perm = np.load(path)
        print(f"  Loaded warm start: {path} ({len(perm)} campaigns)")
        return perm
    return None


def save_warm_perm(result, mill, pick_fn):
    if result is None or result.X is None:
        return
    bal_i = pick_fn(result.F)
    perm  = result.X[bal_i]
    fname = f"warm_start_{mill}.npy"
    np.save(fname, perm)
    print(f"  Saved warm start → {fname}")


# ── Main ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Rolling Mill NSGA-III Scheduler"
    )
    parser.add_argument('--loi',      required=True,
                        help='Path to LOI Excel file')
    parser.add_argument('--co',       required=True,
                        help='Path to changeover Excel file')
    parser.add_argument('--sm-cap',   type=float, default=100.0,
                        help='SM mill capacity MT/shift (default 100)')
    parser.add_argument('--lm-cap',   type=float, default=150.0,
                        help='LM mill capacity MT/shift (default 150)')
    parser.add_argument('--n-gen',    type=int,   default=2000,
                        help='Max generations (default 2000)')
    parser.add_argument('--pop',      type=int,   default=252,
                        help='Min population size (default 252)')
    parser.add_argument('--seed',     type=int,   default=42,
                        help='Random seed (default 42)')
    parser.add_argument('--actual-sm', default=None,
                        help='Path to actual SM rolling plan Excel file')
    parser.add_argument('--actual-lm', default=None,
                        help='Path to actual LM rolling plan Excel file')
    parser.add_argument('--warm-sm',  default=None,
                        help='Path to SM warm start .npy file')
    parser.add_argument('--warm-lm',  default=None,
                        help='Path to LM warm start .npy file')
    parser.add_argument('--save',     action='store_true',
                        help='Save best perms for next cycle warm start')
    args = parser.parse_args()

    t_total = time.time()

    # ── Load data ─────────────────────────────────────────
    print("\nLoading data...")
    try:
        loi_df = load_loi(args.loi)
        co     = load_changeover(args.co)
    except Exception as e:
        print(f"ERROR loading data: {e}")
        sys.exit(1)

    print(f"  LOI rows loaded : {len(loi_df)}")
    print(f"  Mills found     : SM={loi_df[loi_df.mill=='SM'].shape[0]} rows, "
          f"LM={loi_df[loi_df.mill=='LM'].shape[0]} rows")

    # ── Build campaigns ───────────────────────────────────
    camps_sm = build_campaigns(loi_df, 'SM')
    camps_lm = build_campaigns(loi_df, 'LM')

    print(f"  SM campaigns    : {len(camps_sm)}")
    print(f"  LM campaigns    : {len(camps_lm)}")
# ── Load actual rolling plans (optional) ─────────────
    actual_sm = actual_lm = None
    if args.actual_sm:
        try:
            actual_df       = load_actual_plan(args.actual_sm, 'SM')
            actual_sm, miss = build_actual_permutation(actual_df, camps_sm)
            print(f"  SM actual plan  : loaded "
                  f"({miss} campaigns not matched — appended at end)")
        except Exception as e:
            print(f"  SM actual plan  : failed to load — {e}")

    if args.actual_lm:
        try:
            actual_df       = load_actual_plan(args.actual_lm, 'LM')
            actual_lm, miss = build_actual_permutation(actual_df, camps_lm)
            print(f"  LM actual plan  : loaded "
                  f"({miss} campaigns not matched — appended at end)")
        except Exception as e:
            print(f"  LM actual plan  : failed to load — {e}")

    
    # ── Load warm starts ──────────────────────────────────
    warm_sm = load_warm_perm(args.warm_sm)
    warm_lm = load_warm_perm(args.warm_lm)

    # ── Run both mills in parallel ────────────────────────
    print("\nLaunching parallel optimisation for SM and LM mills...")

    mill_configs = [
        ('SM', camps_sm, args.sm_cap, warm_sm, actual_sm),
        ('LM', camps_lm, args.lm_cap, warm_lm, actual_lm),
    ]

    results = {}
    callbacks = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(
                run_mill,
                mill, camps, cap, co,
                args.n_gen, args.pop, args.seed, warm, actual
            ): mill
            for mill, camps, cap, warm, actual in mill_configs
        }

        for future in concurrent.futures.as_completed(futures):
            mill, result, callback = future.result()
            results[mill]   = result
            callbacks[mill] = callback

    # ── Print results ─────────────────────────────────────
    for mill in ['SM', 'LM']:
        print_results(mill, results[mill], callbacks[mill])

    # ── Save warm starts for next cycle ───────────────────
    if args.save:
        print("\nSaving warm starts for next planning cycle...")
        for mill in ['SM', 'LM']:
            if results[mill] is not None:
                save_warm_perm(results[mill], mill, pick_balanced)

    save_results_json(
        mills      = ['SM', 'LM'],
        results    = results,
        callbacks  = callbacks,
        camps_dict = {'SM': camps_sm, 'LM': camps_lm},
        co         = co
    )

    print(f"\nTotal wall time: {time.time() - t_total:.1f}s")
    print("Done.\n")


if __name__ == '__main__':
    main()
