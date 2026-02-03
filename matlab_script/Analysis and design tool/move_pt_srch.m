function [cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev...
            ]=move_pt_srch(x,cp_rev_idx, pt_srch)
% Move constraints in the line search space
% filename: move_pt_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% WARNING: THIS IS PRELIMINARY CODE AND CONTAINS ERRORS

global no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev


for i=1:length(cp_rev_in_group)
    
    if cp_rev_idx(i)<=no_cp
        
        %Move cp_rev location to midpoint of line and then move it along
        %the line with multiplier x
        
        cp_rev(cp_rev_idx(i),1:3)=pt_srch(x,1:3);
        
    elseif cp_rev_idx(i)>no_cp && cp_rev_idx(i)<=no_cp+no_cpin
    
        cpin_rev(cp_rev_idx(i),1:3)=pt_srch(x,1:3);
        
    elseif cp_rev_idx(i)>no_cp+no_cpin && cp_rev_idx(i)<=no_cp+no_cpin+no_clin
      
        clin_rev(cp_rev_idx(i),1:3)=pt_srch(x,1:3);
        
    elseif cp_rev_idx(i)>no_cp+no_cpin+no_clin && cp_rev_idx(i)<=no_cp+no_cpin+no_clin+no_cpln

        cpln_rev(cp_rev_idx(i),1:3)=pt_srch(x,1:3);
        
    end
    
end

% use x as the index for going through the search space. In this case use
% grp_srch_spc with each row corresponding to each constraint.