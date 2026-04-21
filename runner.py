import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from problem import RollingPlanProblem
from operators import PermutationSampling, OrderCrossover, SwapMutation


def run_nsga3(camps, cap, mill, co,
              n_gen=300, pop_size=200, seed=42):

    problem = RollingPlanProblem(camps, cap, mill, co)

    # 6 objectives, 3 partitions → 84 reference directions
    ref_dirs = get_reference_directions(
        "das-dennis", 6, n_partitions=3
    )

    # Population must be >= number of reference directions
    pop_size = max(pop_size, len(ref_dirs))
    print(f"[{mill}] Campaigns: {len(camps)} | "
          f"Ref dirs: {len(ref_dirs)} | Pop size: {pop_size}")

    algorithm = NSGA3(
        ref_dirs  = ref_dirs,
        pop_size  = pop_size,
        sampling  = PermutationSampling(),
        crossover = OrderCrossover(),
        mutation  = SwapMutation(),
        eliminate_duplicates = True
    )

    termination = get_termination("n_gen", n_gen)

    result = minimize(
        problem,
        algorithm,
        termination,
        seed         = seed,
        verbose      = True,
        save_history = False
    )

    return result


def pick_best_per_objective(F):
    """
    Returns indices of best solution per objective.
    One index per objective (6 total).
    """
    return [int(np.argmin(F[:, i])) for i in range(F.shape[1])]


def pick_balanced(F):
    """
    TOPSIS-style balanced solution.
    Normalises all objectives to [0,1] then picks
    solution with minimum sum of normalised values.
    """
    mins  = F.min(axis=0)
    maxs  = F.max(axis=0)
    denom = np.where(maxs > mins, maxs - mins, 1.0)
    norm  = (F - mins) / denom
    scores = norm.sum(axis=1)
    return int(np.argmin(scores))