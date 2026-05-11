
import numpy as np
import pandas as pd

# ── Constants ─────────────────────────────────────────────
SHIFT_HRS     = 12.0
STRETCH_MAX   = SHIFT_HRS * 1.3
SEC_COST      = 24100.0
THK_CO_HRS    = 0.5

CONTRIBUTION_PER_HR  = 62_866.0

STRETCH_MAX_HRS = 6.0
FORBIDDEN_SEC_PENALTY = 1_000_000.0
FORBIDDEN_THK_PENALTY = 1_000_000.0

# OBJ_SCALES is computed at runtime by compute_obj_scales() in runner.py
# and passed into evaluate() as a parameter.
# This array is the fallback only if scales are not yet available.
OBJ_SCALES_FALLBACK = np.ones(6, dtype=float)

# ── Changeover lookup helpers ─────────────────────────────
def load_co_from_json(json_path: str, mill: str):
    """
    Load changeover_data.json and return a co dict compatible with
    get_sec_time() and get_thk_cost().
    """
    import json
    with open(json_path, 'r') as f:
        raw = json.load(f)

    # sec_time: flat list → DataFrame (from=rows, to=cols)
    sec_time_rows = {}
    for e in raw['sec_co_time']:
        sec_time_rows.setdefault(e['from'], {})[e['to']] = e['hours']
    sec_time_df = pd.DataFrame(sec_time_rows).T  # rows=from, cols=to

    # sec_cost: flat list → DataFrame
    sec_cost_rows = {}
    for e in raw['sec_co_cost']:
        sec_cost_rows.setdefault(e['from'], {})[e['to']] = e['cost']
    sec_cost_df = pd.DataFrame(sec_cost_rows).T

    # thk_cost: flat list → DataFrame, mill-specific
    thk_key = f'thk_co_cost_{mill.upper()}'
    thk_cost_rows = {}
    for e in raw[thk_key]:
        thk_cost_rows.setdefault(e['from'], {})[e['to']] = e['cost']
    thk_cost_df = pd.DataFrame(thk_cost_rows).T

    return {
        'sec_time':           sec_time_df,
        f'thk_cost_{mill}':   thk_cost_df,
        'sec_cost':           sec_cost_df,
    }

def get_sec_time(co, s1, s2):
    """Hours lost during shift for section changeover s1 → s2."""
    if s1 == s2:
        return 0.0
    try:
        val = co['sec_time'].loc[s1, s2]
        if pd.isna(val):
            pass
        else:
            return float(val)
    except KeyError:
        pass
    # Try reverse direction (symmetric matrix)
    try:
        val = co['sec_time'].loc[s2, s1]
        if pd.isna(val):
            return None
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
        if not np.isnan(val):
            return float(val)
    except KeyError:
        pass
    # Try reverse direction (symmetric matrix)
    try:
        val = co[key].loc[t2, t1]
        if np.isnan(val):
            return None
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



def evaluate(perm, camps, cap, mill, co, scales):
    """
    Evaluate a campaign permutation.

    Parameters
    ----------
    scales : np.array of shape (6,)
        Per-objective scale constants computed at runtime by
        compute_obj_scales() in runner.py. Derived as raw_max / 10
        so all normalised objectives land in [0, ~10].

    Returns np.array of 6 scaled objectives:
        0  Section changeover cost    (Rs)
        1  Thickness changeover cost  (Rs)
        2  Late delivery              (MT·days)
        3  Storage                    (MT·days)
        4  Storage                    (days)
        5  Idle hours
    """
    sec_co_cost     = 0.0
    thk_co_cost     = 0.0
    late_mt_days    = 0.0
    storage_mt_days = 0.0
    storage_days    = 0.0
    idle_hours      = 0.0

    clock    = 0.0
    prev_sec = None
    prev_thk = None
    n        = len(perm)

    for pos in range(n):
        idx = int(perm[pos])
        c   = camps.iloc[idx]

        sec = c['section']
        thk = c['thickness']
        qty = float(c['qty'])
        due = float(c['due'])

        # ── Changeover from previous campaign ────────────
        if prev_sec is not None:
            if prev_sec != sec:
                co_hrs = get_sec_time(co, prev_sec, sec)
                if co_hrs is None:
                    co_hrs = SHIFT_HRS
                    sec_co_cost += FORBIDDEN_SEC_PENALTY

                remaining = SHIFT_HRS - (clock % SHIFT_HRS)
                if co_hrs <= remaining:
                    clock       += co_hrs
                    sec_co_cost += SEC_COST + (co_hrs * CONTRIBUTION_PER_HR)
                else:
                    idle_hours  += remaining
                    clock        = (np.floor(clock / SHIFT_HRS) + 1) * SHIFT_HRS
                    sec_co_cost += SEC_COST

            elif prev_thk != thk:
                thk_c = get_thk_cost(co, prev_thk, thk, mill)
                if thk_c is None:
                    thk_c = FORBIDDEN_THK_PENALTY
                if thk_c > 0:
                    clock       += THK_CO_HRS
                    thk_co_cost += thk_c

        # ── Look ahead to determine next changeover type ──
        next_is_section_co   = False
        next_is_thickness_co = False
        if pos + 1 < n:
            nxt     = camps.iloc[int(perm[pos + 1])]
            nxt_sec = nxt['section']
            nxt_thk = nxt['thickness']
            if nxt_sec != sec:
                next_is_section_co = True
            elif nxt_thk != thk:
                next_is_thickness_co = True

        # ── Rolling ───────────────────────────────────────
        roll_hrs  = (qty / cap) * SHIFT_HRS
        remaining = SHIFT_HRS - (clock % SHIFT_HRS)
        spill     = roll_hrs - remaining

        # ── Stretch decision ──────────────────────────────
        apply_stretch = False
        if 0 < spill <= STRETCH_MAX_HRS:
            if next_is_section_co:
                apply_stretch = True
            elif next_is_thickness_co:
                est_finish = (clock + roll_hrs) / SHIFT_HRS
                if est_finish > due:
                    apply_stretch = True

        if not apply_stretch and spill > 0 and next_is_section_co:
            idle_hours += remaining

        clock     += roll_hrs
        finish_day = clock / SHIFT_HRS

        # ── Late delivery ─────────────────────────────────
        if finish_day > due:
            late_mt_days += qty * (finish_day - due)

        # ── Storage (finished early) ──────────────────────
        elif finish_day < due:
            early_days       = due - finish_day
            storage_mt_days += qty * early_days
            storage_days    += early_days

        prev_sec = sec
        prev_thk = thk

    raw = np.array([
        sec_co_cost,
        thk_co_cost,
        late_mt_days,
        storage_mt_days,
        storage_days,
        idle_hours,
    ], dtype=float)

    return raw / scales