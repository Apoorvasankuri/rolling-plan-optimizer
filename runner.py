import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from multiprocessing.pool import ThreadPool
from pymoo.parallelization.starmap import StarmapParallelization

from problem import RollingPlanProblem
from operators import PermutationSampling, OrderCrossover, SwapMutation
from convergence import ConvergenceCallback, MAX_GEN
from seeding import compute_hv_ref_point

def compute_obj_scales(camps, cap, mill, co, n_samples=1000, seed=0):
    """
    Derives per-objective scale constants from actual data.
    Runs n_samples random permutations, returns raw_max / 10
    so all normalised objectives land in [0, ~10].
    """
    from evaluator import evaluate

    rng         = np.random.default_rng(seed)
    n           = len(camps)
    all_F       = []
    unit_scales = np.ones(6, dtype=float)

    for _ in range(n_samples):
        perm = rng.permutation(n)
        F    = evaluate(perm, camps, cap, mill, co, unit_scales)
        if np.all(np.isfinite(F)) and np.all(F < 1e8):
            all_F.append(F)

    if len(all_F) == 0:
        print(f"[{mill}] WARNING: no finite solutions during scale "
              f"computation — using unit scales")
        return unit_scales

    all_F   = np.array(all_F)
    raw_max = all_F.max(axis=0)
    raw_max = np.where(raw_max < 1e-9, 1.0, raw_max)
    scales  = raw_max / 10.0

    labels = ["sec_co_cost", "thk_co_cost", "late_mt_days",
              "storage_mt", "storage_days", "idle_hours"]
    print(f"\n[{mill}] Objective scales from {len(all_F)} random permutations:")
    print(f"  {'Objective':<16} {'raw_max':>12}  {'scale':>12}")
    print(f"  {'-'*44}")
    for i, lbl in enumerate(labels):
        print(f"  {lbl:<16} {raw_max[i]:>12.2f}  {scales[i]:>12.2f}")

    return scales

def run_nsga3(camps, cap, mill, co,
              n_gen=MAX_GEN, pop_size=252, seed=42,
              last_best_perm=None, actual_perm=None):
    """
    Parameters
    ----------
    camps          : pd.DataFrame  — campaign data
    cap            : float         — mill capacity (MT/shift)
    mill           : str           — 'SM' or 'LM'
    co             : dict          — changeover matrices
    n_gen          : int           — max generations (safety stop)
    pop_size       : int           — minimum population size
    seed           : int           — random seed for reproducibility
    last_best_perm : array or None — best perm from previous cycle
                                     (enables warm start seeding)
    """
    pool    = ThreadPool(8)
    runner  = StarmapParallelization(pool.starmap)

    # ── Compute objective scales from data ────────────────
    scales  = compute_obj_scales(camps, cap, mill, co, n_samples=1000, seed=seed)

    problem = RollingPlanProblem(camps, cap, mill, co, scales, elementwise_runner=runner)

    # Two-layer reference directions
    # Layer 1 — dense, more reference points overall
    # Layer 2 — sparse, ensures no region is ignored
    ref_dirs = get_reference_directions(
        "multi-layer",
        get_reference_directions("das-dennis", 6, n_partitions=5),
        get_reference_directions("das-dennis", 6, n_partitions=1),
    )

    # Population must be >= number of reference directions
    pop_size = max(pop_size, len(ref_dirs))
    print(f"\n[{mill}] Campaigns: {len(camps)} | "
          f"Ref dirs: {len(ref_dirs)} (two-layer) | Pop size: {pop_size}")
    print(f"[{mill}] Max generations: {n_gen} | "
      f"Convergence window: 100 gens | Tolerance: 0.5%\n")

    # ── Compute HV reference point ────────────────────────
    # Always compute NN+random baseline (covers full objective range)
    # If actual plan provided, take per-objective maximum of both
    nn_ref = compute_hv_ref_point(
        camps  = camps,
        cap    = cap,
        mill   = mill,
        co     = co,
        scales = scales,
        margin = 0.15
    )

    if actual_perm is not None:
        from seeding import compute_hv_ref_point_from_actual
        actual_ref = compute_hv_ref_point_from_actual(
            actual_perm = actual_perm,
            camps       = camps,
            cap         = cap,
            mill        = mill,
            co          = co,
            scales      = scales,
            margin      = 0.15
        )
        ref_point = np.maximum(nn_ref, actual_ref)
        print(f"[{mill}] Final ref point (max of NN and actual plan):")
        labels = ["sec_co_cost", "thk_co_cost",
                  "late", "storage_mt", "storage_days", "idle_hrs"]
        for l, v in zip(labels, ref_point):
            print(f"       {l:<20}: {v:.4f}")
    else:
        ref_point = nn_ref

    callback = ConvergenceCallback(
        ref_point = ref_point,
        window    = 150,
        hv_tol    = 0.005,
        scales    = scales
    )

    sampling = PermutationSampling(
        camps          = camps,
        co             = co,
        scales         = scales,
        seed_fraction  = 0.25,
        last_best_perm = last_best_perm,
        actual_perm    = actual_perm
    )

    algorithm = NSGA3(
        ref_dirs             = ref_dirs,
        pop_size             = pop_size,
        sampling             = sampling,
        crossover            = OrderCrossover(),
        mutation             = SwapMutation(),
        eliminate_duplicates = True
    )

    # Safety stop at MAX_GEN — callback stops earlier if converged
    termination = get_termination("n_gen", n_gen)

    result = minimize(
        problem,
        algorithm,
        termination,
        seed         = seed,
        verbose      = False,
        save_history = False,
        callback     = callback
    )

    # Print convergence summary
    callback.summary()

    return result, callback, scales


def pick_best_per_objective(F):
    """
    Returns indices of best solution per objective.
    One index per objective (5 total).
    """
    return [int(np.argmin(F[:, i])) for i in range(F.shape[1])]


def pick_balanced(F):
    """
    Weighted TOPSIS balanced solution.

    Objective indices:
        0: Section changeover cost
        1: Thickness changeover cost
        2: Late delivery (MT·days)   ← highest priority
        3: Storage MT·days
        4: Storage days
        5: Idle hours
    """
    weights = np.array([
        0.15,   # sec co cost
        0.10,   # thk co cost
        0.35,   # late delivery  ← dominant
        0.15,   # storage MT
        0.10,   # storage days
        0.15,   # idle hours
    ])

    mins  = F.min(axis=0)
    maxs  = F.max(axis=0)
    denom = np.where(maxs > mins, maxs - mins, 1.0)
    norm  = (F - mins) / denom

    weighted      = norm * weights
    ideal         = np.zeros(F.shape[1])
    nadir         = weights
    dist_to_ideal = np.linalg.norm(weighted - ideal, axis=1)
    dist_to_nadir = np.linalg.norm(weighted - nadir, axis=1)
    topsis_score  = dist_to_nadir / (dist_to_ideal + dist_to_nadir + 1e-9)

    return int(np.argmax(topsis_score))