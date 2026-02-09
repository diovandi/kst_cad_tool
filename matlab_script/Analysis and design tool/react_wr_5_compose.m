function [react_wr_5]=react_wr_5_compose(comb,rho,set)
% Compose constraining wrench from pivot wrenches for equilibrium equation
% filename: react_wr_5_compose.m
% Input variables: comb,rho,set
% Output variables: react_wr_5
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev

% This allows the function to be used for both the baseline analysis and optimization routine
if strcmp(set,'original')==1
    set_cp=cp; set_cpin=cpin; set_clin=clin; set_cpln=cpln; set_cpln_prop=cpln_prop;
elseif strcmp(set,'revised')==1 || strcmp(set,'additional')==1
    set_cp=cp_rev; set_cpin=cpin_rev; set_clin=clin_rev; 
    set_cpln=cpln_rev; set_cpln_prop=cpln_prop_rev;
end

c=1; % Row index

% The following procedure is similar to the one in cp_to_wrench function

for a=1:nnz(comb) % Do this for each constraint in the pivot combination
    
    idx=comb(a);
        
    if idx<=no_cp % Point constraint
        % Use row vectors for cross() so result is 1x3 (Octave/ML compatible)
        b=idx;
        cp_pos=(set_cp(b,1:3)'-rho)';
        react_wr_5(c,:)=[set_cp(b,4:6),cross(cp_pos,set_cp(b,4:6))];
        c=c+1;

    elseif idx>no_cp && idx<=no_cp+no_cpin % Pin constraint
        % Use row vectors for cross() so result is 1x3 (Octave/ML compatible)
        b=idx-no_cp;
        cpin_pos=(set_cpin(b,1:3)'-rho)';  % 1x3 row for cross
        axes=null(set_cpin(b,4:6));
        om_axis1=axes(:,1)';
        om_axis2=axes(:,2)';
        mu_axis1=cross(cpin_pos,om_axis1);
        mu_axis2=cross(cpin_pos,om_axis2);
        react_wr_5(c:c+1,:)=[om_axis1 mu_axis1;om_axis2 mu_axis2];
        c=c+2;

    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin % Line constraint

        b=idx-(no_cp+no_cpin);
        clin_pos=set_clin(b,1:3)-rho';
        om_axis1=set_clin(b,7:9); %zero pitch
        om_axis2=[0 0 0]; %inf pitch
        mu_axis1=cross(clin_pos,om_axis1); %zero pitch
        mu_axis2=cross(set_clin(b,4:6),set_clin(b,7:9)); %inf pitch
        react_wr_5(c:c+1,:)=[om_axis1 mu_axis1;om_axis2 mu_axis2];
        c=c+2;

    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln % Plane constraint

        b=idx-(no_cp+no_cpin+no_clin);
        cpln_pos=set_cpln(b,1:3)-rho';
        axes=null(set_cpln(b,4:6));
        om_axis1=set_cpln(b,4:6); %zero pitch
        om_axis2=[0 0 0]; %inf pitch
        om_axis3=[0 0 0]; %inf pitch
        mu_axis1=cross(cpln_pos,om_axis1); %zero pitch
        mu_axis2=axes(:,1)';
        mu_axis3=axes(:,2)';
        react_wr_5(c:c+2,:)=[om_axis1 mu_axis1;om_axis2 mu_axis2;om_axis3 mu_axis3];
        c=c+3;
                
    end

end

