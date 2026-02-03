% Optimization main program for constraint modification
% filename: optim_main_rev.m
% Called functions: optim_rev_mot
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global combo_proc_orig wrench_proc 
global grp_members grp_rev_type grp_srch_spc cp_rev_all
global combo_dup_idx_org remain_idx combo

% Initialize variables for rating collection
Rating_all_rev_optim=[];WTR_optim_all=[];MRR_optim_all=[];MTR_optim_all=[]; 
tot_i=0; %counters for each for loop

clc
fprintf('Calculating optimization...\n')

% Check for empty optimization variables in input file
if size(grp_members,1)==0
    disp('No variable constraints are specified. Optimization terminated');
    return
end

% Load input file for constraints to be modified
[dummy3 dummy4 cp_rev_all]=find(grp_members');

%Find combo that contains cp_rev_all
del_idx=[];
for n=1:length(cp_rev_all)
    [row_idx, dum1, dum2]=find(combo==cp_rev_all(n)); 
    del_idx=[del_idx;row_idx];
end
del_idx=unique(del_idx); %This is the index of combo that contains cp_rev_all
    
combo_red_idx=setdiff([1:size(combo,1)]',del_idx); %This is the combo index that needs to be kept    
dup_idx=combo_dup_idx_org(combo_red_idx); %dup_idx is based on mot_half, or combo_proc, not combo
dup_idx=unique(dup_idx);
%dup_idx identifies the motion in mot_all_org that is a duplicate of the combo index that needs to be kept and therefore must not be removed
dup_idx(1)=[]; %remove the zero that occurs on the first element, non 5-rank combo
    
%Find combo_nondup that contains cp_rev_all and mark these to remove
del_idx_all=[];    
for n=1:length(cp_rev_all)
    [row_idx, dum1, dum2]=find(combo_proc_org(:,2:6)==cp_rev_all(n));
    del_idx_all=[del_idx_all;row_idx];
end 
del_idx_all=unique(del_idx_all);
%del_idx_all is the motion index that contain removed cp, but then
%the ones that must be kept (dup_idx) must be subtracted from the set
del_idx_nondup=setdiff(del_idx_all,dup_idx);

remain_idx=setdiff([1:no_mot_half]',del_idx_nondup);
remain_idx_full=[remain_idx ;remain_idx+no_mot_half];

combo_proc_optimbase=combo_proc_org(remain_idx,2:6);
% input_wr_proc_optimbase=input_wr_proc_org(remain_idx);
% d_proc_optimbase=d_proc_org(remain_idx);
mot_half_optimbase=mot_half_org(remain_idx,:);
mot_all_optimbase=mot_all_org(remain_idx_full,:);
Ri_optimbase=Ri(remain_idx_full,:); 

combo_new=combo(del_idx,:); %Identify original combo that will need re-creation of motion
 
% create mapping for x depending on the dimension for each variable
% the rows of x_map refer to the indices of x to grab
% x is a multi-dimension index for the optim parameter. It's dimension is
% the same size as the number of cp being optimized
% Refer to the use of x_map in optim_rev.m
row=1;
x_map=zeros(size(grp_rev_type,1),2);
for i=1:size(grp_rev_type,1)
    if grp_rev_type(i)==4 || grp_rev_type(i) ==6 || grp_rev_type(i) ==9
        %dim=2
        x_map(i,:)=[row row+1];
        row=row+2;
    else
        %dim=1
        x_map(i,:)=[row 0];
        row=row+1;
    end
end

%calc number of dimension in optimization search
no_dim=row-1;

tot_it=(no_step+1)^no_dim; %total iteration is # of variable * no_step

% Start optimization factorial search here (allow up to 5D search)

if no_dim==1
    
    ai=1:no_step+1; % ai is the index for search increments
    a=((ai-1)/no_step*2)-1; % a is the normalized search units from -1 to 1
    prog_bar=waitbar(0,'Optimization iteration'); % display progress bar

    for ai=1:no_step+1
        
        waitbar(ai/tot_it,prog_bar);  % Updates progress bar
        x=[a(ai)]; % Assign the current variable value parameter x
        % Call the optim_rev to conduct analysis for current increment
        [Rating_all_rev Ri_new_uniq mot_all_new_uniq]=optim_rev(x,x_map,...
                            Ri_optimbase,mot_all_optimbase,mot_half_optimbase, combo_proc_optimbase,combo_new);
        % Collect rating response values
        WTR_optim_all(ai)=Rating_all_rev(1);
        MRR_optim_all(ai)=Rating_all_rev(2);
        MTR_optim_all(ai)=Rating_all_rev(3);
          
    end
    
    close(prog_bar);
    
elseif no_dim==2
    
    ai=1:no_step+1;
    a=((ai-1)/no_step*2)-1;
    bi=1:no_step+1;
    b=((bi-1)/no_step*2)-1;
    
    prog_bar=waitbar(0,'Optimization iteration'); % display progress bar

    for ai=1:no_step+1
        
        for bi=1:no_step+1

            x=[a(ai);b(bi)];             
            
            waitbar(ai*bi/tot_it,prog_bar);
            [Rating_all_rev Ri_new_uniq mot_all_new_uniq]=optim_rev(x,x_map,...
                            Ri_optimbase,mot_all_optimbase,mot_half_optimbase, combo_proc_optimbase,combo_new);
            WTR_optim_all(ai,bi)=Rating_all_rev(1);
            MRR_optim_all(ai,bi)=Rating_all_rev(2);
            MTR_optim_all(ai,bi)=Rating_all_rev(3);  
                        
        end
        
    end
    
    close(prog_bar);
    
elseif no_dim==3
    
    ai=1:no_step+1;
    a=((ai-1)/no_step*2)-1;
    bi=1:no_step+1;
    b=((bi-1)/no_step*2)-1;
    ci=1:no_step+1;
    c=((ci-1)/no_step*2)-1;
    
    for ai=1:no_step+1
        
        for bi=1:no_step+1
            
            for ci=1:no_step+1
                
                clc
                fprintf('Calculating optimization iteration...\n');
                fprintf('Variable 1 iteration (%i/%i)\n',ai,no_step+1);
                fprintf('Variable 2 iteration (%i/%i)\n',bi,no_step+1);
                fprintf('Variable 3 iteration (%i/%i)\n',ci,no_step+1);
                
                x=[a(ai);b(bi);c(ci)]; 
                [Rating_all_rev Ri_new_uniq mot_all_new_uniq]=optim_rev(x,x_map,...
                            Ri_optimbase,mot_all_optimbase,mot_half_optimbase, combo_proc_optimbase,combo_new);
                WTR_optim_all(ai,bi,ci)=Rating_all_rev(1);
                MRR_optim_all(ai,bi,ci)=Rating_all_rev(2);
                MTR_optim_all(ai,bi,ci)=Rating_all_rev(3);
            
            end
            
        end
        
    end
        
elseif no_dim==4
    
    ai=1:no_step+1;
    a=((ai-1)/no_step*2)-1;
    bi=1:no_step+1;
    b=((bi-1)/no_step*2)-1;
    ci=1:no_step+1;
    c=((ci-1)/no_step*2)-1;
    di=1:no_step+1;
    d=((di-1)/no_step*2)-1;

    for ai=1:no_step+1

        for bi=1:no_step+1
            
            for ci=1:no_step+1
                
                for di=1:no_step+1

                    clc
                    fprintf('Calculating optimization iteration...\n');
                    fprintf('Variable 1 iteration (%i/%i)\n',ai,no_step+1);
                    fprintf('Variable 2 iteration (%i/%i)\n',bi,no_step+1);
                    fprintf('Variable 3 iteration (%i/%i)\n',ci,no_step+1);
                    fprintf('Variable 4 iteration (%i/%i)\n',di,no_step+1);
                    
                    x=[a(ai);b(bi);c(ci);d(di)]; 
                    [Rating_all_rev Ri_new_uniq mot_all_new_uniq]=optim_rev(x,x_map,...
                                Ri_optimbase,mot_all_optimbase,mot_half_optimbase, combo_proc_optimbase,combo_new);
                    WTR_optim_all(ai,bi,ci,di)=Rating_all_rev(1);
                    MRR_optim_all(ai,bi,ci,di)=Rating_all_rev(2);
                    MTR_optim_all(ai,bi,ci,di)=Rating_all_rev(3);
                
                end
                
            end
            
        end
        
    end
    
elseif no_dim==5

    ai=1:no_step+1;
    a=((ai-1)/no_step*2)-1;
    bi=1:no_step+1;
    b=((bi-1)/no_step*2)-1;
    ci=1:no_step+1;
    c=((ci-1)/no_step*2)-1;
    di=1:no_step+1;
    d=((di-1)/no_step*2)-1;
    ei=1:no_step+1;
    e=((ei-1)/no_step*2)-1;

    for ai=1:no_step+1
        
        for bi=1:no_step+1
            
            for ci=1:no_step+1
                
                for di=1:no_step+1
                    
                    for ei=1:no_step+1
                        
                        clc
                        fprintf('Calculating optimization iteration...\n');
                        fprintf('Variable 1 iteration (%i/%i)\n',ai,no_step+1);
                        fprintf('Variable 2 iteration (%i/%i)\n',bi,no_step+1);
                        fprintf('Variable 3 iteration (%i/%i)\n',ci,no_step+1);
                        fprintf('Variable 4 iteration (%i/%i)\n',di,no_step+1);
                        fprintf('Variable 5 iteration (%i/%i)\n',ei,no_step+1);
                    
                        x=[a(ai);b(bi);c(ci);d(di);e(ei)]; 
                        [Rating_all_rev Ri_new_uniq mot_all_new_uniq]=optim_rev(x,x_map,...
                                Ri_optimbase,mot_all_optimbase,mot_half_optimbase, combo_proc_optimbase,combo_new);
                        WTR_optim_all(ai,bi,ci,di,ei)=Rating_all_rev(1);
                        MRR_optim_all(ai,bi,ci,di,ei)=Rating_all_rev(2);
                        MTR_optim_all(ai,bi,ci,di,ei)=Rating_all_rev(3);
                    
                    end
                    
                end
                
            end
            
        end
        
    end
    
elseif no_dim>5
    disp('Total dimension to optimize exceeds limit');
    return                   
end

TOR_optim_all=MTR_optim_all./MRR_optim_all;

WTR_optim_chg=(WTR_optim_all-Rating_all_org(1))./Rating_all_org(1).*100;
MRR_optim_chg=(MRR_optim_all-Rating_all_org(2))./Rating_all_org(2).*100;
MTR_optim_chg=(MTR_optim_all-Rating_all_org(3))./Rating_all_org(3).*100;
TOR_optim_chg=(TOR_optim_all-Rating_all_org(4))./Rating_all_org(4).*100;



