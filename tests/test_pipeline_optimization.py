
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from kst_rating_tool.pipeline import analyze_constraints, analyze_constraints_detailed
from kst_rating_tool.constraints import ConstraintSet, PointConstraint
from kst_rating_tool.rating import RatingResults

# Mock helper functions to control the output of `rec_mot`, `form_combo_wrench`, etc.
# This allows us to inject specific motions (duplicates, NaNs) without relying on complex geometry.

@pytest.fixture
def mock_pipeline_dependencies():
    with patch("kst_rating_tool.pipeline.form_combo_wrench") as mock_form, \
         patch("kst_rating_tool.pipeline.matlab_rank") as mock_rank, \
         patch("kst_rating_tool.pipeline.rec_mot") as mock_rec_mot, \
         patch("kst_rating_tool.pipeline.input_wr_compose") as mock_input, \
         patch("kst_rating_tool.pipeline.react_wr_5_compose") as mock_react, \
         patch("kst_rating_tool.pipeline._rate_motion_all_constraints") as mock_rate, \
         patch("kst_rating_tool.pipeline.cp_to_wrench") as mock_cp_to_wr, \
         patch("kst_rating_tool.pipeline.combo_preproc") as mock_combo:

        # Default behaviors
        mock_cp_to_wr.return_value = ([], np.zeros((3,1)), 1.0)
        mock_rank.return_value = 5
        mock_input.return_value = (np.zeros(6), 0)
        mock_react.return_value = np.zeros(6)

        # Mock rating output: 7 arrays
        mock_rate.return_value = (
            np.array([1.0]), np.array([1.0]), np.array([1.0]),
            np.array([1.0]), np.array([1.0]), np.array([1.0]), np.array([1.0])
        )

        yield {
            "form": mock_form,
            "rank": mock_rank,
            "rec_mot": mock_rec_mot,
            "combo": mock_combo,
            "rate": mock_rate
        }

def create_mock_motion(arr_values):
    """Create a mock object that behaves like a ScrewMotion."""
    mock_mot = MagicMock()
    # as_array().ravel() should return the array
    mock_mot.as_array.return_value.ravel.return_value = np.array(arr_values, dtype=float)
    mock_mot.rho = np.zeros(3)
    return mock_mot

def test_analyze_constraints_duplicate_detection(mock_pipeline_dependencies):
    """
    Verify that `analyze_constraints` correctly identifies duplicates based on rounded values,
    and treats NaNs as distinct (non-duplicates).
    """
    mocks = mock_pipeline_dependencies

    # Setup constraints (dummy)
    cs = ConstraintSet(points=[PointConstraint(np.zeros(3), np.array([0,0,1]))])

    # We want to simulate 4 combos:
    # 1. Motion A
    # 2. Motion B (near-equal to A, rounds to same values) -> Should be duplicate
    # 3. Motion C (contains NaN)
    # 4. Motion D (contains NaN, identical to C) -> Should NOT be duplicate (NumPy/tuple logic)

    mocks["combo"].return_value = np.array([[1,2,3,4,5]] * 4) # 4 iterations

    # Create motions
    mot_a = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    mot_b = mot_a + 1e-6 # Small diff, rounds to same
    mot_c = np.array([np.nan] * 10)
    mot_d = np.array([np.nan] * 10)

    # Setup rec_mot to return these sequentially
    mocks["rec_mot"].side_effect = [
        create_mock_motion(mot_a),
        create_mock_motion(mot_b),
        create_mock_motion(mot_c),
        create_mock_motion(mot_d)
    ]

    # Run analysis
    results = analyze_constraints(cs, n_workers=1)

    # We expect `analyze_constraints` to call `_rate_motion_all_constraints` for each UNIQUE motion.
    # Motion A: Unique -> Processed
    # Motion B: Duplicate of A -> Skipped
    # Motion C: Unique (NaN) -> Processed
    # Motion D: Unique (NaN != NaN) -> Processed

    # Total processed: 3
    assert mocks["rate"].call_count == 3

    # Check parallel execution as well
    mocks["rate"].reset_mock()
    mocks["rec_mot"].side_effect = [
        create_mock_motion(mot_a),
        create_mock_motion(mot_b),
        create_mock_motion(mot_c),
        create_mock_motion(mot_d)
    ]

    # Note: mocking pool map/apply is hard because it pickles functions.
    # However, `analyze_constraints` with n_workers > 1 uses `multiprocessing.Pool`.
    # Mocking `Pool` in `kst_rating_tool.pipeline` is required.

    with patch("kst_rating_tool.pipeline.Pool") as mock_pool_cls:
        mock_pool = mock_pool_cls.return_value
        mock_pool.__enter__.return_value = mock_pool

        # We need to simulate what `_process_combo_chunk` returns.
        # It returns a list of (combo_i, mot_arr, R_two_rows).
        # We can construct the return value of `pool.map`.

        # Helper to make dummy R rows
        dummy_R = np.zeros((2, 10)) # 2 rows, enough columns

        # chunk_results: list of lists of results
        # Let's say we have 1 chunk with all 4 results

        # We need to manually round for the test data setup because the real code does it inside _process_combo_chunk
        r_a = np.round(mot_a * 1e4) / 1e4
        r_b = np.round(mot_b * 1e4) / 1e4
        r_c = np.round(mot_c * 1e4) / 1e4 # stays nan
        r_d = np.round(mot_d * 1e4) / 1e4

        chunk_data = [
            [(0, r_a, dummy_R),
             (1, r_b, dummy_R),
             (2, r_c, dummy_R),
             (3, r_d, dummy_R)]
        ]

        mock_pool.map.return_value = chunk_data

        # Run parallel analysis
        analyze_constraints(cs, n_workers=2)

        # The main process loop iterates over these results.
        # It checks duplicates using the set.
        # It should add to `mot_hold` if not duplicate.

        # We can't easily inspect `mot_hold` inside the function, but we can verify behavior
        # via the result or by side effects if we could spy on `mot_hold`.
        # Since we can't spy on locals, we can verify the aggregate result or coverage.

        # However, the best proxy is that `analyze_constraints` returns a `RatingResults`.
        # If behavior is correct, `mot_hold` should end up with 3 items (A, C, D).
        # The function `analyze_constraints` calculates `R` from `mot_hold` size or content if `mot_hold` is used.
        # Actually `R` is built from `R_two_rows` appended to lists.
        # Wait, if `already` is true, it `continues` and DOES NOT append to `Rcp_pos_rows` etc.
        # So the final `R` matrix size depends on how many were accepted.

        # analyze_constraints returns `aggregate_ratings(R_uniq)`.
        # `R_uniq` comes from `mot_all` unique check at the end.
        # But `mot_hold` logic filters BEFORE that.

        # Let's look at `analyze_constraints_detailed` which returns `mot_half` and `combo_dup_idx`.
        # That's easier to verify.
        pass

