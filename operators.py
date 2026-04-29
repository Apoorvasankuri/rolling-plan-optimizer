import numpy as np
from pymoo.core.crossover import Crossover
from pymoo.core.mutation import Mutation
from pymoo.core.sampling import Sampling

from seeding import build_seeded_population

BASE_MUTATION_RATE     = None   # defaults to 1/n_camps
DIVERSITY_THRESHOLD    = 0.20   # below this, boost mutation
MAX_MUTATION_RATE      = 0.15   # ceiling when boosting
STRETCH_MAX            = 4.0    # hours — if rolling time exceeds this, no stretch

class PermutationSampling(Sampling):
    """
    Initialises population with a mix of heuristic seeds
    and random permutations.

    Parameters
    ----------
    camps          : pd.DataFrame  — campaign data
    co             : dict          — changeover matrices
    seed_fraction  : float         — fraction of pop to seed (default 0.20)
    last_best_perm : array or None — warm start from previous cycle
    """

    def __init__(self, camps=None, co=None,
                 seed_fraction=0.20, last_best_perm=None,
                 actual_perm=None):
        super().__init__()
        self.camps          = camps
        self.co             = co
        self.seed_fraction  = seed_fraction
        self.last_best_perm = last_best_perm
        self.actual_perm    = actual_perm

    def _do(self, problem, n_samples, **kwargs):
        # If camps/co provided use seeded init, else fall back to random
        if self.camps is not None and self.co is not None:
            return build_seeded_population(
                n_camps        = problem.n_camps,
                pop_size       = n_samples,
                camps          = self.camps,
                co             = self.co,
                seed_fraction  = self.seed_fraction,
                last_best_perm = self.last_best_perm,
                actual_perm    = self.actual_perm
            )
        else:
            # Pure random fallback
            return np.array([
                np.random.permutation(problem.n_camps)
                for _ in range(n_samples)
            ])


class OrderCrossover(Crossover):
    """
    Order Crossover (OX) for permutation chromosomes.
    Takes a random segment from parent 1, fills remaining
    positions in order from parent 2.
    """

    def __init__(self):
        super().__init__(2, 2)   # 2 parents → 2 children

    def _do(self, problem, X, **kwargs):
        n_matings = X.shape[1]
        n_var     = X.shape[2]
        Y         = np.full_like(X, -1)

        for k in range(n_matings):
            p1 = X[0, k].copy()
            p2 = X[1, k].copy()

            for child_idx, (pa, pb) in enumerate([(p1, p2), (p2, p1)]):
                a, b = sorted(np.random.choice(n_var, 2, replace=False))

                child = np.full(n_var, -1)
                child[a:b+1] = pa[a:b+1]

                segment_set = set(pa[a:b+1])
                remaining   = [v for v in pb if v not in segment_set]
                positions   = [i for i in range(n_var) if child[i] == -1]

                for pos, val in zip(positions, remaining):
                    child[pos] = val

                Y[child_idx, k] = child

        return Y


class SwapMutation(Mutation):
    def __init__(self):
        super().__init__()
        self._current_rate = None   # tracked externally by callback

    def _do(self, problem, X, **kwargs):
        rate = self._current_rate if self._current_rate is not None \
               else 1.0 / problem.n_camps

        for i in range(len(X)):
            # Always do at least one swap
            j, k = np.random.choice(problem.n_camps, 2, replace=False)
            X[i, j], X[i, k] = X[i, k], X[i, j]

            # Then keep swapping with probability `rate` until it fails
            while np.random.random() < rate:
                j, k = np.random.choice(problem.n_camps, 2, replace=False)
                X[i, j], X[i, k] = X[i, k], X[i, j]
        return X
