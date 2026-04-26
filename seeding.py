import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────
# HEURISTIC SEED GENERATORS
# Each function returns a 1-D numpy array — a permutation
# of campaign indices [0 .. n_camps-1]
# ─────────────────────────────────────────────────────────


def seed_nearest_neighbour(camps, co):
    """
    Greedy nearest-neighbour:
    Start from the campaign with the earliest due date.
    At each step pick the unvisited campaign with the
    lowest section changeover time, breaking ties by
    thickness changeover cost, then by due date.
    """
    n        = len(camps)
    visited  = [False] * n
    sequence = []

    # Start from earliest due date
    start = int(camps['due'].idxmin())
    sequence.append(start)
    visited[start] = True

    for _ in range(n - 1):
        current = sequence[-1]
        cur_sec = camps.iloc[current]['section']
        cur_thk = camps.iloc[current]['thickness']
        cur_mill= camps.iloc[current]['mill']

        best_idx  = None
        best_cost = np.inf

        for j in range(n):
            if visited[j]:
                continue

            nxt_sec = camps.iloc[j]['section']
            nxt_thk = camps.iloc[j]['thickness']

            # Section changeover time
            if cur_sec != nxt_sec:
                try:
                    t = co['sec_time'].loc[cur_sec, nxt_sec]
                    sec_t = float(t) if not pd.isna(t) else 999.0
                except KeyError:
                    sec_t = 999.0
            else:
                sec_t = 0.0

            # Thickness changeover cost (tiebreaker)
            if cur_thk != nxt_thk and cur_sec == nxt_sec:
                key = f'thk_cost_{cur_mill}'
                try:
                    c = co[key].loc[cur_thk, nxt_thk]
                    if pd.isna(c):
                        combined = 999e6
                        if combined < best_cost:
                            best_cost = combined
                            best_idx  = j
                        continue
                    thk_c = float(c)
                except KeyError:
                    thk_c = 0.0
            else:
                thk_c = 0.0

            # Combined cost — section time dominates
            combined = sec_t * 1e6 + thk_c

            if combined < best_cost:
                best_cost = combined
                best_idx  = j

        sequence.append(best_idx)
        visited[best_idx] = True

    return np.array(sequence, dtype=int)


def seed_group_by_section(camps):
    """
    Groups all campaigns by section family, then within
    each section sorts by thickness ascending.
    Sections ordered by their earliest due date so urgent
    sections roll first.
    """
    df = camps.copy()
    df['_idx'] = np.arange(len(df))

    # Order sections by their earliest due date
    sec_order = (
        df.groupby('section')['due']
        .min()
        .sort_values()
        .index.tolist()
    )

    sequence = []
    for sec in sec_order:
        block = df[df['section'] == sec].sort_values('thickness')
        sequence.extend(block['_idx'].tolist())

    return np.array(sequence, dtype=int)


def seed_earliest_due(camps):
    """
    Sorts all campaigns by min_due ascending.
    Ties broken by mean_due, then by section name
    to keep same-section campaigns adjacent.
    """
    df = camps.copy()
    df['_idx'] = np.arange(len(df))
    df = df.sort_values(['due', 'section', 'thickness'])
    return np.array(df['_idx'].tolist(), dtype=int)


def seed_warm_start(last_best_perm, n_camps):
    """
    Uses the best permutation from the previous planning
    cycle as a seed.  If the number of campaigns has changed,
    falls back to None so the caller knows to skip it.

    Parameters
    ----------
    last_best_perm : list or np.array or None
        Best permutation from last run. Pass None if not available.
    n_camps : int
        Current number of campaigns.

    Returns
    -------
    np.array or None
    """
    if last_best_perm is None:
        return None
    perm = np.array(last_best_perm, dtype=int)
    if len(perm) != n_camps:
        print(f"[warm start] Campaign count changed "
              f"({len(perm)} → {n_camps}), skipping warm start.")
        return None
    # Validate it is a valid permutation
    if set(perm.tolist()) != set(range(n_camps)):
        print("[warm start] Invalid permutation, skipping.")
        return None
    return perm


# ─────────────────────────────────────────────────────────
# PERTURBATION HELPERS
# Generate slight variants of a seed so multiple similar
# but non-identical seeds can fill the seeded slots
# ─────────────────────────────────────────────────────────

def perturb(perm, n_swaps=3):
    """
    Returns a copy of perm with n_swaps random swaps applied.
    Used to generate variants of the same heuristic seed.
    """
    p = perm.copy()
    n = len(p)
    for _ in range(n_swaps):
        i = np.random.randint(n)
        j = np.random.randint(n)
        while j == i:
            j = np.random.randint(n)
        tmp  = int(p[i])
        p[i] = p[j]
        p[j] = tmp
    return p


# ─────────────────────────────────────────────────────────
# MAIN BUILDER — called from PermutationSampling
# ─────────────────────────────────────────────────────────

