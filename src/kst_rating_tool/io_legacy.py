from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .constraints import ConstraintSet


def _parse_matlab_vector(s: str) -> np.ndarray:
    """Parse a MATLAB row vector string like ' 3.57 -0.75 -0.50  0.43  0.75  0.50' or '0.625 0 0, 0, 0 0 0, 0' into a 1D array."""
    parts = re.split(r"[\s,]+", s.strip())
    parts = [x for x in parts if x]
    return np.array([float(x) for x in parts], dtype=float)


def _collect_numbered_vars(
    content: str,
    prefix: str,
    cols_per_row: int,
) -> dict[str, np.ndarray]:
    """Find all occurrences of prefixN = [ ... ]; and return them as a dict."""
    pattern = re.compile(
        rf"{re.escape(prefix)}(\d+)\s*=\s*\[\s*([^]]+)\]\s*;",
    )
    vars_dict: dict[str, np.ndarray] = {}
    for m in pattern.finditer(content):
        name = prefix + m.group(1)
        vec = _parse_matlab_vector(m.group(2))
        if vec.size == cols_per_row:
            vars_dict[name] = vec
    return vars_dict


def _parse_matlab_matrix_from_refs(
    inner: str,
    vars_dict: dict[str, np.ndarray],
    error_on_missing: bool = False,
) -> list[np.ndarray] | None:
    """Parse a MATLAB matrix from a string of variable references (e.g., 'cp1; cp2; ...')."""
    # Remove MATLAB line continuation "..." so "cp10;... cp11" -> "cp10; cp11"
    inner = re.sub(r"\.\.\.\s*", " ", inner)
    refs = re.split(r"\s*;\s*", inner)
    rows = []
    for ref in refs:
        ref = ref.strip()
        if not ref:
            continue
        if ref not in vars_dict:
            if error_on_missing:
                raise ValueError(f"Unknown variable in MATLAB assignment: {ref}")
            return None
        rows.append(vars_dict[ref])
    return rows


def _parse_cp_only_m_file(text: str) -> np.ndarray:
    """Parse cp-only .m file content; return cp as (n, 6) with position and normal columns.
    Handles: cp1 = [ ... ]; ... cp = [cp1;cp2;...];  or  cp = [ row1; row2; ... ];
    """
    # Strip single-line comments (rest of line after %)
    lines = []
    for line in text.splitlines():
        idx = line.find("%")
        if idx >= 0:
            line = line[:idx]
        line = line.strip()
        if line:
            lines.append(line)
    content = " ".join(lines)

    # Case 4 (case2b): ct_2 = input(...); use ct_2==7 branch
    m_assign = None
    content_before_assign = ""
    if "ct_2 = input" in content or "ct_2=input" in content:
        m7 = re.search(r"elseif\s+ct_2\s*==\s*7\s+cp\s*=\s*\[\s*([^]]+)\]\s*;", content)
        if m7:
            content_before_assign = (content.split("ct_2 = input")[0].split("ct_2=input")[0])
            m_assign = m7
    if m_assign is None:
        m_assign = re.search(r"cp\s*=\s*\[\s*([^]]+)\]\s*;", content)
        if not m_assign:
            raise ValueError("No 'cp = [ ... ];' found in file")
        content_before_assign = content[: m_assign.start()]

    cp_vars = _collect_numbered_vars(content_before_assign, "cp", 6)

    inner = m_assign.group(1).strip()
    # Check if it's cp1;cp2;... (variable refs) or numeric rows
    if re.match(r"^cp\d+", inner.replace(" ", ""), re.IGNORECASE):
        # Variable refs: cp1;cp2;cp3;...
        rows = _parse_matlab_matrix_from_refs(inner, cp_vars, error_on_missing=True)
        if not rows:
            raise ValueError("cp matrix has no valid variable references")
        cp = np.vstack(rows)
    else:
        # Literal matrix: "a b c d e f ; g h i j k l ; ..."
        row_strs = re.split(r"\s*;\s*", inner)
        rows = []
        for rs in row_strs:
            rs = rs.strip()
            if not rs:
                continue
            vec = _parse_matlab_vector(rs)
            if vec.size == 6:
                rows.append(vec)
        if not rows:
            raise ValueError("cp matrix has no valid rows")
        cp = np.vstack(rows)

    return cp


