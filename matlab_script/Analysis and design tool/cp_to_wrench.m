function [wr_all pts max_d]=cp_to_wrench(cp,cpin,clin,cpln,cpln_prop)
% Transforms constraints into wrenches
% filename: cp_to_wrench.m
% Purpose:  
% - Transforms point, pin, line, and plane constraints into wrench systems
% - Create discretized constraint location points for moment arm calculation
% - Calculates the maximum distance between discretized location points
% 
% Input variables: cp, cpin, clin, cpln, cpln_prop
% Output variables: wr_all, pts, max_d
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

wr_pt=[];wr_pin=[];wr_lin=[];wr_pln=[];wr_all=[]; % Initialize default values for variables
j=1; % Initialize index for wr_all

% Transform all point contacts
for i = 1:size(cp,1)
    wr=[cp(i,4:6),cross(cp(i,1:3),cp(i,4:6))];
    wr_all{j}=wr;
    j=j+1; % Advance index
end  

% Transform all pin contacts
% Pin syntax cpin=[centerpoint(x,y,z), pinaxis(x,y,z)]
for i = 1:size(cpin,1)
    axes=null(cpin(i,4:6)); % Solve for basis vectors of plane normal to pin axis
    om_axis1=axes(:,1)'; % Wrench principle axis 1 zero pitch
    om_axis2=axes(:,2)'; % Wrench principle axis 2 zero pitch
    mu_axis1=cross(cpin(i,1:3),om_axis1); % mu principle axis 1 zero pitch
    mu_axis2=cross(cpin(i,1:3),om_axis2); % mu principle axis 2 zero pitch
    wr_all{j}=[om_axis1 mu_axis1;om_axis2 mu_axis2]; % Merge wrench principle axes
    j=j+1; % Advance index
end 

% Transform line contact
% Line syntax clin=[midpoint(x,y,z), line dir(x,y,z), constraint dir(x,y,z), length of line]
for i = 1:size(clin,1)
  om_axis1=clin(i,7:9); %zero pitch
  om_axis2=[0 0 0]; %inf pitch
  mu_axis1=cross(clin(i,1:3),om_axis1); %zero pitch
  mu_axis2=cross(clin(i,4:6),clin(i,7:9)); %inf pitch
  wr_all{j}=[om_axis1 mu_axis1;om_axis2 mu_axis2];
  j=j+1;
end 

% Plane syntax cpln=[midpoint(x,y,z), normal(x,y,z), type (1 is rect 2 is circ)
% cpln_prop= [xaxisdir(x,y,z),x-length,yaxisdir(x,y,z),y-length]
% or for circular cpln_prop=[radius];

% Transform plane contact
for i = 1:size(cpln,1)
  axes=null(cpln(i,4:6));
  om_axis1=cpln(i,4:6); %zero pitch
  om_axis2=[0 0 0]; %inf pitch
  om_axis3=[0 0 0]; %inf pitch
  mu_axis1=cross(cpln(i,1:3),om_axis1); %zero pitch
  mu_axis2=axes(:,1)';
  mu_axis3=axes(:,2)';
  wr_all{j} =[om_axis1 mu_axis1;om_axis2 mu_axis2;om_axis3 mu_axis3];
  j=j+1;
end 

clear i j

pts=[];

if isempty(cp)==0
    pts=[pts;cp(:,1:3)];
end

if isempty(cpin)==0
    pts=[pts;cpin(:,1:3)];
end

if isempty(clin)==0
    for j=1:size(clin,1)
        pts=[pts;clin(j,1:3)+clin(j,10)/2.*clin(j,4:6)];
        pts=[pts;clin(j,1:3)-clin(j,10)/2.*clin(j,4:6)];
    end        
end
    
if isempty(cpln)==0
    for j=1:size(cpln,1)
        if cpln(j,7)==1
            pts=[pts;cpln(j,1:3)+cpln_prop(j,4)/2.*cpln_prop(j,1:3)+cpln_prop(j,8)/2.*cpln_prop(j,5:7)];
            pts=[pts;cpln(j,1:3)+cpln_prop(j,4)/2.*cpln_prop(j,1:3)-cpln_prop(j,8)/2.*cpln_prop(j,5:7)];
            pts=[pts;cpln(j,1:3)-cpln_prop(j,4)/2.*cpln_prop(j,1:3)+cpln_prop(j,8)/2.*cpln_prop(j,5:7)];
            pts=[pts;cpln(j,1:3)-cpln_prop(j,4)/2.*cpln_prop(j,1:3)-cpln_prop(j,8)/2.*cpln_prop(j,5:7)];
        else
            axes=null(cpln(j,4:6));
            pts=[pts;cpln(j,1:3)+cpln_prop(j,1).*axes(:,1)'];
            pts=[pts;cpln(j,1:3)-cpln_prop(j,1).*axes(:,1)'];
            pts=[pts;cpln(j,1:3)+cpln_prop(j,1).*axes(:,2)'];
            pts=[pts;cpln(j,1:3)-cpln_prop(j,1).*axes(:,2)'];
            pts=[pts;cpln(j,1:3)+cosd(45)*cpln_prop(j,1).*axes(:,1)'+cosd(45)*cpln_prop(j,1).*axes(:,2)'];
            pts=[pts;cpln(j,1:3)+cosd(45)*cpln_prop(j,1).*axes(:,1)'-cosd(45)*cpln_prop(j,1).*axes(:,2)'];
            pts=[pts;cpln(j,1:3)-cosd(45)*cpln_prop(j,1).*axes(:,1)'+cosd(45)*cpln_prop(j,1).*axes(:,2)'];
            pts=[pts;cpln(j,1:3)-cosd(45)*cpln_prop(j,1).*axes(:,1)'-cosd(45)*cpln_prop(j,1).*axes(:,2)'];
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

