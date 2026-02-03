function resize_rectpln_srch(x_grp,cp_rev_in_group, pln_size_srch)
% Resize rectangular plane constraints 
% filename: resize_rectpln_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global cpln_prop_rev

% Adjustment because parameter x ranges from -1 to 1
pln_length=pln_size_srch(1)+(x_grp(1)+1)/2*(pln_size_srch(2)-pln_size_srch(1));
pln_width=pln_size_srch(3)+(x_grp(2)+1)/2*(pln_size_srch(4)-pln_size_srch(3));

% Apply this to all rectangular plane constraints
for i=1:length(cp_rev_in_group)    
    idx=cp_rev_in_group(i);    
    if idx<=no_cp
        disp('Plane size search is not applicable to point constraints');
        return        
    elseif idx>no_cp && idx<=no_cp+no_cpin    
        disp('Plane size search is not applicable to pin constraints');
        return        
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin        
        disp('Plane size search is not applicable to line constraints');
        return        
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln        
        k=idx-(no_cp+no_cpin+no_clin);
        cpln_prop_rev(k,4)=pln_length;
        cpln_prop_rev(k,8)=pln_width;                
    end
end