def _parse_optional_matrix(
    content: str,
    var_prefix: str,
    assign_name: str,
    cols_per_row: int,
) -> np.ndarray | None:
    """Parse optional MATLAB matrix: var_prefix1 = [ ... ]; ... assign_name = [ var_prefix1; ... ];"""
    vars_dict = _collect_numbered_vars(content, var_prefix, cols_per_row)

    assign_re = re.compile(
        rf"{re.escape(assign_name)}\s*=\s*\[\s*([^]]+)\]\s*;",
        re.IGNORECASE,
    )
    m = assign_re.search(content)
    if not m or not vars_dict:
        return None

    rows = _parse_matlab_matrix_from_refs(m.group(1).strip(), vars_dict)
    if not rows:
        return None

    return np.vstack(rows)


def _parse_optional_matrix_or_single(
    content: str,
    var_prefix: str,
    assign_name: str,
    cols_per_row: int,
) -> np.ndarray | None:
    """Parse optional matrix: assign_name = [ a; b; ... ] or assign_name = var_prefix1 (single)."""
    vars_dict = _collect_numbered_vars(content, var_prefix, cols_per_row)
    # Single: cpln = cpln1 (only if we have vars)
    if vars_dict:
        m_single = re.search(
            rf"{re.escape(assign_name)}\s*=\s*(\w+)\s*;",
            content,
            re.IGNORECASE,
        )
        if m_single:
            ref = m_single.group(1).strip()
            if ref in vars_dict:
                return vars_dict[ref].reshape(1, -1)
    # Matrix: assign_name = [ a; b; ... ]
    mat = _parse_optional_matrix(content, var_prefix, assign_name, cols_per_row)
    if mat is not None:
        return mat
    # Literal single row: cpln = [ a b c d e f g ];
    m_lit = re.search(
        rf"{re.escape(assign_name)}\s*=\s*\[\s*([^]]+)\]\s*;",
        content,
        re.IGNORECASE,
    )
    if m_lit:
        vec = _parse_matlab_vector(m_lit.group(1))
        if vec.size == cols_per_row:
            return vec.reshape(1, -1)
    return None


def _extract_active_branch(text: str) -> str:
    """Extract the active code branch from a MATLAB file with conditionals.

    Handles case4a-style files with ``if no_snap==0 ... elseif no_snap==2 ...``
    by extracting only the first branch (``no_snap==0``).

    Also strips ``if ~exist('no_snap'...)`` preamble lines.
    Returns the full text unchanged for files without ``no_snap`` conditionals.
    """
    # Strip single-line comments
    lines = []
    for line in text.splitlines():
        idx = line.find("%")
        if idx >= 0:
            line = line[:idx]
        line = line.rstrip()
        if line.strip():
            lines.append(line)
    joined = "\n".join(lines)

    # Check for no_snap conditional pattern
    m_branch = re.search(r'if\s+no_snap\s*==\s*0\b', joined)
    if not m_branch:
        return text  # no conditional — return unchanged

    # Find the start of the first branch (right after 'if no_snap==0')
    branch_start = m_branch.end()

    # Find the end: the next top-level 'elseif', 'else', or 'end' at the same nesting level
    depth = 1
    pos = branch_start
    branch_end = len(joined)
    while pos < len(joined):
        # Look for keywords
        m_kw = re.search(r'\b(if|elseif|else|end)\b', joined[pos:])
        if not m_kw:
            break
        kw = m_kw.group(1)
        kw_pos = pos + m_kw.start()
        if kw == 'if':
            depth += 1
            pos = kw_pos + len(kw)
        elif kw in ('elseif', 'else'):
            if depth == 1:
                branch_end = kw_pos
                break
            pos = kw_pos + len(kw)
        elif kw == 'end':
            if depth == 1:
                branch_end = kw_pos
                break
            depth -= 1
            pos = kw_pos + len(kw)
        else:
            pos = kw_pos + len(kw)

    # Return everything before the if-block + the first branch content
    preamble = joined[:m_branch.start()]
    branch_body = joined[branch_start:branch_end]
    return preamble + "\n" + branch_body


