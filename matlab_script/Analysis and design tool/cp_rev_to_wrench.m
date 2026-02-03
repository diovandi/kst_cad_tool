function [wr_all_new pts max_d]=cp_rev_to_wrench(wr_all,cp_rev_idx...
    ,cp_rev ,cpin_rev, clin_rev, cpln_rev,cpln_prop_rev)
% Transforms constraints into wrenches (for optimization routine)
% filename: cp_rev_to_wrench.m
% Purpose:  
% - Transforms point, pin, line, and plane constraints into wrench systems
% - Create discretized constraint location points for moment arm calculation
% - Calculates the maximum distance between discretized location points
% 
% Input variables:wr_all,cp_rev_idx,cp_rev ,cpin_rev, clin_rev, cpln_rev,cpln_prop_rev
% Output variables: wr_all_new, pts, max_d
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global no_cp no_cpin no_clin no_cpln

% Initialize default values for variables
wr_all_new=wr_all;

% Transform contacts into wrench systems with motor notation [om,mu]% 
% om = Normal(x,y,z) - the screw axis direction, 
% mu = cross(Position,Normal) - the velocity of the origin

% Only change wr_all for modified constraints for efficiency
for i=1:length(cp_rev_idx)    
    idx=cp_rev_idx(i);    
    if idx<=no_cp        
        k=idx;
        wr_all_new{idx}=[cp_rev(k,4:6),cross(cp_rev(k,1:3),cp_rev(k,4:6))];               
    elseif idx>no_cp && idx<=no_cp+no_cpin        
        k=idx-no_cp;        
        axes=null(cpin_rev(k,4:6));
        om_axis1=axes(:,1)';
        om_axis2=axes(:,2)';
        mu_axis1=cross(cpin_rev(k,1:3),om_axis1);
        mu_axis2=cross(cpin_rev(k,1:3),om_axis2);
        wr_all_new{idx}=[om_axis1 mu_axis1;om_axis2 mu_axis2];        
    elseif idx>no_cp+no_cpin && idx<=no_cp+no_cpin+no_clin        
        k=idx-(no_cp+no_cpin);    
        om_axis1=clin_rev(k,7:9); %zero pitch
        om_axis2=[0 0 0]; %inf pitch
        mu_axis1=cross(clin_rev(k,1:3),om_axis1); %zero pitch
        mu_axis2=cross(clin_rev(k,4:6),clin_rev(k,7:9)); %inf pitch
        wr_all_new{idx}=[om_axis1 mu_axis1;om_axis2 mu_axis2];        
    elseif idx>no_cp+no_cpin+no_clin && idx<=no_cp+no_cpin+no_clin+no_cpln        
        k=idx-(no_cp+no_cpin+no_clin);        
        axes=null(cpln_rev(k,4:6));
        om_axis1=cpln_rev(k,4:6); %zero pitch
        om_axis2=[0 0 0]; %inf pitch
        om_axis3=[0 0 0]; %inf pitch
        mu_axis1=cross(cpln_rev(k,1:3),om_axis1); %zero pitch
        mu_axis2=axes(:,1)';
        mu_axis3=axes(:,2)';
        wr_all_new{idx}=[om_axis1 mu_axis1;om_axis2 mu_axis2;om_axis3 mu_axis3];        
    end    
end

clear k j

pts=[];

if isempty(cp_rev)==0
    pts=[pts;cp_rev(:,1:3)];
end

if isempty(cpin_rev)==0
    pts=[pts;cpin_rev(:,1:3)];
end

if isempty(clin_rev)==0
    for j=1:size(clin_rev,1)
        pts=[pts;clin_rev(j,1:3)+clin_rev(j,10)/2.*clin_rev(j,4:6)];
        pts=[pts;clin_rev(j,1:3)-clin_rev(j,10)/2.*clin_rev(j,4:6)];
    end        
end
    
if isempty(cpln_rev)==0
    for j=1:size(cpln_rev,1)
        if cpln_rev(j,7)==1
            pts=[pts;cpln_rev(j,1:3)+cpln_prop_rev(j,4)/2.*cpln_prop_rev(j,1:3)+cpln_prop_rev(j,8)/2.*cpln_prop_rev(j,5:7)];
            pts=[pts;cpln_rev(j,1:3)+cpln_prop_rev(j,4)/2.*cpln_prop_rev(j,1:3)-cpln_prop_rev(j,8)/2.*cpln_prop_rev(j,5:7)];
            pts=[pts;cpln_rev(j,1:3)-cpln_prop_rev(j,4)/2.*cpln_prop_rev(j,1:3)+cpln_prop_rev(j,8)/2.*cpln_prop_rev(j,5:7)];
            pts=[pts;cpln_rev(j,1:3)-cpln_prop_rev(j,4)/2.*cpln_prop_rev(j,1:3)-cpln_prop_rev(j,8)/2.*cpln_prop_rev(j,5:7)];
        else
            axes=null(cpln_rev(j,4:6));
            pts=[pts;cpln_rev(j,1:3)+cpln_prop_rev(j,1).*axes(:,1)'];
            pts=[pts;cpln_rev(j,1:3)-cpln_prop_rev(j,1).*axes(:,1)'];
            pts=[pts;cpln_rev(j,1:3)+cpln_prop_rev(j,1).*axes(:,2)'];
            pts=[pts;cpln_rev(j,1:3)-cpln_prop_rev(j,1).*axes(:,2)'];
            pts=[pts;cpln_rev(j,1:3)+cosd(45)*cpln_prop_rev(j,1).*axes(:,1)'+cosd(45)*cpln_prop_rev(j,1).*axes(:,2)'];
            pts=[pts;cpln_rev(j,1:3)+cosd(45)*cpln_prop_rev(j,1).*axes(:,1)'-cosd(45)*cpln_prop_rev(j,1).*axes(:,2)'];
            pts=[pts;cpln_rev(j,1:3)-cosd(45)*cpln_prop_rev(j,1).*axes(:,1)'+cosd(45)*cpln_prop_rev(j,1).*axes(:,2)'];
            pts=[pts;cpln_rev(j,1:3)-cosd(45)*cpln_prop_rev(j,1).*axes(:,1)'-cosd(45)*cpln_prop_rev(j,1).*axes(:,2)'];
        end
    end
end

c=nchoosek(1:size(pts,1),2);

for a=1:size(c,1)
    distance(a)=((pts(c(a,1),1)-pts(c(a,2),1))^2 + ...
        (pts(c(a,1),2)-pts(c(a,2),2))^2 +...
        (pts(c(a,1),3)-pts(c(a,2),3))^2)^.5;
end

max_d=max(distance);

