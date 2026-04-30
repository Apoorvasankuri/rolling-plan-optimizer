import numpy as np
from pymoo.core.problem import ElementwiseProblem
from evaluator import evaluate


class RollingPlanProblem(ElementwiseProblem):

    def __init__(self, camps, cap, mill, co, elementwise_runner=None):
        self.camps = camps
        self.cap   = cap
        self.mill  = mill
        self.co    = co
        self.n_camps = len(camps)

        runner_kwargs = {"elementwise_runner": elementwise_runner} \
                        if elementwise_runner is not None else {}

        super().__init__(
            n_var        = self.n_camps,
            n_obj        = 5,
            n_ieq_constr = 0,
            xl           = 0,
            xu           = self.n_camps - 1,
            vtype        = int,
            **runner_kwargs
        )

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"] = evaluate(
            x,
            self.camps,
            self.cap,
            self.mill,
            self.co
        )