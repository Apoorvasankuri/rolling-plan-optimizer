import numpy as np
from pymoo.core.problem import Problem
from evaluator import evaluate


class RollingPlanProblem(Problem):

    def __init__(self, camps, cap, mill, co, scales):
        self.camps   = camps
        self.cap     = cap
        self.mill    = mill
        self.co      = co
        self.scales  = scales
        self.n_camps = len(camps)

        super().__init__(
            n_var        = self.n_camps,
            n_obj        = 6,
            n_ieq_constr = 0,
            xl           = 0,
            xu           = self.n_camps - 1,
            vtype        = int,
        )

    def _evaluate(self, X, out, *args, **kwargs):
        F = np.empty((len(X), self.n_obj), dtype=float)
        for i, x in enumerate(X):
            F[i] = evaluate(x, self.camps, self.cap, self.mill, self.co, self.scales)
        out["F"] = F