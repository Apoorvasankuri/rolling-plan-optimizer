import numpy as np
import time
from pymoo.core.callback import Callback
from pymoo.indicators.hv import HV

# ── Adaptive mutation constants ───────────────────────────
DIVERSITY_THRESHOLD = 0.20
MAX_MUTATION_RATE   = 0.15

# ── Convergence parameters ────────────────────────────────
WINDOW          = 100     # generations to look back
HV_TOL          = 0.005   # 0.5% improvement threshold
GD_TOL          = 0.01    # generational distance threshold
MAX_GEN         = 2000    # hard safety stop only — no fixed gen count


class ConvergenceCallback(Callback):
    """
    Runs after every generation.
    Records hypervolume, best objectives, diversity.
    Sets algorithm.termination flag when converged.
    """

    # FIX 1: corrected __init__ indentation — all assignments now inside method
    def __init__(self, ref_point=None, window=WINDOW, hv_tol=HV_TOL):
        super().__init__()
        if ref_point is None:
            raise ValueError(
                "ref_point must be provided — "
                "compute via compute_hv_ref_point() in seeding.py"
            )
        self.ref_point = ref_point
        self.window    = window
        self.hv_tol    = hv_tol

        # History lists — one entry per generation
        self.hypervolume   = []
        self.best_per_obj  = []
        self.diversity     = []
        self.gen_dist      = []   # generational distance per generation
        self.gen_numbers   = []

        self._hv_calc      = HV(ref_point=ref_point)
        self._converged_at = None

    # ── Called by pymoo after each generation ────────────
    def notify(self, algorithm, **kwargs):
        gen = algorithm.n_gen
        F   = algorithm.pop.get("F")

        # ── Hypervolume ───────────────────────────────────
        # FIX 5: exclude solutions outside ref point instead of clipping
        feasible = F[np.all(F < 1e8, axis=1)]
        if len(feasible) == 0:
            hv = 0.0
        else:
            valid = feasible[np.all(feasible < self.ref_point, axis=1)]
            if len(valid) == 0:
                hv = 0.0
            else:
                try:
                    hv = self._hv_calc.do(valid)
                except Exception:
                    hv = 0.0

        # ── Best per objective ────────────────────────────
        best = feasible.min(axis=0) if len(feasible) > 0 else np.full(F.shape[1], np.nan)

        # ── Generational distance ─────────────────────────
        if len(self.best_per_obj) > 0:
            prev_best = self.best_per_obj[-1]
            if not np.any(np.isnan(prev_best)) and not np.any(np.isnan(best)):
                gd = float(np.linalg.norm(best - prev_best))
            else:
                gd = 1.0
        else:
            gd = 1.0   # no history yet
        self.gen_dist.append(gd)

        # ── Diversity ─────────────────────────────────────
        X         = algorithm.pop.get("X")
        unique    = len(set(tuple(x) for x in X))
        diversity = unique / len(X)

        # ── Adaptive mutation ─────────────────────────────
        n_camps   = algorithm.problem.n_camps
        base_rate = 1.0 / n_camps
        if diversity < DIVERSITY_THRESHOLD:
            boost    = (DIVERSITY_THRESHOLD - diversity) / DIVERSITY_THRESHOLD
            new_rate = base_rate + boost * (MAX_MUTATION_RATE - base_rate)
        else:
            new_rate = base_rate

        # Push rate into mutation operator
        algorithm.mating.mutation._current_rate = new_rate

        # ── Store ─────────────────────────────────────────
        self.hypervolume.append(hv)
        self.best_per_obj.append(best)
        self.diversity.append(diversity)
        self.gen_numbers.append(gen)

        # ── Print progress every 50 generations ──────────
        if gen % 50 == 0 or gen == 1:
            self._print_status(gen, hv, best, diversity, mut_rate=new_rate)

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

        # ── Condition 1: Hypervolume plateau ─────────────
        recent  = self.hypervolume[-self.window:]
        oldest  = recent[0]
        newest  = recent[-1]
        if oldest == 0.0:
            return False
        hv_improvement = abs(newest - oldest) / oldest
        cond_hv = hv_improvement < self.hv_tol

        # ── Condition 2: Best objectives unchanged ────────
        recent_best = self.best_per_obj[-self.window:]
        first_best  = recent_best[0]
        last_best   = recent_best[-1]

        # FIX 3: define obj_change in both branches to avoid NameError
        if np.any(np.isnan(first_best)) or np.any(np.isnan(last_best)):
            cond_obj   = False
            obj_change = float('nan')
        else:
            obj_change = np.max(np.abs(last_best - first_best))
            cond_obj   = obj_change < self.hv_tol

        # ── Condition 3: Generational distance near zero ──
        recent_gd = self.gen_dist[-self.window:]
        cond_gd   = float(np.mean(recent_gd)) < GD_TOL

        # ── All three must be true ────────────────────────
        converged = cond_hv and cond_obj and cond_gd

        if gen % 50 == 0:
            print(f"         Convergence check → "
                  f"HV:{cond_hv} "
                  f"OBJ:{cond_obj} "
                  f"GD:{cond_gd} "
                  f"(hv_Δ={hv_improvement:.4f} "
                  f"obj_Δ={obj_change:.4f} "
                  f"gd={np.mean(recent_gd):.4f})")

        return converged

    # ── Console output ────────────────────────────────────
    # FIX 2: corrected _print_status indentation — all body lines at 4 spaces
    def _print_status(self, gen, hv, best, diversity, mut_rate=None):
        hv_change = ""
        if len(self.hypervolume) > 1:
            prev = self.hypervolume[-2]
            if prev > 0:
                delta     = (hv - prev) / prev * 100
                hv_change = f"  Δ{delta:+.2f}%"

        mut_str = f"{mut_rate:.4f}" if mut_rate is not None else "default"
        print(
            f"Gen {gen:>5} | "
            f"HV: {hv:.4f}{hv_change:<12} | "
            f"Diversity: {diversity:.2f} | "
            f"MutRate: {mut_str} | "
            f"BestCost: {best[0] * 10_000_000:>12.0f} | "
            f"BestLate: {best[2] * 60_000:>10.0f}"
        )

    # ── Summary after run ─────────────────────────────────
    def summary(self):
        print("\n" + "="*60)
        print("CONVERGENCE SUMMARY")
        print("="*60)
        if self._converged_at:
            print(f"  Converged at generation : {self._converged_at}")
            print(f"  (all 3 conditions met — HV plateau, "
                  f"objective stability, GD < {GD_TOL})")
        else:
            print(f"  Hit safety limit        : {self.gen_numbers[-1]} generations")
            print(f"  (consider increasing MAX_GEN if solution quality is poor)")
        print(f"  Final hypervolume       : {self.hypervolume[-1]:.4f}")
        print(f"  Final diversity         : {self.diversity[-1]:.2f}")
        final_best = self.best_per_obj[-1]
        labels = [
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
