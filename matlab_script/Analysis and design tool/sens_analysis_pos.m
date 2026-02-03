% Sensitivity analysis by perturbing constraint location
% filename: sens_analysis_pos.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% This procedure uses optim_main_rev plane search space to explore position perturbation

pert_dist=input('How much position perturbation? (same units as input file) ');

for idx=1:total_cp
    
    % Set up plane search space
    grp_members=idx;
    grp_rev_type=4;   
    if idx<=no_cp
        k=idx;
        cp_ctr=cp(k,1:3);cp_normal=cp(k,4:6);
    elseif idx>no_cp && idx<=no_cp+no_cpin
        k=idx-no_cp;
        cp_ctr=cpin(k,1:3);cp_normal=cpin(k,4:6);
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin
        k=idx-(no_cp+no_cpin);
        cp_ctr=clin(k,1:3);cp_normal=clin(k,7:9);
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln
        k=idx-(no_cp+no_cpin+no_clin);
        cp_ctr=cpln(k,1:3);cp_normal=cpln(k,4:6);
    end
    xy=null(cp_normal);
    grp_srch_spc=[cp_ctr xy(:,1)' pert_dist xy(:,2)' pert_dist];
    no_step=2;    
    
    optim_main_rev
    
    % Collect rating change
    SAP_WTR(idx,:,:)=WTR_optim_chg;
    SAP_MRR(idx,:,:)=MRR_optim_chg;
    SAP_MTR(idx,:,:)=MTR_optim_chg;
    SAP_TOR(idx,:,:)=TOR_optim_chg;
    
end

% Optional plots
k=input('Plot which constraint''s perturbation? (enter 0 to exit) ');
while k~=0 & k<=total_cp        
    WTR=zeros(3,3);MRR=zeros(3,3);MTR=zeros(3,3);TOR=zeros(3,3);
    WTR(:,:)=SAP_WTR(k,:,:);MRR(:,:)=SAP_MRR(k,:,:);MTR(:,:)=SAP_MTR(k,:,:);TOR(:,:)=SAP_TOR(k,:,:);
    optim_postproc(no_step,no_dim, WTR,MRR,MTR,TOR,Rating_all_org,'sens_plot');
    k=input('Plot which constraint''s perturbation? (enter 0 to exit) ');    
end

for m=1:total_cp
    WTR=zeros(3,3);
    WTR(:,:)=SAP_WTR(m,:,:);
    SAP_WTR_min(m)=min(min(WTR));
end
