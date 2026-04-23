import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from problem import RollingPlanProblem
from operators import PermutationSampling, OrderCrossover, SwapMutation
from convergence import ConvergenceCallback, MAX_GEN
from seeding import compute_hv_ref_point


def run_nsga3(camps, cap, mill, co,
              n_gen=MAX_GEN, pop_size=252, seed=42,
              last_best_perm=None):
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
    problem = RollingPlanProblem(camps, cap, mill, co)

    # Two-layer reference directions
    # Layer 1 — dense, more reference points overall
    # Layer 2 — sparse, ensures no region is ignored
    ref_dirs = get_reference_directions(
        "multi-layer",
        get_reference_directions("das-dennis", 6, n_partitions=6),
        get_reference_directions("das-dennis", 6, n_partitions=3),
    )

    # Population must be >= number of reference directions
    pop_size = max(pop_size, len(ref_dirs))
    print(f"\n[{mill}] Campaigns: {len(camps)} | "
          f"Ref dirs: {len(ref_dirs)} (two-layer) | Pop size: {pop_size}")
    print(f"[{mill}] Max generations: {n_gen} | "
      f"Convergence window: 100 gens | Tolerance: 0.5%\n")

    # ── Compute HV reference point from NN baseline ───────
    ref_point = compute_hv_ref_point(
        camps   = camps,
        cap     = cap,
        mill    = mill,
        co      = co,
        margin  = 0.15
    )

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
        last_best_perm = last_best_perm
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
    One index per objective (6 total).
    """
    return [int(np.argmin(F[:, i])) for i in range(F.shape[1])]


def pick_balanced(F):
    """
    True TOPSIS balanced solution.
    Picks solution closest to ideal and furthest from nadir.
    """
    mins  = F.min(axis=0)
    maxs  = F.max(axis=0)
    denom = np.where(maxs > mins, maxs - mins, 1.0)
    norm  = (F - mins) / denom

    ideal = np.zeros(F.shape[1])
    nadir = np.ones(F.shape[1])

    dist_to_ideal = np.linalg.norm(norm - ideal, axis=1)
    dist_to_nadir = np.linalg.norm(norm - nadir, axis=1)

    topsis_score  = dist_to_nadir / (dist_to_ideal + dist_to_nadir + 1e-9)
    return int(np.argmax(topsis_score))
