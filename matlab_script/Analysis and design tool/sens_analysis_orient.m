% Sensitivity analysis by perturbing constraint orientation
% filename:sens_analysis_orient.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% This procedure uses optim_main_rev orient2d search space to explore orientation perturbation

pert_angle=input('How much angle perturbation? (same units as input file) ');

for idx=1:total_cp
    
    % Set up orient2d search space
    grp_members=idx;
    grp_rev_type=6; 
    if idx<=no_cp
        k=idx;
        cp_normal=cp(k,4:6);
    elseif idx>no_cp && idx<=no_cp+no_cpin
        k=idx-no_cp;
        cp_normal=cpin(k,4:6);
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin
        k=idx-(no_cp+no_cpin);
        cp_normal=clin(k,7:9);
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln
        k=idx-(no_cp+no_cpin+no_clin);
        cp_normal=cpln(k,4:6);
    end    
    xy=null(cp_normal);
    grp_srch_spc=[xy(:,1)' xy(:,2)' pert_angle pert_angle];
    no_step=2;
    
    optim_main_rev
    
    % Collect rating change
    SAO_WTR(idx,:,:)=WTR_optim_chg;
    SAO_MRR(idx,:,:)=MRR_optim_chg;
    SAO_MTR(idx,:,:)=MTR_optim_chg;
    SAO_TOR(idx,:,:)=TOR_optim_chg;
    
end

% Optional plots
k=input('Plot which constraint''s perturbation? (enter 0 to exit) ');
while k~=0 & k<=total_cp        
    WTR=zeros(3,3);MRR=zeros(3,3);MTR=zeros(3,3);TOR=zeros(3,3);
    WTR(:,:)=SAO_WTR(k,:,:);MRR(:,:)=SAO_MRR(k,:,:);MTR(:,:)=SAO_MTR(k,:,:);TOR(:,:)=SAO_TOR(k,:,:);
    optim_postproc(no_step,no_dim, WTR,MRR,MTR,TOR,'sens_plot');
    k=input('Plot which constraint''s perturbation? (enter 0 to exit) ');    
end

for m=1:total_cp
    WTR=zeros(3,3);
    WTR(:,:)=SAO_WTR(m,:,:);
    SAO_WTR_min(m)=min(min(WTR));
end
