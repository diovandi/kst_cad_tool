function [Rcp_pos Rcp_neg]=rate_cp(mot,react_wr_5, input_wr, cp_row)
% Rate the resistance quality of point constraints
% filename: rate_cp.m
% Input variables: mot,react_wr_5, input_wr, cp_row
% Output variables: Rcp_pos, Rcp_neg
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

rho=mot(7:9);
cp_pos=cp_row(1:3)-rho; % Position vector of cp from rho
wr_pt_set=[cp_row(4:6),cross(cp_pos,cp_row(4:6))]; % Reaction wrench

% Merge the constraining wrenches from pivot constraints and reaction constraints 
react_wr=[react_wr_5; wr_pt_set]'; 

if rank(react_wr')==6 % If rank is not 6 then it is linearly dependent have infinite reaction
    static_sol=react_wr\input_wr; % Solve static equilibrium              
    if static_sol(end)>=0 % Capture the Positive value
        Rcp_pos=static_sol(end);
        Rcp_neg=inf;
    else % Capture the Negative value
        Rcp_pos=inf;
        Rcp_neg=-static_sol(end);
    end
else
    Rcp_pos=inf;
    Rcp_neg=inf;
end

