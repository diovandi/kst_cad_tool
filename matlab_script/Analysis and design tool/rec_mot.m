function [mot]=rec_mot(wrench)
% Calculates reciprocal motion for a given wrench
% filename: rec_mot.m
% Input variables: wrench
% Output variables: mot
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

x=null(wrench); % The reciprocal motion is the null space of pivot wrench matrix
x=round(x.*1e4)./1e4; % Round to 4 decimal places
mu =x(1:3)'; % Translation of the origin due to screw axis
om =x(4:6)'; % Screw axis


% Calculate rho, position vector of screw axis
if norm(om)==0 % Check for pure translation
    h = inf; % Pitch is infinity for pure translation
    rho = [0 0 0];  % Set rho=0 for pure translation
    muu=mu/norm(mu); % Normalize mu    
    mot=[om muu rho h]; % Compose into standard screw motion notation    
else
    h = dot(mu,om)./dot(om,om); % Calculate pitch
    rho = cross(om,mu)./dot(om,om); % Calculate rho
    omu = om/norm(om); % Normalize screw axis
    mot=[omu mu rho h]; % Compose into standard screw motion notation    
end  

mot=round(mot.*1e4)./1e4; % Round everything to 4 decimal places



