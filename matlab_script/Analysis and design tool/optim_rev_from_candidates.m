% Run constraint revision optimization from a precomputed candidate matrix (generic).
% Use when the wizard (or other tool) has already discretized the search space
% and provides candidate constraint rows (e.g. CP6.1, CP6.2, ...) instead of grp_srch_spc.
%
% For a single modified point constraint: candidate_matrix is N x 6 (each row = [x,y,z,nx,ny,nz]).
%
% [WTR_all, MTR_all, TOR_all] = optim_rev_from_candidates(cp_rev_all, candidate_matrix);
%
% Requires baseline analysis to be done (globals: cp, combo, combo_proc_org, mot_half_org, etc.).

function [WTR_all, MTR_all, TOR_all] = optim_rev_from_candidates(cp_rev_all, candidate_matrix)
global cp cpin clin cpln cpln_prop
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev
global combo combo_proc_org combo_dup_idx_org
global mot_half_org mot_all_org no_mot_half
global Ri wr_all

if isempty(cp_rev_all) || size(candidate_matrix, 2) < 6
    error('optim_rev_from_candidates: need cp_rev_all and candidate_matrix Nx6 (point contact).');
end

% Support only one modified constraint (index) for now; candidate_matrix = N x 6
cp_idx = cp_rev_all(1);
N = size(candidate_matrix, 1);
WTR_all = zeros(1, N);
MTR_all = zeros(1, N);
TOR_all = zeros(1, N);

[combo_new, remain_idx, combo_proc_optimbase, mot_half_optimbase, mot_all_optimbase, Ri_optimbase] = ...
    get_base_motion_set(cp_rev_all, combo, combo_proc_org, combo_dup_idx_org, no_mot_half, ...
                       mot_half_org, mot_all_org, Ri);

for k = 1:N
    % Build revised constraint set: replace cp(cp_idx,:) with candidate row (set globals for main_loop/rate_motset)
    cp_rev = cp;
    cp_rev(cp_idx,:) = candidate_matrix(k, 1:6);
    cpin_rev = cpin;
    clin_rev = clin;
    cpln_rev = cpln;
    cpln_prop_rev = cpln_prop;

    % Revised wrenches (only affected rows change; cp_rev_to_wrench handles it)
    [wr_all_new, ~, ~] = cp_rev_to_wrench(wr_all, cp_rev_all, cp_rev, cpin_rev, clin_rev, cpln_rev, cpln_prop_rev);

    % Re-rate base motions with revised CP column(s)
    [R_recalc] = rate_motset(combo_proc_optimbase, mot_half_optimbase, cp_rev_all, 'revised');
    Ri_recalc = 1 ./ R_recalc;
    Ri_optimbase_recalc = Ri_optimbase;
    Ri_optimbase_recalc(:, cp_rev_all) = Ri_recalc;

    % Recompute motions for combo_new only
    set = 'revised';
    dispbar = 0;
    [mot_all_add, R_add, ~, ~, ~] = main_loop(combo_new, wr_all_new, dispbar, set);
    Ri_add = 1 ./ R_add;
    mot_all_add_rev = [-mot_all_add(:,1:6), mot_all_add(:,7:10)];

    % Merge and unique
    Ri_new = [Ri_optimbase_recalc; Ri_add];
    mot_all_new = [mot_all_optimbase; mot_all_add; mot_all_add_rev];
    [mot_all_new_uniq, uniq_idx] = unique(mot_all_new, 'rows', 'first');
    Ri_new_uniq = Ri_new(uniq_idx, :);

    [Rating_all_rev, ~, ~, ~, ~] = rating(Ri_new_uniq, mot_all_new_uniq);
    WTR_all(k) = Rating_all_rev(1);
    MTR_all(k) = Rating_all_rev(3);
    TOR_all(k) = sum(Ri_new_uniq, 'all') / numel(Ri_new_uniq);
end
end
