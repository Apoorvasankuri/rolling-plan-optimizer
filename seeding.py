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
    start = int(camps['mean_due'].idxmin())
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
                    thk_c = float(c) if not pd.isna(c) else 0.0
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
        df.groupby('section')['min_due']
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
    df = df.sort_values(['min_due', 'mean_due', 'section', 'thickness'])
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
