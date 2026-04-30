import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from multiprocessing.pool import ThreadPool
from pymoo.core.parallel import StarmapParallelization

from problem import RollingPlanProblem
from operators import PermutationSampling, OrderCrossover, SwapMutation
from convergence import ConvergenceCallback, MAX_GEN
from seeding import compute_hv_ref_point


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
    problem = RollingPlanProblem(camps, cap, mill, co, elementwise_runner=runner)

    # Two-layer reference directions
    # Layer 1 — dense, more reference points overall
    # Layer 2 — sparse, ensures no region is ignored
    ref_dirs = get_reference_directions(
        "multi-layer",
        get_reference_directions("das-dennis", 5, n_partitions=6),
        get_reference_directions("das-dennis", 5, n_partitions=3),
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
            margin      = 0.15
        )
        ref_point = np.maximum(nn_ref, actual_ref)
        print(f"[{mill}] Final ref point (max of NN and actual plan):")
        labels = ["sec_co_cost", "thk_co_cost",
                  "late", "storage_mt", "storage_days"]
        for l, v in zip(labels, ref_point):
            print(f"       {l:<20}: {v:.4f}")
    else:
        ref_point = nn_ref

    # ── Convergence callback ──────────────────────────────
    callback = ConvergenceCallback(
        ref_point = ref_point,
        window    = 100,
        hv_tol    = 0.005
    )

    # ── Seeded sampling ───────────────────────────────────
    sampling = PermutationSampling(
        camps          = camps,
        co             = co,
        seed_fraction  = 0.20,
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

    return result, callback


def pick_best_per_objective(F):
    """
    Returns indices of best solution per objective.
    One index per objective (5 total).
    """
    return [int(np.argmin(F[:, i])) for i in range(F.shape[1])]


def pick_balanced(F):
    """
    Weighted TOPSIS balanced solution.
    Weights reflect priority: Late > Sec CO Time > Sec CO Cost > Thk CO Cost > Storage.

    Objective indices:
        0: Sec CO time
        1: Sec CO cost
        2: Thk CO cost
        3: Late (MT·days)      ← highest priority
        4: Storage (MT·days)
        5: Storage (days)
    """
    weights = np.array([0.20, 0.15, 0.40, 0.15, 0.10])
    # weights sum to 1.0 — late delivery gets 40%, sec CO cost 20%

    mins  = F.min(axis=0)
    maxs  = F.max(axis=0)
    denom = np.where(maxs > mins, maxs - mins, 1.0)
    norm  = (F - mins) / denom          # shape (n_solutions, 5), range [0,1]

    weighted = norm * weights           # scale each objective by its priority

    ideal = np.zeros(F.shape[1])        # best possible = 0 in every objective
    nadir = weights                     # worst in weighted space = weights vector

    dist_to_ideal = np.linalg.norm(weighted - ideal, axis=1)
    dist_to_nadir = np.linalg.norm(weighted - nadir, axis=1)

    topsis_score  = dist_to_nadir / (dist_to_ideal + dist_to_nadir + 1e-9)
    return int(np.argmax(topsis_score))