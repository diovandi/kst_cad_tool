function [cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev...
            ]=orient_srch_cone(x,cp_rev_idx, dir_srch)
        
global no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev

th=x(1);
phi=x(2);
% orientation of normal vector relative to local frame
% non-perturbed is phi=0 --> [0 0 1]
dn=[sind(phi)*cosd(th);sind(phi)*sind(th);cosd(phi)];
dn=dn/norm(dn);
        
for i=1:size(cp_rev_idx,1)
    
    idx=cp_rev_idx(i);
    
    if idx<=no_cp
        
        k=idx;
        
        %extract cp location and orientation
        %locate local x and y frame
        local_orig=cp_rev(k,1:3)';
        local_z=cp_rev(k,4:6)'; 
        local_xy=null(local_z');
        local_x=local_xy(:,1);
        local_y=local_xy(:,2);

        %rotation matrix
        rot=[   local_x(1) local_y(1) local_z(1);
                local_x(2) local_y(2) local_z(2);
                local_x(3) local_y(3) local_z(3)];
                
        new_normal=rot*dn;
        cp_rev(k,4:6)=new_normal./norm(new_normal);
        
    elseif idx>no_cp && idx<=no_cp+no_cpin
    
        k=idx-no_cp;
        
        local_orig=cpin_rev(k,1:3)';
        local_z=cpin_rev(k,4:6)';              
        local_xy=null(local_z');
        local_x=local_xy(:,1);
        local_y=local_xy(:,2);

        rot=[   local_x(1) local_y(1) local_z(1);
                local_x(2) local_y(2) local_z(2);
                local_x(3) local_y(3) local_z(3)];
                
        new_normal=rot*dn;
        cpin_rev(k,4:6)=new_normal./norm(new_normal);
        
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin
        
        k=idx-(no_cp+no_cpin);
        
        local_orig=clin_rev(k,1:3)';
        local_z=clin_rev(k,7:9)';              
        local_xy=null(local_z');
        local_x=local_xy(:,1);
        local_y=local_xy(:,2);

        rot=[   local_x(1) local_y(1) local_z(1);
                local_x(2) local_y(2) local_z(2);
                local_x(3) local_y(3) local_z(3)];
        
        new_normal=rot*dn;
        clin_rev(k,7:9)=new_normal./norm(new_normal);
        
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln
        
        k=idx-(no_cp+no_cpin+no_clin);
        
        local_orig=cpln_rev(k,1:3)';
        local_z=cpln_rev(k,4:6)';              
        local_xy=null(local_z');
        local_x=local_xy(:,1);
        local_y=local_xy(:,2);

        rot=[   local_x(1) local_y(1) local_z(1);
                local_x(2) local_y(2) local_z(2);
                local_x(3) local_y(3) local_z(3)];
        
        new_normal=rot*dn;
        cpln_rev(k,4:6)=new_normal./norm(new_normal);
        
    end
    
end

