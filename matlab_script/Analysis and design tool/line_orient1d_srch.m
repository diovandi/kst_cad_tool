function []=line_orient1d_srch(x_grp,cp_rev_in_group, lin_dir_srch)
% Reorient line constraints about 1 axis
% filename: line_orient1d_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global clin_rev

% dir1d_srch format:
% [local_rot_axis(3), angle,zeros]
% local_rot_axis is treated as the local x axis 

% original line direction clin_rev(k,4:6) is the local z axis
% Later the same case for clin_rev(k,7:9), the constraint normal

% make sure follows right hand rule 

angle=x_grp*lin_dir_srch(4); 

% Specify dn, orientation of normal vector relative to local frame for rotation around local x
dn=[0; -sind(angle); cosd(angle)];
% Note that non-perturbed (phi=0) --> dn=[0 0 1]
dn=dn/norm(dn);

local_x=lin_dir_srch(1:3)';

for i=1:length(cp_rev_in_group)    
    idx=cp_rev_in_group(i);    
    if idx<=no_cp        
        disp('Line orientation search is not applicable to point constraints');
        return        
    elseif idx>no_cp && idx<=no_cp+no_cpin    
        disp('Line orientation search is not applicable to pin constraints');
        return        
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin        
        k=idx-(no_cp+no_cpin);
        % Rotate the line constraint 
        local_z=clin_rev(k,4:6)';              
        local_y=cross(local_z,local_x);
        rot=[local_x local_y local_z];
        new_linedir=rot*dn;
        clin_rev(k,4:6)=new_linedir./norm(new_linedir);        
        % Rotate the line constraint normal also
        local_z=clin_rev(k,7:9)';              
        local_y=cross(local_z,local_x);
        rot=[local_x local_y local_z];
        new_line_normal=rot*dn;
        clin_rev(k,7:9)=new_line_normal./norm(new_line_normal);        
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln        
        disp('Line orientation search is not applicable to plane constraints');
        return        
    end
end