def load_case_m_file(
    path: str | Path,
    *,
    normalize_normals: bool = True,
) -> ConstraintSet:
    """Load a MATLAB case file and return a ConstraintSet.

    Parses .m files that define a ``cp`` matrix and optionally ``cpin``, ``clin``,
    ``cpln``, ``cpln_prop``.

    Handles conditional files (e.g. case4a with ``no_snap`` branches) by extracting
    only the first branch.

    Parameters
    ----------
    path
        Path to the .m case file (e.g. matlab_script/Input_files/case1a_chair_height.m).
    normalize_normals
        If True (default), normalize each row's normal (columns 4:6) as in input_preproc.m.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")

    # Extract the active branch for files with conditionals (e.g. case4a)
    active_text = _extract_active_branch(text)

    # Strip comments for content-based parsing
    content = " ".join(
        line[: line.find("%")] if "%" in line else line
        for line in active_text.splitlines()
        if line.strip()
    )

    cp = _parse_cp_only_m_file(active_text)

    # Optional cpin (6 cols), clin (10 cols)
    # Use _parse_optional_matrix_or_single so single-row literal assignments
    # like "cpin=[0 0 0 0 0 1];" (without cpin1, cpin2, etc.) are parsed.
    cpin = _parse_optional_matrix_or_single(content, "cpin", "cpin", 6)
    if cpin is None:
        cpin = np.empty((0, 6), dtype=float)
    clin = _parse_optional_matrix_or_single(content, "clin", "clin", 10)
    if clin is None:
        clin = np.empty((0, 10), dtype=float)
    # cpln (7 cols: midpoint 3, normal 3, type 1), cpln_prop (8 for rect)
    cpln = _parse_optional_matrix_or_single(content, "cpln", "cpln", 7)
    if cpln is None:
        cpln = np.empty((0, 7), dtype=float)
    cpln_prop = _parse_optional_matrix_or_single(content, "cpln_prop", "cpln_prop", 8)
    if cpln_prop is None:
        cpln_prop = np.empty((0, 8), dtype=float)

    # ---- Normalize direction cosines (mirrors MATLAB input_preproc.m) ----
    if normalize_normals:
        # CP: normalize normal vector (cols 4:6)
        for i in range(cp.shape[0]):
            n = cp[i, 3:6]
            nnorm = np.linalg.norm(n)
            if nnorm > 0:
                cp[i, 3:6] = n / nnorm
        # CPIN: normalize pin axis (cols 4:6)
        for i in range(cpin.shape[0]):
            n = cpin[i, 3:6]
            nnorm = np.linalg.norm(n)
            if nnorm > 0:
                cpin[i, 3:6] = n / nnorm
        # CLIN: normalize line direction (cols 4:6) AND constraint direction (cols 7:9)
        for i in range(clin.shape[0]):
            d = clin[i, 3:6]
            dnorm = np.linalg.norm(d)
            if dnorm > 0:
                clin[i, 3:6] = d / dnorm
            c = clin[i, 6:9]
            cnorm = np.linalg.norm(c)
            if cnorm > 0:
                clin[i, 6:9] = c / cnorm
        # CPLN: normalize plane normal (cols 4:6)
        for i in range(cpln.shape[0]):
            n = cpln[i, 3:6]
            nnorm = np.linalg.norm(n)
            if nnorm > 0:
                cpln[i, 3:6] = n / nnorm

    return ConstraintSet.from_matlab_style_arrays(cp, cpin, clin, cpln, cpln_prop)
