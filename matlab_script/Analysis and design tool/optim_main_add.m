% Main processor for constraint addition
% filename: optim_main_add.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University
% 
% WARNING: THIS PERLIMINARY CODE CONTAINS ERRORS. IN THE DISSERTATION
% CONSTRAINT ADDITION IS STILL DONE MANUALLY.

global cp cpin clin cpln cpln_prop 
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev
global no_cp no_cpin no_clin no_cpln
global no_cp_rev no_cpin_rev no_clin_rev no_cpln_rev
global wr_all
global pts_rev max_d_rev

cp_rev=cp;cpin_rev=cpin;clin_rev=clin;cpln_rev=cpln;cpln_prop_rev=cpln_prop;
no_cp_rev=no_cp;no_cpin_rev=no_cpin;no_clin_rev=no_clin;no_cpln_rev=no_cpln;

Ri_insert=Ri;
    
% First relocate the cp(s) according to each type of cp
% Possibly organize these into functions to relocate cp or reorient cp

% add_type=input('What type of addition constraint search? ');

% Normalize direction cosines for each constraint type
for i=1:size(cp_rev,1)
    cp_rev(i,4:6)=cp_rev(i,4:6)./norm(cp_rev(i,4:6));
end

for i=1:size(cpin_rev,1)
    cpin_rev(i,4:6)=cpin_rev(i,4:6)./norm(cpin_rev(i,4:6));
end

for i=1:size(clin_rev,1)
    clin_rev(i,4:6)=clin_rev(i,4:6)./norm(clin_rev(i,4:6));
    clin_rev(i,7:9)=clin_rev(i,7:9)./norm(clin_rev(i,7:9));
end

for i=1:size(cpln_rev,1)
    cpln_rev(i,4:6)=cpln_rev(i,4:6)./norm(cpln_rev(i,4:6));
end

for i=1:length(add_cp_type)
    if add_cp_type(i)==1    
        no_cp_rev=no_cp_rev+1;
        cp_rev(no_cp_rev,:)=add_cp(i,:);
    elseif add_cp_type(i)==2
        no_cpin_rev=no_cpin_rev+1;
        cpin_rev(no_cpin_rev,:)=add_cp;
    elseif add_cp_type(i)==3
        no_clin_rev=no_clin_rev+1;
        clin_rev(no_clin_rev,:)=add_cp;
    elseif add_cp_type(i)==4    
        no_cpln_rev=no_cpln_rev+1;
        cpln_rev(no_cpln_rev,:)=add_cp(1:7);
        cpln_prop_rev(no_cpln_rev,:)=add_cp(8:15);
    end
end

total_cp_rev = no_cp_rev+no_cpin_rev+no_clin_rev+no_cpln_rev;

% Transform revised cp into revised wrenches
[wr_all_new pts_rev max_d_rev]=cp_to_wrench(cp_rev,cpin_rev,clin_rev,cpln_rev,cpln_prop_rev);

cp_add_idx=[];

for j=1:(no_cp_rev-no_cp)
    cp_add_idx=[cp_add_idx; no_cp+j];
end

for j=1:(no_cpin_rev-no_cpin)
    cp_add_idx=[cp_add_idx; no_cp_rev+no_cpin+j];
end

for j=1:(no_clin_rev-no_clin)
    cp_add_idx=[cp_add_idx; no_cp_rev+no_cpin_rev+no_clin+j];
end

for j=1:(no_cpln_rev-no_cpln)
    cp_add_idx=[cp_add_idx; no_cp_rev+no_cpin_rev+no_clin_rev+no_cpln+j];
end

% Calculate additional cp for the original motion
[R_add_cp]=rate_motset(combo_proc_org(:,2:6),...
    mot_half_org,cp_add_idx,'additional');
Ri_add_cp=1./R_add_cp;

% Substitute revised CP columns in the rating matrix
for k=1:length(cp_add_idx)%this is the for loop for inserting the new columns
    Ri_swap=[Ri_insert(:,1:cp_add_idx(k)-1) Ri_add_cp(:,k) Ri_insert(:,cp_add_idx(k):end)];
    Ri_insert=Ri_swap;
end

% Re-create combinations that contain cp_rev
% use mainloop function

[combo_rev]=combo_preproc(total_cp_rev,'revised');
row_all=[];
for p=1:length(cp_add_idx)
    [row dum1 dum2]=find(combo_rev==cp_add_idx(p));
    row_all=[row_all ;row];
end
combo_new_idx=unique(row_all);
combo_new=combo_rev(combo_new_idx,:);
[mot_all_add R_add combo_proc_rev]=main_loop(combo_new,wr_all_new,0,'revised');
Ri_add=1./R_add;
mot_all_add_rev=[-mot_all_add(:,1:6) mot_all_add(:,7:10)];
    
%Merge reduced old rating with new rating
Ri_new=[Ri_insert;Ri_add];
mot_all_new=[mot_all_org;mot_all_add;mot_all_add_rev];
[mot_all_new_uniq uniq_idx]=unique(mot_all_new,'rows');
Ri_new_uniq=Ri_new(uniq_idx,:);

% Calculate new rating
[Rating_all_rev WTR_idx_rev free_mot_rev free_mot_idx_rev best_cp_rev rowsum_rev]=rating(Ri_new_uniq, mot_all_new_uniq);
histogr(Rating_all_rev, rowsum_rev)
disp(Rating_all_rev)



