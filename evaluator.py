
import numpy as np
import pandas as pd

# ── Constants ─────────────────────────────────────────────
SHIFT_HRS     = 12.0
STRETCH_MAX   = SHIFT_HRS * 1.3
SEC_COST      = 24100.0
THK_CO_HRS    = 0.5

# ── Normalisation denominators ────────────────────────────
# Set to expected worst-case value for each objective
# Objectives will be returned in range [0, ~1]
CONTRIBUTION_PER_HR  = 62_866.0
NORM_SEC_CO_COST     = 10_000_000.0
NORM_THK_CO_COST     = 3_000_000.0
NORM_LATE_MT_DAYS    = 60_000.0
NORM_STORAGE_MT_DAYS = 5_000.0
NORM_STORAGE_DAYS    = 250.0

# ── Changeover lookup helpers ─────────────────────────────

def get_sec_time(co, s1, s2):
    """Hours lost during shift for section changeover s1 → s2."""
    if s1 == s2:
        return 0.0
    try:
        val = co['sec_time'].loc[s1, s2]
        if pd.isna(val):
            return None   # impossible changeover
        return float(val)
    except KeyError:
        return None


def get_thk_cost(co, t1, t2, mill):
    """Cost in Rs for thickness changeover t1 → t2 on given mill.
    Returns None if combination is forbidden (NaN in matrix).
    Returns 0.0 if same thickness.
    """
    if t1 == t2:
        return 0.0
    key = f'thk_cost_{mill}'
    try:
        val = co[key].loc[t1, t2]
        if np.isnan(val):
            return None   # forbidden combination
        return float(val)
    except KeyError:
        return None


# ── Shift timing helper ───────────────────────────────────

def advance_clock(clock, hours_needed):
    shift_position = clock % SHIFT_HRS
    remaining      = SHIFT_HRS - shift_position

    if hours_needed <= remaining:
        # Fits in current shift
        return clock + hours_needed, 0.0
    else:
        # Spills into next day — continue from start of next shift
        hours_carried = hours_needed - remaining
        new_clock     = (np.floor(clock / SHIFT_HRS) + 1) * SHIFT_HRS + hours_carried
        return new_clock, 0.0

def compute_changeover_clock(clock, co_hrs):
    shift_position = clock % SHIFT_HRS
    remaining      = SHIFT_HRS - shift_position

    if co_hrs <= remaining:
        # Fits in current shift — productive hours lost
        hrs_lost  = co_hrs
        new_clock = clock + co_hrs
    else:
        # Doesn't fit — done post-shift, 0 hours lost
        hrs_lost  = 0.0
        new_clock = (np.floor(clock / SHIFT_HRS) + 1) * SHIFT_HRS

    return new_clock, hrs_lost


# ── Main evaluation function ──────────────────────────────



def evaluate(perm, camps, cap, mill, co):
    """
    Evaluates a permutation of campaigns and returns 5 objective values.

    Objectives:
        0: Section changeover cost (Rs) — fixed cost + opportunity cost of hrs lost
        1: Thickness changeover cost (Rs)
        2: Late delivery (MT x days late)
        3: Inventory storage (MT x days finished before bucket)
        4: Inventory storage days (sum of days early, unweighted)

    Returns np.array of 5 floats.
    Returns a very large penalty array if the permutation is infeasible
    (forbidden thickness changeover encountered).
    """
    sec_co_cost     = 0.0
    thk_co_cost     = 0.0
    late_mt_days    = 0.0
    storage_mt_days = 0.0
    storage_days    = 0.0

    clock    = 0.0   # hours elapsed since day 1 shift start
    prev_sec = None
    prev_thk = None

    PENALTY = np.array([1e9, 1e9, 1e9, 1e9, 1e9], dtype=float)

    for pos in range(len(perm)):
        idx = int(perm[pos])
        c   = camps.iloc[idx]

        sec = c['section']
        thk = c['thickness']
        qty = float(c['qty'])
        due = float(c['due'])       # single due date per campaign

        # ── Changeover from previous campaign ────────────
        if prev_sec is not None:

            if prev_sec != sec:
                # Section changeover
                co_hrs = get_sec_time(co, prev_sec, sec)
                if co_hrs is None:
                    return PENALTY   # impossible — penalise
                new_clock, hrs_lost = compute_changeover_clock(clock, co_hrs)
                clock        = new_clock
                sec_co_cost += SEC_COST + (hrs_lost * CONTRIBUTION_PER_HR)

            elif prev_thk != thk:
                thk_c = get_thk_cost(co, prev_thk, thk, mill)
                if thk_c is None:
                    return PENALTY
                if thk_c > 0:
                    clock       += THK_CO_HRS   # just burns 0.5 hrs in place, no shift jump
                    thk_co_cost += thk_c

        # ── Rolling time for this campaign ────────────────
        roll_hrs  = (qty / cap) * SHIFT_HRS
        new_clock, _ = advance_clock(clock, roll_hrs)
        clock         = new_clock

        finish_day = clock / SHIFT_HRS

        # ── Late delivery ─────────────────────────────────
        if finish_day > due:
            late_mt_days += qty * (finish_day - due)

        # ── Storage (finished early) ──────────────────────
        if finish_day < due:
            early_days       = due - finish_day
            storage_mt_days += qty * early_days
            storage_days    += early_days

        prev_sec = sec
        prev_thk = thk

    return np.array([
    sec_co_cost     / NORM_SEC_CO_COST,
    thk_co_cost     / NORM_THK_CO_COST,
    late_mt_days    / NORM_LATE_MT_DAYS,
    storage_mt_days / NORM_STORAGE_MT_DAYS,
    storage_days    / NORM_STORAGE_DAYS
], dtype=float)