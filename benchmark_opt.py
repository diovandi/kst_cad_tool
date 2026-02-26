import numpy as np
import time
from kst_rating_tool import ConstraintSet, PointConstraint, analyze_constraints_detailed

def benchmark():
    # Create a constraint set that yields many combinations
    # 10 points -> 10 choose 5 = 252 combos
    # 12 points -> 12 choose 5 = 792 combos
    # 15 points -> 15 choose 5 = 3003 combos
    n_points = 12
    points = [
        PointConstraint(
            position=np.random.rand(3),
            normal=np.random.rand(3)
        ) for _ in range(n_points)
    ]
    cs = ConstraintSet(points=points)

    start_time = time.time()
    # We use n_workers=1 to focus on the loop overhead in the main process
    # although the issue also exists in the n_workers > 1 block.
    # Actually line 312 is in the n_workers > 1 block.
    res = analyze_constraints_detailed(cs, n_workers=2)
    end_time = time.time()

    print(f"Time taken for {n_points} points: {end_time - start_time:.4f} seconds")
    print(f"Number of processed combos: {res.combo_proc.shape[0]}")

if __name__ == "__main__":
    benchmark()
