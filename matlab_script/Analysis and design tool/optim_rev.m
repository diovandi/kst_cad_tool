function [Rating_all_rev Ri_new_uniq mot_all_new_uniq]=optim_rev(x,x_map,...
    Ri_optimbase,mot_all_optimbase,mot_half_optimbase, combo_proc_optimbase,combo_new)
% Constraint modification routine called in nested for-loop from optim_main_rev
% filename: optim_rev.m
% Called functions: move_pt_srch, move_lin_srch, move_circlin_srch, move_pln_srch
%                   orient1d_srch, orient2d_srch, line_orient1d_srch, resize_lin_srch
%                   resize_rectpln_srch, resize_circpln_srch, cp_rev_to_wrench
%                   rate_motset, main_loop, rating
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global cp cpin clin cpln cpln_prop 
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev
global grp_members grp_rev_type grp_srch_spc cp_rev_all
global wr_all
global pts_rev max_d_rev
global combo_dup_idx_org

cp_rev=cp; cpin_rev=cpin; clin_rev=clin;
cpln_rev=cpln; cpln_prop_rev=cpln_prop;

% Relocate and reorient modified constraints according to rev type
% 1 - move location, point search
% 2 - move location, straight line search
% 3 - move location, curved line search
% 4 - move location, plane search
% 5 - reorient normal, 1D angular search
% 6 - reorient normal, 2D angular search
% 7 - reorient line, 1D angular search
% 8 - resize line length
% 9,10 - resize plane length and width for rectangular plane and circular plane

% This for loop is based on the numebr of group. Linked constraints are done within the subroutines
for i=1:size(grp_members,1) 
    % i is the group #
    rev_type=grp_rev_type(i);
    cp_rev_in_group=nonzeros(grp_members(i,:));
    if rev_type==1
        clc
        disp('THE POINT REV_TYPE IS PRELIMINARY AND MOST LIKELY CONTAIN ERRORS')
        return
        % Right now the dimensions of pt srch is still only for one constraint
        % It also does not allow two constraints cause they can occupy the same search space  x_grp=x(x_map(i,1));
%         move_pt_srch(x_grp,cp_rev_in_group,grp_srch_spc);  
    elseif rev_type==2
        x_grp=x(x_map(i,1));
        move_lin_srch(x_grp,cp_rev_in_group,grp_srch_spc(i,:));
    elseif rev_type==3
        x_grp=x(x_map(i,1));
        move_curvlin_srch(x_grp,cp_rev_in_group,grp_srch_spc(i,:));
    elseif rev_type==4
        x_grp=x(x_map(i,1:2));
        move_pln_srch(x_grp,cp_rev_in_group,grp_srch_spc(i,:));
    elseif rev_type==5
        x_grp=x(x_map(i,1));
        orient1d_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
    elseif rev_type==6
        x_grp=x(x_map(i,1:2));
        orient2d_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
    elseif rev_type==7
        x_grp=x(x_map(i,1));
        line_orient1d_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
    elseif rev_type==8
        x_grp=x(x_map(i,1));
        resize_lin_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
    elseif rev_type==9
        x_grp=x(x_map(i,1));
        resize_rectpln_srch(x_grp(1:2),cp_rev_in_group, grp_srch_spc(i,:));
    elseif rev_type==10
        x_grp=x(x_map(i,1));
        resize_circpln_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
    end

end

% Transform revised cp into revised wrenches
[wr_all_new pts_rev max_d_rev]=cp_rev_to_wrench(wr_all,cp_rev_all, ...
    cp_rev, cpin_rev, clin_rev, cpln_rev, cpln_prop_rev);

%mot_all_optimbase is duplex mot format

% Re-calculate cp_rev column in rating with old motion
[R_recalc]=rate_motset(combo_proc_optimbase,...
    mot_half_optimbase,cp_rev_all,'revised');
Ri_recalc=1./R_recalc;

% Substitute revised CP columns in the rating matrix
Ri_optimbase_recalc=Ri_optimbase;
Ri_optimbase_recalc(:,cp_rev_all)=Ri_recalc;

% Re-create combinations that contain cp_rev
% use mainloop function
dispbar=0; %disable progress bar
set='revised';
[mot_all_add R_add dmy1 dmy2 dmy3]=main_loop(combo_new,wr_all_new,dispbar,set);
Ri_add=1./R_add;
mot_all_add_rev=[-mot_all_add(:,1:6) mot_all_add(:,7:10)];
    
%Merge reduced old rating with additional rating
Ri_new=[Ri_optimbase_recalc;Ri_add];
mot_all_new=[mot_all_optimbase;mot_all_add;mot_all_add_rev];
[mot_all_new_uniq uniq_idx]=unique(mot_all_new,'rows','first');
Ri_new_uniq=Ri_new(uniq_idx,:);

% Calculate new rating
[Rating_all_rev WTR_idx_rev free_mot_rev free_mot_idx_rev best_cp_rev]=rating(Ri_new_uniq, mot_all_new_uniq);



