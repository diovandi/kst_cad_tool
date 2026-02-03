function []=orient1d_srch(x_grp,cp_rev_in_group, dir1d_srch)
% Reorient constraints about 1 axis
% filename: orient1d_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev 

% dir1d_srch format:
% [local_rot_axis(3), angle,zeros]
% local_rot_axis is treated as the local x axis 
% constraint normal is local_z axis
% make sure follows right hand rule 

angle=x_grp*dir1d_srch(4); 

% Specify dn, orientation of normal vector relative to local frame for rotation around local x
dn=[0; -sind(angle);  cosd(angle)];
% Note that non-perturbed (phi=0) --> dn=[0 0 1]
dn=dn/norm(dn);

local_x=dir1d_srch(1:3)';
        
for i=1:length(cp_rev_in_group)    
    idx=cp_rev_in_group(i);    
    if idx<=no_cp        
        k=idx;        
        %extract cp location and orientation
        %locate local x and y frame
        local_z=cp_rev(k,4:6)';
        local_y=cross(local_z,local_x);
        rot=[local_x local_y local_z]; % Transform from local to global frame
        new_normal=rot*dn;
        cp_rev(k,4:6)=new_normal./norm(new_normal);        
    elseif idx>no_cp && idx<=no_cp+no_cpin    
        k=idx-no_cp;        
        local_z=cpin_rev(k,4:6)';  
        local_y=cross(local_z,local_x);
        rot=[local_x local_y local_z];
        new_normal=rot*dn;
        cpin_rev(k,4:6)=new_normal./norm(new_normal);        
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin        
        k=idx-(no_cp+no_cpin);        
        local_z=clin_rev(k,7:9)';              
        local_y=cross(local_z,local_x);
        rot=[local_x local_y local_z];
        new_normal=rot*dn;
        clin_rev(k,7:9)=new_normal./norm(new_normal);        
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln        
        k=idx-(no_cp+no_cpin+no_clin);        
        local_z=cpln_rev(k,4:6)';              
        local_y=cross(local_z,local_x);
        rot=[local_x local_y local_z];
        new_normal=rot*dn;
        cpln_rev(k,4:6)=new_normal./norm(new_normal);        
    end    
end

