function [Rcpin]=rate_cpin(mot,react_wr_5,input_wr,cpin_row)
% Rate the resistance quality of pin constraints
% filename: rate_cpin.m
% Input variables: mot,react_wr_5,input_wr,cpin_row
% Output variables: Rcpin
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

omu=mot(1:3);muu=mot(4:6);rho=mot(7:9);h=mot(10);

cpin_ctr=cpin_row(1:3);
cpin_normal=cpin_row(4:6);

%in the write up describe the different cases that this can fall into
% parallel, coincident, intersecting, non-intersecting

if h~=inf
    % Assess the relationship between input wrench and reaction wrench
    mom_arm=cpin_ctr-rho; % Calculate moment arm length
    if norm(mom_arm)~=0 % Non-intersecting
        line_action=h*omu+cross(omu,mom_arm);
    else % Intersecting
        line_action=[0 0 0]; %if axis is coincident and/or intersecting, then pin cannot react
    end
else
    line_action=muu; % Pure translation case
end

% Project the line of action on to the plane of CPIN
const_dir = cross(cpin_normal,cross(line_action,cpin_normal));
const_dir = round(const_dir.*1e5)./1e5;

if norm(const_dir)~=0 % If const_dir==0, it a mark that reaction is infinite
    const_dir=const_dir./norm(const_dir);
    wr_const_dir=[const_dir,cross((cpin_ctr-rho),const_dir)]; % Reaction wrench
    
    % Merge the constraining wrenches from pivot constraints and reaction constraints 
    react_wr=[react_wr_5; wr_const_dir]';
    
    if rank(react_wr')==6 % If rank is not 6 then it is linearly dependent have infinite reaction
        static_sol=react_wr\input_wr; % Solve static equilibrium                
        Rcpin=abs(static_sol(end)); % Capture lambda_6
    else
        Rcpin=inf;
    end
else
    Rcpin=inf;
end