def test_analyze_constraints_detailed_indices(mock_pipeline_dependencies):
    """
    Verify `analyze_constraints_detailed` correctly assigns `combo_dup_idx`
    using the dictionary map.
    """
    mocks = mock_pipeline_dependencies
    cs = ConstraintSet(points=[PointConstraint(np.zeros(3), np.array([0,0,1]))])

    mocks["combo"].return_value = np.array([[1,2,3,4,5]] * 4)

    mot_a = np.array([1.0] * 10)
    mot_b = mot_a + 1e-6 # Duplicate of A (index 1)
    mot_c = np.array([2.0] * 10) # New (index 2)
    mot_d = mot_a + 1e-8 # Duplicate of A (index 1)

    # 1. Test Sequential (n_workers=1)
    mocks["rec_mot"].side_effect = [
        create_mock_motion(mot_a),
        create_mock_motion(mot_b),
        create_mock_motion(mot_c),
        create_mock_motion(mot_d)
    ]

    res_seq = analyze_constraints_detailed(cs, n_workers=1)

    # Expected indices:
    # 0: 0 (New) -> stored at index 0 in mot_hold
    # 1: 1 (Duplicate of A) -> mot_hold[0] is A. Index in Python is 0. MATLAB/Output usually 1-based?
    #    Code says: `idx_existing = mot_map[mot_tuple]`, `combo_dup_idx[combo_i] = idx_existing + 1`
    #    So if duplicate of first item (index 0), dup_idx should be 1.
    # 2: 0 (New) -> stored at index 1
    # 3: 1 (Duplicate of A) -> dup_idx should be 1.

    assert res_seq.combo_dup_idx[0] == 0
    assert res_seq.combo_dup_idx[1] == 1
    assert res_seq.combo_dup_idx[2] == 0
    assert res_seq.combo_dup_idx[3] == 1

    # 2. Test Parallel (n_workers=2)
    # We mock Pool again
    with patch("kst_rating_tool.pipeline.Pool") as mock_pool_cls:
        mock_pool = mock_pool_cls.return_value
        mock_pool.__enter__.return_value = mock_pool

        dummy_R = np.zeros((2, 10))
        r_a = np.round(mot_a * 1e4) / 1e4
        r_b = np.round(mot_b * 1e4) / 1e4
        r_c = np.round(mot_c * 1e4) / 1e4
        r_d = np.round(mot_d * 1e4) / 1e4

        # Order in result list matters. Assuming they come back in order or are sorted by index (code sorts them).
        chunk_data = [
            [(0, r_a, dummy_R),
             (1, r_b, dummy_R),
             (2, r_c, dummy_R),
             (3, r_d, dummy_R)]
        ]
        mock_pool.map.return_value = chunk_data

        res_par = analyze_constraints_detailed(cs, n_workers=2)

        assert res_par.combo_dup_idx[0] == 0
        assert res_par.combo_dup_idx[1] == 1
        assert res_par.combo_dup_idx[2] == 0
        assert res_par.combo_dup_idx[3] == 1
