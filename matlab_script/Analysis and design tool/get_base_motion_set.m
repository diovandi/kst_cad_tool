% Identify base motion set and combo rows that need recalculation when modifying constraints.
% Generic: works for any constraint set and any modified constraint indices.
%
% [combo_new, remain_idx, combo_proc_optimbase, mot_half_optimbase, mot_all_optimbase, Ri_optimbase] = ...
%   get_base_motion_set(cp_rev_all, combo, combo_proc_org, combo_dup_idx_org, no_mot_half, ...
%                       mot_half_org, mot_all_org, Ri);
%
% Inputs:
%   cp_rev_all   - column vector of constraint indices (1-based) being modified
%   combo        - full combination matrix (from combo_preproc)
%   combo_proc_org, combo_dup_idx_org, no_mot_half, mot_half_org, mot_all_org, Ri - from baseline analysis
% Outputs:
%   combo_new    - combo rows that contain any of cp_rev_all (need recalculation)
%   remain_idx   - indices into mot_half_org of motions to keep (base set)
%   combo_proc_optimbase, mot_half_optimbase, mot_all_optimbase, Ri_optimbase - base set data for merge

function [combo_new, remain_idx, combo_proc_optimbase, mot_half_optimbase, mot_all_optimbase, Ri_optimbase] = ...
    get_base_motion_set(cp_rev_all, combo, combo_proc_org, combo_dup_idx_org, no_mot_half, mot_half_org, mot_all_org, Ri)

del_idx = [];
for n = 1:length(cp_rev_all)
    [row_idx, ~, ~] = find(combo == cp_rev_all(n));
    del_idx = [del_idx; row_idx];
end
del_idx = unique(del_idx);

combo_red_idx = setdiff((1:size(combo,1))', del_idx);
dup_idx = combo_dup_idx_org(combo_red_idx);
dup_idx = unique(dup_idx);
if ~isempty(dup_idx), dup_idx(1) = []; end

del_idx_all = [];
for n = 1:length(cp_rev_all)
    [row_idx, ~, ~] = find(combo_proc_org(:,2:6) == cp_rev_all(n));
    del_idx_all = [del_idx_all; row_idx];
end
del_idx_all = unique(del_idx_all);
del_idx_nondup = setdiff(del_idx_all, dup_idx);

remain_idx = setdiff((1:no_mot_half)', del_idx_nondup);
remain_idx_full = [remain_idx; remain_idx + no_mot_half];

combo_new = combo(del_idx,:);
combo_proc_optimbase = combo_proc_org(remain_idx, 2:6);
mot_half_optimbase = mot_half_org(remain_idx,:);
mot_all_optimbase = mot_all_org(remain_idx_full,:);
Ri_optimbase = Ri(remain_idx_full,:);
end
