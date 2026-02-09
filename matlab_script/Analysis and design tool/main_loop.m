function [mot_half R combo_proc input_wr_proc d_proc]=main_loop(combo,wr_all,dispbar,set)
% Main processor for computing reciprocal motions from pivot constraint sets and rate resistance quality
% filename: main_loop.m
% Function: 
% - Create pivot wrench set
% - Check linear independence in pivot wrench matrix
% - Calculate reciprocal motion
% - Test for duplicate motion
% - Create input wrench and reaction wrench
% - Rate resistance quality of each constraints to the motion
% - Merge resistance values
%
% Input variables: cp, cpin, clin, cpln, cp_rev, cpin_rev, clin_rev, cpln_rev
% Output variables: mot_half R combo_proc input_wr_proc d_proc
% Called functions: form_combo_wrench, rec_mot, input_wr_compose, react_wr_5_compose
%                   rate_cp, rate_cpin, rate_clin, rate_cpln1, rate_cpln2
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev
global wrench_proc combo_dup_idx

global pts max_d pts_rev max_d_rev

% This allows the function to be used for both the baseline analysis and optimization routine
if strcmp(set,'original')==1
    set_cp=cp; set_cpin=cpin; set_clin=clin; set_cpln=cpln; set_cpln_prop=cpln_prop;
    set_pts=pts; set_max_d=max_d;
elseif strcmp(set,'revised')==1
    set_cp=cp_rev; set_cpin=cpin_rev; set_clin=clin_rev; 
    set_cpln=cpln_rev; set_cpln_prop=cpln_prop_rev;
    set_pts=pts_rev; set_max_d=max_d_rev;
end

% Initialize variables
mot_hold=[];m=1;
Rcp_pos=[];Rcp_neg=[];Rcpin=[];Rclin_pos=[];Rclin_neg=[]; Rcpln_pos=[];Rcpln_neg=[];
combo_dup_idx=zeros(size(combo,1),1);

if dispbar==1
    prog_bar=waitbar(0,'Base Calculation progress'); % Display progress bar
end

for i = 1:size(combo,1)
    
    % Update progress bar
    if dispbar==1
        if size(combo,1)<=1000
            waitbar(i/size(combo,1),prog_bar);
        else
            if mod(i,50)==0
            waitbar(i/size(combo,1),prog_bar);
            end
        end
    end
    
    % Compose pivot wrench matrix
    [pivot_wr]=form_combo_wrench(i,combo, wr_all);      
    rank_check = rank(pivot_wr); % Calculate the number of linearly independent wrench in the set
    
        if rank_check==5 % Proceed if the wrench is a 5-system
        
        % Solve the reciprocal motion
        [mot]=rec_mot(pivot_wr);

        % Check for duplicate motion (skip when mot_hold empty: MATLAB requires same cols for 'rows')
        if isempty(mot_hold)
            ismbr = 0;
            idx = 0;
        else
            [ismbr idx]=ismember(mot,mot_hold,'rows');
        end
        if ismbr==0
            mot_hold=[mot_hold;mot];
        else
            combo_dup_idx(i)=idx; % Record the motion index to which the motion is a duplicate
            continue
        end
        
        % Compose input wrench
        [input_wr d]=input_wr_compose(mot,set_pts,set_max_d);      

        % Set up matrix of constraining wrench from pivot constraints (rho as origin)        
        [react_wr_5]=react_wr_5_compose(combo(i,:),mot(7:9)',set);
        
        % Calculate reaction value for each CP (reaction wrenches are calculated with these functions)
        for j = 1:no_cp
            [Rcp_pos(m,j) Rcp_neg(m,j)]=rate_cp(mot,react_wr_5, input_wr, set_cp(j,:));
        end

        % Calculate resistance value for each CPIN
        for j = 1:no_cpin
            [Rcpin(m,j)]=rate_cpin(mot,react_wr_5,input_wr,set_cpin(j,:));
        end

        % Calculate resistance value for each CLIN
        for j = 1:no_clin
            [Rclin_pos(m,j) Rclin_neg(m,j)]=rate_clin(mot,react_wr_5,input_wr,set_clin(j,:));
        end

        % Calculate resistance value for each CPLN
        for j = 1:no_cpln
            if set_cpln(j,7)==1
                [Rcpln_pos(m,j) Rcpln_neg(m,j)]=rate_cpln1(mot,react_wr_5, input_wr,set_cpln(j,:),set_cpln_prop(j,:));
            elseif set_cpln(j,7)==2
                [Rcpln_pos(m,j) Rcpln_neg(m,j)]=rate_cpln2(mot,react_wr_5, input_wr,set_cpln(j,:),set_cpln_prop(j,:));
            end
        end

        d_proc(m,1)=d; % Collect the calculated moment arms
        combo_proc(m,:)=[i, combo(i,:)]; % Collect processed combinations
        wrench_proc{m}=pivot_wr; % Collect processed pivot wrenches
        input_wr_proc{m}=input_wr; % Collect input wrenches
        
        m=m+1; % Advance rating matrix row index 
    else
        continue
    end
    
end

mot_half=mot_hold; % Grab the evaluated motion set


Rcp=[Rcp_pos;Rcp_neg]; % Merge resistance value for fwd and rev motion
Rcpin=[Rcpin;Rcpin]; % Resistance values for fwd and rev motion is the same for cpin
Rclin=[Rclin_pos;Rclin_neg]; % Merge resistance value for fwd and rev motion
Rcpln=[Rcpln_pos;Rcpln_neg]; % Merge resistance value for fwd and rev motion

R=[Rcp Rcpin Rclin Rcpln]; % Merge all ratings across different constraints

if dispbar==1
    close(prog_bar); %close the progress bar
end

