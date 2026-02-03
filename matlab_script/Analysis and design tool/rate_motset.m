function [R]=rate_motset(combo_set,mot_half_reduc,cp_set,whatkind_cp)
% Rate a specified set of constraints to resist a specified set of motion
% filename: rate_motset.m
% Input variables: combo_set,mot_half_reduc,cp_set,whatkind_cp
% Output variables: R
% Called functions: input_wr_compose, react_wr_5_compose
%                   rate_cp, rate_cpin, rate_clin, rate_cpln1, rate_cpln2
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global no_cp_rev no_cpin_rev no_clin_rev no_cpln_rev
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev pts_rev max_d_rev
global combo_dup_idx_org remain_idx combo
m=1;

Rcp_pos=[];Rcp_neg=[];Rcpin=[];Rclin_pos=[];Rclin_neg=[];
Rcpln_pos=[];Rcpln_neg=[];
Rpos=[];Rneg=[];

if strcmp(whatkind_cp,'additional')==1
    %modify using the appended cp indexes
    no_cp=no_cp_rev;
    no_cpin=no_cpin_rev;
    no_clin=no_clin_rev;
    no_cpln=no_cpln_rev;
end

%motset is half_mot format
%cp_set is column format
% cnt1=1;cnt2=1;cnt3=1;cnt4=1;

for i=1:size(mot_half_reduc,1)

    % Note that d might change once the cp set is revised, but it's too costly to recalculate d for all rated cp and mot
    
    mot=mot_half_reduc(i,:);
    [input_wr dmy1]=input_wr_compose(mot,pts_rev,max_d_rev);  
    [react_wr_5]=react_wr_5_compose(combo_set(i,:),mot(7:9)',whatkind_cp);
    
    for j=1:length(cp_set);
    
        % The procedure below is implemented to handle cases when modified constraints
        % belonging to the pivot wrench changes the pivot wrench matrix ranks
        cp_eval=cp_set(j);        
        cp_eval_idx=find(combo_set(i,:)==cp_eval);        
        pivot_wr=react_wr_5;    
        if isempty(cp_eval_idx)==0
            pivot_wr(cp_eval_idx,:)=[]; %delete the row
        end
        % if want to increase accuracy, insert a linear dependence
        % eliminator here, and get rid of ther pitvot_wr rank check
        swap=pivot_wr;        
        while rank(swap)>5
            swap(6,:)=[];
        end                
        alt_idx=find(combo_dup_idx_org==remain_idx(i));        
        if rank(pivot_wr)<5
            for s=1:size(alt_idx,1)
                [swap]=react_wr_5_compose(combo(alt_idx(s),:),mot(7:9)',whatkind_cp);   
                if rank(swap)==5
                    break
                end
            end
        end        
        pivot_wr=swap;
        
        % Rate the constraint quality to resist motion
        if cp_eval<=no_cp
            k=cp_eval;
            [Rpos(m,j) Rneg(m,j)]=rate_cp(mot,pivot_wr,input_wr, cp_rev(k,:));
        elseif cp_eval>no_cp && cp_eval<=no_cp+no_cpin
            k=cp_eval-no_cp;
            [Rpos(m,j)]=rate_cpin(mot,pivot_wr,input_wr,cpin_rev(k,:));
            Rneg(m,j)=Rpos(m,j);
        elseif cp_eval>no_cp+no_cpin && cp_eval<=no_cp+no_cpin+no_clin
            k=cp_eval-(no_cp+no_cpin);
            [Rpos(m,j) Rneg(m,j)]=rate_clin(mot,pivot_wr,input_wr,clin_rev(k,:));
        elseif cp_eval>no_cp+no_cpin+no_clin && cp_eval<=no_cp+no_cpin+no_clin+no_cpln
            k=cp_eval-(no_cp+no_cpin+no_clin);
            if cpln_rev(k,7)==1
                [Rpos(m,j) Rneg(m,j)]=rate_cpln1(mot,pivot_wr, input_wr,cpln_rev(k,:),cpln_prop_rev(k,:));
            elseif cpln_rev(k,7)==2
                [Rpos(m,j) Rneg(m,j)]=rate_cpln2(mot,pivot_wr, input_wr,cpln_rev(k,:),cpln_prop_rev(k,:));
            end
        end
        
        % Just in case the procedure above did not handle the rank problem
        if rank(pivot_wr)~=5
            Rpos(m,j)=inf; Rneg(m,j)=inf;
        end        
    end    
    m=m+1; %advance rating matrix row index    
end

% Merge all ratings
R=[Rpos;Rneg];

