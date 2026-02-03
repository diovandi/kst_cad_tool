function []=move_pln_srch(x_grp,cp_rev_in_group, pln_srch)
% Move constraints in the plane search space
% filename: move_pln_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev

pln_srch(4:6)=pln_srch(4:6)./norm(pln_srch(4:6));
pln_srch(8:10)=pln_srch(8:10)./norm(pln_srch(8:10));

%pln search format
% [ center (x,y,z), x-dir-search(x,y,z),x-dir one-way width,
% y-dir-search(x,y,z,),y-dir one-way width]

% The procedure here is very similar to line search space, but applied in 2D
% See comments on move_lin_srch

idx=cp_rev_in_group(1);

if idx<=no_cp

    k=idx;
    ctr_move=pln_srch(1:3)-cp_rev(k,1:3);

elseif idx>no_cp && idx<=no_cp+no_cpin

    k=idx-no_cp;
    ctr_move=pln_srch(1:3)-cpin_rev(k,1:3);

elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin

    k=idx-(no_cp+no_cpin);
    ctr_move=pln_srch(1:3)-clin_rev(k,1:3);

elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln

    k=idx-(no_cp+no_cpin+no_clin);
    ctr_move=pln_srch(1:3)-cpln_rev(k,1:3);

end

for i=1:length(cp_rev_in_group)

    idx=cp_rev_in_group(i);
    if idx==0, return, end
    
    if idx<=no_cp        
        %Move cp_rev location to midpoint of line and then move it along
        %the line with multiplier x
        k=idx;
        cp_rev(k,1:3)=cp_rev(k,1:3)+ctr_move+(x_grp(1)*pln_srch(7)).*pln_srch(4:6)+(x_grp(2)*pln_srch(11)).*pln_srch(8:10);        
    elseif idx>no_cp && idx<=no_cp+no_cpin    
        k=idx-no_cp;
        cpin_rev(k,1:3)=cpin_rev(k,1:3)+ctr_move+(x_grp(1)*pln_srch(7)).*pln_srch(4:6)+(x_grp(2)*pln_srch(11)).*pln_srch(8:10);        
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin        
        k=idx-(no_cp+no_cpin);
        clin_rev(k,1:3)=clin_rev(k,1:3)+ctr_move+(x_grp(1)*pln_srch(7)).*pln_srch(4:6)+(x_grp(2)*pln_srch(11)).*pln_srch(8:10);        
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln        
        k=idx-(no_cp+no_cpin+no_clin);
        cpln_rev(k,1:3)=cpln_rev(k,1:3)+ctr_move+(x_grp(1)*pln_srch(7)).*pln_srch(4:6)+(x_grp(2)*pln_srch(11)).*pln_srch(8:10);        
    end    
end

    

