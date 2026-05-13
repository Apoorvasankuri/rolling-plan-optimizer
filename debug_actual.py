import numpy as np
from data_loader import (load_loi, load_changeover, build_campaigns,
                         load_actual_plan, build_actual_permutation)
from evaluator import (evaluate, get_sec_time, get_thk_cost,
                        SHIFT_HRS, SEC_COST, CONTRIBUTION_PER_HR, THK_CO_HRS)

# Load data
loi_df = load_loi('LOI_Jan_2026.xlsx')
co     = load_changeover('changeover_data.json')

# Build campaigns for SM
camps = build_campaigns(loi_df, 'SM')
print(f"SM campaigns: {len(camps)}")

# Load actual plan and build permutation
actual_df       = load_actual_plan('Rolling_Plan_FY26_SM.xlsx', 'SM')
actual_perm, miss = build_actual_permutation(actual_df, camps)
print(f"Actual perm length: {len(actual_perm)}, unmatched: {miss}")

# Walk through the actual sequence and print every changeover
clock    = 0.0
prev_sec = None
prev_thk = None
total_sec_co_cost = 0.0

print(f"\n{'#':<4} {'Section':<10} {'Thk':<5} {'Qty':>7} {'Due':>4}  "
      f"{'CO Type':<10} {'CO Hrs':>7} {'Remaining':>10} {'Fits?':<6} "
      f"{'CO Cost':>12} {'Running Total':>14}")
print("-" * 105)

for pos, idx in enumerate(actual_perm):
    c   = camps.iloc[int(idx)]
    sec = c['section']
    thk = c['thickness']
    qty = float(c['qty'])
    due = float(c['due'])

    co_type = ''
    co_hrs  = 0.0
    co_cost = 0.0
    fits    = ''

    if prev_sec is not None and prev_sec != sec:
        co_type = 'SECTION'
        co_hrs  = get_sec_time(co, prev_sec, sec)
        if co_hrs is None:
            co_hrs = SHIFT_HRS
            co_type = 'SEC(FORBID)'

        remaining = SHIFT_HRS - (clock % SHIFT_HRS)
        if co_hrs <= remaining:
            fits = 'YES'
            co_cost = SEC_COST + (co_hrs * CONTRIBUTION_PER_HR)
            clock += co_hrs
        else:
            fits = 'NO'
            co_cost = SEC_COST
            clock = (np.floor(clock / SHIFT_HRS) + 1) * SHIFT_HRS

        total_sec_co_cost += co_cost

    elif prev_sec is not None and prev_sec == sec and prev_thk != thk:
        co_type = 'THICKNESS'

    print(f"{pos+1:<4} {sec:<10} {thk:<5} {qty:>7.1f} {due:>4}  "
          f"{co_type:<10} {co_hrs:>7.1f} "
          f"{(SHIFT_HRS - (clock % SHIFT_HRS)):>10.2f} {fits:<6} "
          f"{co_cost:>12,.0f} {total_sec_co_cost:>14,.0f}")

    # Advance clock for rolling
    roll_hrs  = (qty / 150.0) * SHIFT_HRS
    shift_pos = clock % SHIFT_HRS
    remaining = SHIFT_HRS - shift_pos
    if roll_hrs <= remaining:
        clock += roll_hrs
    else:
        carried = roll_hrs - remaining
        clock = (np.floor(clock / SHIFT_HRS) + 1) * SHIFT_HRS + carried

    prev_sec = sec
    prev_thk = thk

print(f"\nTotal Section CO Cost: {total_sec_co_cost:,.0f} Rs")