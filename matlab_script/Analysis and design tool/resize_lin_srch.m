function resize_lin_srch(x_grp,cp_rev_in_group,lin_size_srch)
% Resize line constraints 
% filename: resize_lin_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global clin_rev

% Adjustments need to be made since parameter x is from -1 to 1
line_length=lin_size_srch(1)+((x_grp+1)/2)*(lin_size_srch(2)-lin_size_srch(1));

% Apply this to all line constraints in the group
for i=1:length(cp_rev_in_group)
    
    idx=cp_rev_in_group(i);
    
    if idx<=no_cp        
        disp('Line size search is not applicable to point constraints');
        return        
    elseif idx>no_cp && idx<=no_cp+no_cpin    
        disp('Line size search is not applicable to pin constraints');
        return        
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin        
        k=idx-(no_cp+no_cpin);
        clin_rev(k,10)=line_length;        
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln        
        disp('Line size search is not applicable to plane constraints');
        return        
    end    
end