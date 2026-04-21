import numpy as np
from pymoo.core.crossover import Crossover
from pymoo.core.mutation import Mutation
from pymoo.core.sampling import Sampling


class PermutationSampling(Sampling):
    """Initialises population with random permutations."""

    def _do(self, problem, n_samples, **kwargs):
        X = np.array([
            np.random.permutation(problem.n_camps)
            for _ in range(n_samples)
        ])
        return X


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
                # Pick random crossover segment
                a, b = sorted(np.random.choice(n_var, 2, replace=False))

                child = np.full(n_var, -1)
                child[a:b+1] = pa[a:b+1]

                # Fill remaining from pb in order
                segment_set = set(pa[a:b+1])
                remaining   = [v for v in pb if v not in segment_set]
                positions   = [i for i in range(n_var) if child[i] == -1]

                for pos, val in zip(positions, remaining):
                    child[pos] = val

                Y[child_idx, k] = child

        return Y


class SwapMutation(Mutation):
    """
    Swap mutation for permutation chromosomes.
    Each position has probability 1/n_camps of being
    swapped with a random other position.
    """

    def __init__(self):
        super().__init__()

    def _do(self, problem, X, **kwargs):
        rate = 1.0 / problem.n_camps

        for i in range(len(X)):
            for j in range(problem.n_camps):
                if np.random.random() < rate:
                    k         = np.random.randint(problem.n_camps)
                    X[i, j], X[i, k] = X[i, k], X[i, j]

        return X