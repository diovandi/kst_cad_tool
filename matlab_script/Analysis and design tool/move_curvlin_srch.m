function []=move_curvlin_srch(x_grp,cp_rev_in_group,circlin_srch)
% Move constraints in the curved line search space
% filename: move_curvlin_srch.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev 

%curvlin_srch format is relative, not absolute, basically it rotates the
%position using the axis defined.
%[center_coord(3), rotation_axis_dir(3), angle]
%starting point x axis is defined by 

angle=x_grp*circlin_srch(7); 
circlin_srch(4:6)=circlin_srch(4:6)./norm(circlin_srch(4:6));
local_orig=circlin_srch(1:3)'; % Location of the rotation axis center

% For loop to apply modification to all constraints in the group
for i=1:length(cp_rev_in_group)
    
    idx=cp_rev_in_group(i);
    
    % Find local_x - the vector from the rotation axis to the constraint location    
    if idx<=no_cp
        k=idx;
        local_x=cp_rev(k,1:3)'-local_orig;
    elseif idx>no_cp && idx<=no_cp+no_cpin
        k=idx-no_cp;
        local_x=cpin_rev(k,1:3)'-local_orig;
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin
        k=idx-(no_cp+no_cpin);
        local_x=clin_rev(k,1:3)'-local_orig;
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln
        k=idx-(no_cp+no_cpin+no_clin);
        local_x=cpln_rev(k,1:3)'-local_orig;
    end
    
    % Rotation matrix
    rot_local=[ cosd(angle) -sind(angle)  	0;
                sind(angle) cosd(angle) 	0;
                0           0               1];
    
    % dp is the vector from rotation center to the new position
    dp=rot_local*local_x;    
    new_pos=local_orig+dp;
    
    % Apply this to each constraints depending on their type
    if idx<=no_cp
        k=idx;
        cp_rev(k,1:3)=new_pos';            
     elseif idx>no_cp && idx<=no_cp+no_cpin
        k=idx-no_cp;
        cpin_rev(k,1:3)=new_pos';
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin
        k=idx-(no_cp+no_cpin);
        clin_rev(k,1:3)=new_pos';
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln
        k=idx-(no_cp+no_cpin+no_clin);
        cpln_rev(k,1:3)=new_pos';
    end
    
end

    

