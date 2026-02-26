
import numpy as np
from kst_rating_tool.constraints import (
    ConstraintSet,
    PointConstraint,
    PinConstraint,
    LineConstraint,
    PlaneConstraint,
    normalize,
)

def test_normalize():
    v = np.array([3.0, 4.0, 0.0])
    n = normalize(v)
    assert np.allclose(n, np.array([0.6, 0.8, 0.0]))

    # Check original not modified
    assert np.allclose(v, np.array([3.0, 4.0, 0.0]))

    v_zero = np.zeros(3)
    n_zero = normalize(v_zero)
    assert np.allclose(n_zero, v_zero)

def test_constraint_set_empty_serialization():
    cs = ConstraintSet()
    cp, cpin, clin, cpln, cpln_prop = cs.to_matlab_style_arrays()

    assert cp.shape == (0, 6)
    assert cpin.shape == (0, 6)
    assert clin.shape == (0, 10)
    assert cpln.shape == (0, 7)
    assert cpln_prop.shape == (0, 0)

    # Test roundtrip for empty
    cs_new = ConstraintSet.from_matlab_style_arrays(cp, cpin, clin, cpln, cpln_prop)
    assert cs_new.total_cp == 0

def test_constraint_set_serialization_roundtrip():
    points = [
        PointConstraint(position=np.array([1, 2, 3]), normal=np.array([0, 0, 1])),
        PointConstraint(position=np.array([4, 5, 6]), normal=np.array([0, 1, 0])),
    ]
    pins = [
        PinConstraint(center=np.array([7, 8, 9]), axis=np.array([1, 0, 0])),
    ]
    lines = [
        LineConstraint(
            midpoint=np.array([10, 11, 12]),
            line_dir=np.array([0, 1, 0]),
            constraint_dir=np.array([0, 0, 1]),
            length=5.0
        ),
    ]
    planes = [
        PlaneConstraint(
            midpoint=np.array([13, 14, 15]),
            normal=np.array([1, 0, 0]),
            type=1,
            prop=np.array([0, 1, 0, 10, 0, 0, 1, 5]) # Rectangular
        ),
    ]

    cs = ConstraintSet(points=points, pins=pins, lines=lines, planes=planes)

    cp, cpin, clin, cpln, cpln_prop = cs.to_matlab_style_arrays()

    assert cp.shape == (2, 6)
    assert cpin.shape == (1, 6)
    assert clin.shape == (1, 10)
    assert cpln.shape == (1, 7)
    assert cpln_prop.shape == (1, 8)

    cs_new = ConstraintSet.from_matlab_style_arrays(cp, cpin, clin, cpln, cpln_prop)

    assert cs_new.total_cp == cs.total_cp
    assert len(cs_new.points) == 2
    assert len(cs_new.pins) == 1
    assert len(cs_new.lines) == 1
    assert len(cs_new.planes) == 1

    # Deep comparison
    assert np.allclose(cs_new.points[0].position, cs.points[0].position)
    assert np.allclose(cs_new.points[0].normal, cs.points[0].normal)

    assert np.allclose(cs_new.pins[0].center, cs.pins[0].center)
    assert np.allclose(cs_new.pins[0].axis, cs.pins[0].axis)

    assert np.allclose(cs_new.lines[0].midpoint, cs.lines[0].midpoint)
    assert np.allclose(cs_new.lines[0].line_dir, cs.lines[0].line_dir)
    assert np.allclose(cs_new.lines[0].constraint_dir, cs.lines[0].constraint_dir)
    assert cs_new.lines[0].length == cs.lines[0].length

    assert np.allclose(cs_new.planes[0].midpoint, cs.planes[0].midpoint)
    assert np.allclose(cs_new.planes[0].normal, cs.planes[0].normal)
    assert cs_new.planes[0].type == cs.planes[0].type
    assert np.allclose(cs_new.planes[0].prop, cs.planes[0].prop)


def test_constraint_set_mixed_planes_serialization():
    # This checks correct padding for varying prop lengths
    planes = [
        PlaneConstraint(
            midpoint=np.zeros(3),
            normal=np.array([0, 0, 1]),
            type=1, # Rectangular
            prop=np.array([1, 0, 0, 10, 0, 1, 0, 5], dtype=float)
        ),
        PlaneConstraint(
            midpoint=np.zeros(3),
            normal=np.array([0, 0, 1]),
            type=2, # Circular
            prop=np.array([5], dtype=float)
        )
    ]
    cs = ConstraintSet(planes=planes)

    cp, cpin, clin, cpln, cpln_prop = cs.to_matlab_style_arrays()

    assert cpln.shape == (2, 7)
    # The prop array should have the width of the largest prop (8)
    assert cpln_prop.shape == (2, 8)

    # Check padding
    assert cpln_prop[1, 0] == 5.0 # Radius
    assert np.all(cpln_prop[1, 1:] == 0.0) # Zero padding

    # Roundtrip check
    cs_new = ConstraintSet.from_matlab_style_arrays(cp, cpin, clin, cpln, cpln_prop)
    assert len(cs_new.planes) == 2

    # Verify that we can recover meaningful data
    # Note: roundtrip results in padded array, original was length 1
    assert cs_new.planes[1].prop.shape == (8,)
    assert cs_new.planes[1].prop[0] == 5.0
