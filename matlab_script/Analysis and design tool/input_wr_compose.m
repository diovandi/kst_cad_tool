function [input_wr d]=input_wr_compose(mot,set_pts,set_max_d)
% Compose input wrench for a given motion
% filename: input_wr_compose.m
% Input variables: mot,set_pts,set_max_d
% Output variables: input_wr, d
% Called functions: calc_d
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% Assign variables from screw axis parameters
omu=mot(1:3)';mu=mot(4:6)';rho=mot(7:9)';h=mot(10); 

%Determine max moment arm d for motion
if h~=inf
    [d]=calc_d(omu,rho,set_pts,set_max_d);
else
    d=inf; % For pure translation, d is not used
end

hs=h; % Screw pitch 
hw=1/h; % Wrench pitch 

if abs(hw)>=d
    % Rotation-dominant motion, torque input
    fi=hs*d*omu;
    ti=d*omu;
elseif h==inf     
    % Pure translation , force input
    fi=mu;  % mu is the screw axis for pure translation
    ti=[0;0;0];                    
else
    % Translation-dominant motion, force input
    fi=omu;
    ti=hw*omu;
end

input_wr=-[fi;ti]; % Compose input wrench, negative sign for static equilibrium