def build_seeded_population(n_camps, pop_size, camps, co,
                            seed_fraction=0.20,
                            last_best_perm=None):
    """
    Builds the full initial population of size pop_size.

    seed_fraction of pop_size slots are filled with heuristic
    seeds (and perturbations of them).
    Remaining slots are filled with random permutations.

    Parameters
    ----------
    n_camps       : int
    pop_size      : int
    camps         : pd.DataFrame
    co            : dict  (changeover data)
    seed_fraction : float (default 0.20)
    last_best_perm: list/array or None

    Returns
    -------
    np.ndarray of shape (pop_size, n_camps)
    """
    n_seeds = max(1, int(pop_size * seed_fraction))
    population = []

    # ── Generate base heuristic seeds ────────────────────
    base_seeds = []

    # 1. Nearest neighbour
    try:
        s = seed_nearest_neighbour(camps, co)
        base_seeds.append(('nearest_neighbour', s))
    except Exception as e:
        print(f"[seeding] nearest_neighbour failed: {e}")

    # 2. Group by section
    try:
        s = seed_group_by_section(camps)
        base_seeds.append(('group_by_section', s))
    except Exception as e:
        print(f"[seeding] group_by_section failed: {e}")

    # 3. Earliest due date
    try:
        s = seed_earliest_due(camps)
        base_seeds.append(('earliest_due', s))
    except Exception as e:
        print(f"[seeding] earliest_due failed: {e}")

    # 4. Warm start
    try:
        s = seed_warm_start(last_best_perm, n_camps)
        if s is not None:
            base_seeds.append(('warm_start', s))
    except Exception as e:
        print(f"[seeding] warm_start failed: {e}")

    if base_seeds:
        print(f"[seeding] {len(base_seeds)} heuristic seeds generated: "
              f"{[name for name, _ in base_seeds]}")
        print(f"[seeding] Filling {n_seeds}/{pop_size} slots "
              f"({seed_fraction*100:.0f}%) with seeds + perturbations")
    else:
        print("[seeding] No heuristic seeds available — using random init")

    # ── Fill seeded slots ─────────────────────────────────
    # Add each base seed first, then perturbed variants
    seed_pool = []
    for _, s in base_seeds:
        seed_pool.append(s)

    # Fill remaining seed slots with perturbations
    i = 0
    while len(seed_pool) < n_seeds and base_seeds:
        _, base = base_seeds[i % len(base_seeds)]
        seed_pool.append(perturb(base, n_swaps=max(2, n_camps // 10)))
        i += 1

    population.extend(seed_pool[:n_seeds])

    # ── Fill remaining slots with random permutations ─────
    n_random = pop_size - len(population)
    for _ in range(n_random):
        population.append(np.random.permutation(n_camps))

    pop_array = np.array(population[:pop_size], dtype=int)
    print(f"[seeding] Population built: "
          f"{len(population[:n_seeds])} seeded + {n_random} random "
          f"= {pop_size} total\n")

    return pop_array

def compute_hv_ref_point(camps, cap, mill, co, margin=0.15):
    """
    Runs nearest-neighbour from every possible starting campaign.
    Evaluates each sequence.
    Returns reference point = worst value per objective × (1 + margin).
    Separate for SM and LM since capacity and cost scales differ.
    """
    from evaluator import evaluate

    n      = len(camps)
    all_F  = []

    print(f"[{mill}] Computing HV reference point "
          f"({n} NN runs from all starting points)...")

    for start_idx in range(n):
        # Build NN sequence starting from start_idx
        visited  = [False] * n
        sequence = [start_idx]
        visited[start_idx] = True

        for _ in range(n - 1):
            current  = sequence[-1]
            cur_sec  = camps.iloc[current]['section']
            cur_thk  = camps.iloc[current]['thickness']
            cur_mill = camps.iloc[current]['mill']

            best_idx  = None
            best_cost = np.inf

            for j in range(n):
                if visited[j]:
                    continue
                nxt_sec = camps.iloc[j]['section']
                nxt_thk = camps.iloc[j]['thickness']

                if cur_sec != nxt_sec:
                    try:
                        t     = co['sec_time'].loc[cur_sec, nxt_sec]
                        sec_t = float(t) if not pd.isna(t) else 999.0
                    except KeyError:
                        sec_t = 999.0
                else:
                    sec_t = 0.0

                if cur_thk != nxt_thk and cur_sec == nxt_sec:
                    key = f'thk_cost_{cur_mill}'
                    try:
                        c     = co[key].loc[cur_thk, nxt_thk]
                        thk_c = float(c) if not pd.isna(c) else 0.0
                    except KeyError:
                        thk_c = 0.0
                else:
                    thk_c = 0.0

                combined = sec_t * 1e6 + thk_c
                if combined < best_cost:
                    best_cost = combined
                    best_idx  = j

            sequence.append(best_idx)
            visited[best_idx] = True

        # Evaluate this sequence
        perm = np.array(sequence, dtype=int)
        F    = evaluate(perm, camps, cap, mill, co)
        if np.all(F < 1e8):
            all_F.append(F)

    # ── Random sequences — capture objectives NN ignores ──
    rng = np.random.default_rng(seed=0)
    for _ in range(50):
        perm = rng.permutation(n)
        F    = evaluate(perm, camps, cap, mill, co)
        if np.all(F < 1e8):
            all_F.append(F)

    if len(all_F) == 0:
        print(f"[{mill}] WARNING: all sequences infeasible, "
              f"using fallback ref point [2.0 x 6]")
        return np.ones(6) * 2.0

    all_F     = np.array(all_F)
    worst     = all_F.max(axis=0)
    ref_point = worst * (1.0 + margin)

    print(f"[{mill}] Reference point from "
          f"{len(all_F)} sequences ({n} NN + 50 random):")
    labels = [
        "Sec CO time (norm)", "Sec CO cost (norm)",
        "Thk CO cost (norm)", "Late (norm)",
        "Storage MT (norm)",  "Storage days (norm)"
    ]
    for i, (label, val) in enumerate(zip(labels, ref_point)):
        print(f"       {label:<22}: {val:.4f}")

    return ref_point

def compute_hv_ref_point_from_actual(actual_perm, camps, cap, mill, co,
                                      margin=0.15):
    """
    Evaluates the actual historical rolling plan permutation.
    Uses its objective values as the HV reference point.

    Forbidden transitions in the actual plan are treated as
    high-cost (not 1e9 penalty) so the plan can still serve
    as a meaningful baseline.

    Returns ref_point = actual_F * (1 + margin)
    """
    from evaluator import (SHIFT_HRS, THK_CO_HRS, SEC_COST,
                           get_sec_time, get_thk_cost,
                           compute_changeover_clock, advance_clock,
                           NORM_SEC_CO_TIME, NORM_SEC_CO_COST,
                           NORM_THK_CO_COST, NORM_LATE_MT_DAYS,
                           NORM_STORAGE_MT_DAYS, NORM_STORAGE_DAYS)

    denoms = np.array([
        NORM_SEC_CO_TIME, NORM_SEC_CO_COST, NORM_THK_CO_COST,
        NORM_LATE_MT_DAYS, NORM_STORAGE_MT_DAYS, NORM_STORAGE_DAYS
    ])

    sec_co_time = sec_co_cost = thk_co_cost = 0.0
    late_mt_days = storage_mt_days = storage_days = 0.0
    clock = 0.0
    prev_sec = prev_thk = None
    n_forbidden = 0

    for pos in range(len(actual_perm)):
        idx = int(actual_perm[pos])
        c   = camps.iloc[idx]
        sec = c['section']; thk = c['thickness']
        qty = float(c['qty']); due = float(c['due'])

        if prev_sec is not None:
            if prev_sec != sec:
                co_hrs = get_sec_time(co, prev_sec, sec)
                if co_hrs is None:
                    co_hrs = SHIFT_HRS
                    n_forbidden += 1
                new_clock, hrs_lost = compute_changeover_clock(clock, co_hrs)
                clock        = new_clock
                sec_co_time += hrs_lost
                try:
                    sec_co_cost += SEC_COST
                except Exception:
                    sec_co_cost += SHIFT_HRS * SEC_COST
            elif prev_thk != thk:
                thk_c = get_thk_cost(co, prev_thk, thk, mill)
                if thk_c is None:
                    thk_c = float(denoms[2]) * 0.8
                    n_forbidden += 1
                if thk_c > 0:
                    new_clock, _ = compute_changeover_clock(clock, THK_CO_HRS)
                    clock        = new_clock
                    thk_co_cost += thk_c

        roll_hrs          = (qty / cap) * SHIFT_HRS
        new_clock, _      = advance_clock(clock, roll_hrs)
        clock             = new_clock
        finish_day        = clock / SHIFT_HRS

        if finish_day > due:
            late_mt_days    += qty * (finish_day - due)
        elif finish_day < due:
            early_days       = due - finish_day
            storage_mt_days += qty * early_days
            storage_days    += early_days

        prev_sec = sec; prev_thk = thk

    raw = np.array([sec_co_time, sec_co_cost, thk_co_cost,
                    late_mt_days, storage_mt_days, storage_days])
    actual_F  = raw / denoms
    ref_point = actual_F * (1.0 + margin)

    labels = [
        "Sec CO time (norm)", "Sec CO cost (norm)",
        "Thk CO cost (norm)", "Late (norm)",
        "Storage MT (norm)",  "Storage days (norm)"
    ]
    note = f" ({n_forbidden} forbidden transitions treated as high-cost)" \
           if n_forbidden else ""
    print(f"[{mill}] HV ref point from actual rolling plan{note}:")
    for i, (label, val) in enumerate(zip(labels, ref_point)):
        print(f"       {label:<22}: {val:.4f}  (actual={actual_F[i]:.4f})")

    return ref_point