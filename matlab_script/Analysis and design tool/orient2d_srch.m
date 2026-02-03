function []=orient2d_srch(x_grp,cp_rev_in_group, dir2d_srch)
% Reorient constraints about 2 axis
% filename: orient2d_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev 

alpha=x_grp(1)*dir2d_srch(7);
beta=x_grp(2)*dir2d_srch(8);

% Specify dn, orientation of normal vector relative to local frame for 
% rotation around local_x and local_y
% constraint normal is local_z

% dir_srch format:
% [local_x_axis(3), local_y_axis(3), angle(x), angle(y)]
% make sure follows right hand rule 

dn=[sind(beta);  -sind(alpha);  cosd(alpha)*cosd(beta)];
% Note that non-perturbed (alpha=beta=0) --> dn=[0 0 1]
dn=dn/norm(dn);

local_x=dir2d_srch(1:3)';
local_y=dir2d_srch(4:6)';
        
for i=1:length(cp_rev_in_group)    
    idx=cp_rev_in_group(i);    
    if idx<=no_cp        
        k=idx;        
        %extract cp location and orientation
        %locate local x and y frame
        local_z=cp_rev(k,4:6)'; 
        rot=[local_x local_y local_z]; % Transform from local to global frame                
        new_normal=rot*dn;
        cp_rev(k,4:6)=new_normal./norm(new_normal);        
    elseif idx>no_cp && idx<=no_cp+no_cpin    
        k=idx-no_cp;        
        local_z=cpin_rev(k,4:6)';              
        rot=[local_x local_y local_z];                
        new_normal=rot*dn;
        cpin_rev(k,4:6)=new_normal./norm(new_normal);        
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin        
        k=idx-(no_cp+no_cpin);        
        local_z=clin_rev(k,7:9)';              
        rot=[local_x local_y local_z];        
        new_normal=rot*dn;
        clin_rev(k,7:9)=new_normal./norm(new_normal);        
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln        
        k=idx-(no_cp+no_cpin+no_clin);        
        local_z=cpln_rev(k,4:6)';              
        rot=[local_x local_y local_z];       
        new_normal=rot*dn;
        cpln_rev(k,4:6)=new_normal./norm(new_normal);        
    end    
end