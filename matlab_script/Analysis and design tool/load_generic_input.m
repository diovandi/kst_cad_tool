% Load generic JSON input file and set global constraint variables.
% Use this for wizard-generated or generic input (any geometry).
% Sets: cp, cpin, clin, cpln, cpln_prop (and optionally grp_* for optimization).
%
% Usage:
%   load_generic_input('path/to/generic_example_analysis.json')
% Then run inputfile_check, input_preproc, cp_to_wrench, combo_preproc, main_loop, rating as usual.
%
% Requires: MATLAB R2016b+ (jsondecode).

function load_generic_input(json_path)
global cp cpin clin cpln cpln_prop grp_members grp_rev_type grp_srch_spc

raw = fileread(json_path);
data = jsondecode(raw);

% Analysis constraint set (may be at top level or under analysis_input)
if isfield(data, 'analysis_input')
    inp = data.analysis_input;
else
    inp = data;
end

% Helper: ensure row vector from JSON array
toRow = @(r) reshape(r, 1, []);

% Point contacts: [x,y,z,nx,ny,nz] per row
if isfield(inp, 'point_contacts') && ~isempty(inp.point_contacts)
    pc = inp.point_contacts;
    if iscell(pc)
        cp = cell2mat(cellfun(toRow, pc, 'UniformOutput', false));
    else
        cp = pc;
    end
else
    cp = [];
end

% Pins: [x,y,z,ax,ay,az] per row
if isfield(inp, 'pins') && ~isempty(inp.pins)
    pn = inp.pins;
    if iscell(pn)
        cpin = cell2mat(cellfun(toRow, pn, 'UniformOutput', false));
    else
        cpin = pn;
    end
else
    cpin = [];
end

% Lines: [mx,my,mz,lx,ly,lz,nx,ny,nz,length] per row
if isfield(inp, 'lines') && ~isempty(inp.lines)
    ln = inp.lines;
    if iscell(ln)
        clin = cell2mat(cellfun(toRow, ln, 'UniformOutput', false));
    else
        clin = ln;
    end
else
    clin = [];
end

% Planes: midpoint [3], normal [3], type, prop
if isfield(inp, 'planes') && ~isempty(inp.planes)
    cpln = [];
    cpln_prop = [];
    planes = inp.planes;
    if ~iscell(planes), planes = num2cell(planes); end
    for k = 1:numel(planes)
        pl = planes{k};
        if isstruct(pl)
            mid = toRow(pl.midpoint);
            nrm = toRow(pl.normal);
            cpln = [cpln; mid, nrm, pl.type];
            if isfield(pl, 'prop')
                cpln_prop = [cpln_prop; toRow(pl.prop)];
            else
                cpln_prop = [cpln_prop; zeros(1, 8)];
            end
        end
    end
else
    cpln = [];
    cpln_prop = [];
end

% Optimization plan (optional). When present, run baseline then optim_rev_from_candidates
% with data.optimization.candidate_matrix and data.optimization.modified_constraints.
grp_members = [];
grp_rev_type = [];
grp_srch_spc = [];
