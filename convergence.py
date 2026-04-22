import numpy as np
import time
from pymoo.core.callback import Callback
from pymoo.indicators.hv import HV


# ── Reference point for hypervolume ──────────────────────
# Set to worst acceptable values for each objective:
#   0: sec_co_time     (hrs)
#   1: sec_co_cost     (Rs)
#   2: thk_co_cost     (Rs)
#   3: late_mt_days    (MT·days)
#   4: storage_mt_days (MT·days)
#   5: storage_days    (days)
HV_REF_POINT = np.array([
    50.0,           # 50 hrs shift loss
    5_000_000.0,    # Rs 50L section changeover cost
    5_000_000.0,    # Rs 50L thickness changeover cost
    500_000.0,      # 500k MT·days late
    1_000_000.0,    # 1M MT·days storage
    500.0           # 500 days early storage
], dtype=float)


# ── Convergence parameters ────────────────────────────────
WINDOW          = 50      # generations to look back
HV_TOL          = 0.005   # 0.5% improvement threshold
MAX_GEN         = 2000    # hard safety stop


class ConvergenceCallback(Callback):
    """
    Runs after every generation.
    Records hypervolume, best objectives, diversity.
    Sets algorithm.termination flag when converged.
    """

    def __init__(self, ref_point=HV_REF_POINT, window=WINDOW, hv_tol=HV_TOL):
        super().__init__()
        self.ref_point  = ref_point
        self.window     = window
        self.hv_tol     = hv_tol

        # History lists — one entry per generation
        self.hypervolume    = []
        self.best_per_obj   = []    # list of arrays, shape (n_obj,)
        self.diversity      = []    # unique sequences / pop_size
        self.gen_numbers    = []

        self._hv_calc = HV(ref_point=ref_point)
        self._converged_at = None

    # ── Called by pymoo after each generation ────────────
    def notify(self, algorithm, **kwargs):
        gen = algorithm.n_gen
        F   = algorithm.pop.get("F")

        # ── Hypervolume ───────────────────────────────────
        # Filter out penalty solutions before computing
        feasible = F[np.all(F < 1e8, axis=1)]
        if len(feasible) == 0:
            hv = 0.0
        else:
            # Clip to ref point — HV requires F <= ref_point
            clipped = np.minimum(feasible, self.ref_point)
            try:
                hv = self._hv_calc.do(clipped)
            except Exception:
                hv = 0.0

        # ── Best per objective ────────────────────────────
        best = feasible.min(axis=0) if len(feasible) > 0 else np.full(F.shape[1], np.nan)

        # ── Diversity ─────────────────────────────────────
        X          = algorithm.pop.get("X")
        unique     = len(set(tuple(x) for x in X))
        diversity  = unique / len(X)

        # ── Store ─────────────────────────────────────────
        self.hypervolume.append(hv)
        self.best_per_obj.append(best)
        self.diversity.append(diversity)
        self.gen_numbers.append(gen)

        # ── Print progress every 50 generations ──────────
        if gen % 50 == 0 or gen == 1:
            self._print_status(gen, hv, best, diversity)

        # ── Check convergence ─────────────────────────────
        if self._check_converged(gen):
            self._converged_at = gen
            print(f"\n✓ Converged at generation {gen} "
                  f"(HV change < {self.hv_tol*100:.1f}% "
                  f"over last {self.window} generations)")
            algorithm.termination.force_termination = True

    # ── Convergence check ─────────────────────────────────
    def _check_converged(self, gen):
        if len(self.hypervolume) < self.window + 1:
            return False   # not enough history yet

        recent   = self.hypervolume[-self.window:]
        oldest   = recent[0]
        newest   = recent[-1]

        if oldest == 0.0:
            return False   # avoid divide by zero early on

        improvement = abs(newest - oldest) / oldest
        return improvement < self.hv_tol

    # ── Console output ────────────────────────────────────
    def _print_status(self, gen, hv, best, diversity):
        hv_change = ""
        if len(self.hypervolume) > 1:
            prev = self.hypervolume[-2]
            if prev > 0:
                delta = (hv - prev) / prev * 100
                hv_change = f"  Δ{delta:+.2f}%"

        print(
            f"Gen {gen:>5} | "
            f"HV: {hv:.4f}{hv_change:<12} | "
            f"Diversity: {diversity:.2f} | "
            f"BestCost: {best[1]:>12.0f} | "
            f"BestLate: {best[3]:>10.0f}"
        )

    # ── Summary after run ─────────────────────────────────
    def summary(self):
        print("\n" + "="*60)
        print("CONVERGENCE SUMMARY")
        print("="*60)
        if self._converged_at:
            print(f"  Converged at generation : {self._converged_at}")
        else:
            print(f"  Reached max generations : {self.gen_numbers[-1]}")
        print(f"  Final hypervolume       : {self.hypervolume[-1]:.4f}")
        print(f"  Final diversity         : {self.diversity[-1]:.2f}")
        final_best = self.best_per_obj[-1]
        labels = [
            "Sec CO time (hrs)",
            "Sec CO cost (Rs)",
            "Thk CO cost (Rs)",
            "Late (MT·days)",
            "Storage (MT·days)",
            "Storage (days)"
        ]
        print("\n  Best values on Pareto front:")
        for i, (label, val) in enumerate(zip(labels, final_best)):
            print(f"    {label:<22}: {val:>15.2f}")
        print("="*60)
