function []=move_lin_srch(x_grp,cp_rev_in_group,lin_srch)
% Move constraints in the line search space
% filename: move_lin_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev 

% The line search space is defined for the first constraints only, the other constraints follow

% First find the relative position vector from the first constraints midpoint to the midpoint of line search space

idx=cp_rev_in_group(1);
lin_srch(4:6)=lin_srch(4:6)./norm(lin_srch(4:6));

if idx<=no_cp

    k=idx;
    ctr_move=lin_srch(1:3)-cp_rev(k,1:3);

elseif idx>no_cp && idx<=no_cp+no_cpin

    k=idx-no_cp;
    ctr_move=lin_srch(1:3)-cpin_rev(k,1:3);

elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin

    k=idx-(no_cp+no_cpin);
    ctr_move=lin_srch(1:3)-clin_rev(k,1:3);

elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln

    k=idx-(no_cp+no_cpin+no_clin);
    ctr_move=lin_srch(1:3)-cpln_rev(k,1:3);

end

% Move the constraints with ctr_move, then move in the same direction as the first constraints

for i=1:length(cp_rev_in_group)
    
    idx=cp_rev_in_group(i);
    if idx==0, return, end

    if idx<=no_cp

        k=idx;
        cp_rev(k,1:3)=cp_rev(k,1:3)+ctr_move+(x_grp*lin_srch(7)).*lin_srch(4:6);
            
     elseif idx>no_cp && idx<=no_cp+no_cpin

        k=idx-no_cp;
        cpin_rev(k,1:3)=cpin_rev(k,1:3)+ctr_move+(x_grp*lin_srch(7)).*lin_srch(4:6);

    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin

        k=idx-(no_cp+no_cpin);
        clin_rev(k,1:3)=clin_rev(k,1:3)+ctr_move+(x_grp*lin_srch(7)).*lin_srch(4:6);

    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln

        k=idx-(no_cp+no_cpin+no_clin);
        cpln_rev(k,1:3)=cpln_rev(k,1:3)+ctr_move+(x_grp*lin_srch(7)).*lin_srch(4:6);

    end
    
end

    

