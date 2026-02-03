function [d]=calc_d(omu,rho,pts,max_d)
% Calculate maximum moment arm d between screw axis and constraint locations
% filename: calc_d.m
% Input variables: omu,rho,pts,max_d
% Output variables: d
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

for a=1:size(pts,1)
    mom_arm = pts(a,:)'-rho;    
    dist(a)=norm(cross(omu,mom_arm)); % project moment arm to perpendicular distance
end

d=max(dist); % pick the maximum

if d>max_d
    d=max_d; %limit d to max_d, maximum distance between constraints
end





