% Main processor for constraint reduction
% filename: optim_main_red.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

clc;fprintf('Calculating optimization...\n');

% Initialize variables
WTR_optim_all=[];MRR_optim_all=[];MTR_optim_all=[]; del_idx=[];

% Create combination scheme, especially when removing more than one constraints at a time
cp_del_comb=nchoosek(1:total_cp,no_red);

prog_bar=waitbar(0,'Optimization iteration progress'); % display progress bar

for a=1:size(cp_del_comb,1)
    
    % Update progress bar
    if size(cp_del_comb,1)<=1000
        waitbar(a/size(cp_del_comb,1),prog_bar);
    else
        if mod(a,50)==0
        waitbar(a/size(cp_del_comb,1),prog_bar);
        end
    end
    
    cp_del_idx=cp_del_comb(a,:); %This is the cp that needs to be removed
    
    %Find combo that contains cp_del_idx
    del_idx=[];
    for n=1:length(cp_del_idx)
        [row_idx, dum1, dum2]=find(combo==cp_del_idx(n)); 
        del_idx=[del_idx;row_idx];
    end
    del_idx=unique(del_idx); %This is the index of combo that contains cp_del_idx

    combo_red_idx=setdiff([1:size(combo,1)]',del_idx); %This is the combo index that needs to be kept    
    dup_idx=combo_dup_idx(combo_red_idx); 
    dup_idx=unique(dup_idx);
    %dup_idx identifies the motion in mot_all_org that is a duplicate of the combo index that needs to be kept and therefore must not be removed
    dup_idx(1)=[]; %remove the zero that occurs on the first element, non 5-rank combo

    %Find combo_nondup that contains cp_del_idx and mark these to remove
    del_idx_all=[];    
    for n=1:length(cp_del_idx)
        [row_idx, dum1, dum2]=find(combo_proc_org(:,2:6)==cp_del_idx(n));
        del_idx_all=[del_idx_all;row_idx];
    end 
    %del_idx_all is the motion index that contain removed cp,
    del_idx_all=unique(del_idx_all);
    % but then the ones that must be kept (dup_idx) must be subtracted from the set
    del_idx_nondup=setdiff(del_idx_all,dup_idx);
    
    remain_idx=setdiff([1:no_mot_half]',del_idx_nondup);
    remain_idx_full=[remain_idx ;remain_idx+no_mot_half];
    
    combo_proc_red=combo_proc_org(remain_idx,2:6);
    Ri_red=Ri(remain_idx_full,:); 
    Ri_red(:,cp_del_idx)=[]; %delete column for deleted cp
    mot_all_red=mot_all_org(remain_idx_full,:);
    
    [mot_all_red_uniq uniq_idx]=unique(mot_all_red,'rows');
    Ri_red_uniq=Ri_red(uniq_idx,:);

    % Calculate rating after constraint reduction
    [Rating_all_rev WTR_idx_rev free_mot_rev free_mot_idx_rev best_cp_rev...
        ]=rating(Ri_red_uniq, mot_all_red_uniq);
    WTR_optim_all(a)=Rating_all_rev(1);
    MRR_optim_all(a)=Rating_all_rev(2);
    MTR_optim_all(a)=Rating_all_rev(3);    
end

TOR_optim_all=MTR_optim_all./MRR_optim_all;
close(prog_bar); %close the progress bar



% t is constraint removal index
t=1:size(cp_del_comb,1);

% Calculate rating change
WTR_optim_chg=(WTR_optim_all-Rating_all_org(1))./Rating_all_org(1).*100;
MRR_optim_chg=(MRR_optim_all-Rating_all_org(2))./Rating_all_org(2).*100;
MTR_optim_chg=(MTR_optim_all-Rating_all_org(3))./Rating_all_org(3).*100;
TOR_optim_chg=(TOR_optim_all-Rating_all_org(4))./Rating_all_org(4).*100;

% Plot constraint reduction 
f2=figure('Position',[100,300,640,480]);
title('Rating Change (%) Due to Constraint Reduction');
subplot(2,2,1);plot(t,WTR_optim_chg,'LineWidth',1.25);ylabel('WTR Change (%)');xlabel('Constraint Removal Index');grid on;
subplot(2,2,2);plot(t,MRR_optim_chg,'LineWidth',1.25);ylabel('MRR Change (%)');xlabel('Constraint Removal Index');grid on;
subplot(2,2,3);plot(t,MTR_optim_chg,'LineWidth',1.25);ylabel('MTR Change (%)');xlabel('Constraint Removal Index');grid on;
subplot(2,2,4);plot(t,TOR_optim_chg,'LineWidth',1.25);ylabel('TOR Change (%)');xlabel('Constraint Removal Index');grid on;

% Identify constraint removal combination that yield maximum TOR increase
[max_tor_increase b]=max(TOR_optim_chg)
cp_del_comb(b,:)
ratings_at_TOR_increase=[WTR_optim_all(b) MRR_optim_all(b) MTR_optim_all(b)]

% Automatically save the figures
saveas(f2,inputfile,'fig')
saveas(f2,inputfile,'eps')


