function [Rcpln_pos Rcpln_neg]=rate_cpln2(mot,react_wr_5,input_wr,cpln_row,cpln_prop_row)
% Rate the resistance quality of rectangular plane constraints
% filename: rate_cpln2.m
% Input variables: mot,react_wr_5,input_wr,cpln_row,cpln_prop_row
% Output variables: Rcpln_pos, Rcpln_neg
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

omu=mot(1:3);rho=mot(7:9);h=mot(10); %muu is only unit length in trans

cpln_ctr=cpln_row(1:3); % plane midpoint coordinate
cpln_normal=cpln_row(4:6); % plane normal constraint direction
cpln_rad=cpln_prop_row(1); %circular plane radius

if h~=inf
    % Assess the relationship between input wrench and reaction wrench
    mom_arm = cpln_ctr-rho;            
    if norm(mom_arm)~=0 % Non-intersecting
        mom_arm_proj = cross(cpln_normal,cross(mom_arm,cpln_normal)); 
        % If the cross mom_arm ~=0 but parallel to normal this is fine
        % because then it means the plane cannot react
    else  % Intersecting
        mom_arm_proj=cross(omu,cpln_normal);
    end
    
    if norm(mom_arm_proj)~=0 
        mom_arm_proj=mom_arm_proj./norm(mom_arm_proj);
    end

    % Optimum reaction location
    cpln_edge_pos1=cpln_ctr+mom_arm_proj.*cpln_rad;
    cpln_edge_pos2=cpln_ctr-mom_arm_proj.*cpln_rad; 
else
    % For pure translation, the location of wrench does not matter
    cpln_edge_pos1=cpln_ctr;
    cpln_edge_pos2=cpln_ctr;    
end

% Reaction wrenches
wr_line_proj1=[cpln_normal,cross((cpln_edge_pos1-rho),cpln_normal)];
wr_line_proj2=[cpln_normal,cross((cpln_edge_pos2-rho),cpln_normal)];

% Merge the constraining wrenches from pivot constraints and reaction constraints 
react_wr1=[react_wr_5; wr_line_proj1]';
react_wr2=[react_wr_5; wr_line_proj2]';

if rank(react_wr1')==6  % If rank is not 6 then it is linearly dependent have infinite reaction
    static_sol=react_wr1\input_wr; % Solve static equilibrium     
    M1=static_sol(end);     % Capture lambda_6                    
else
    M1=inf;
end

if rank(react_wr2')==6 
    static_sol=react_wr2\input_wr;                    
    M2=static_sol(end);                    
else
    M2=inf;
end

M=[M1 M2]; Mpos=[inf inf];Mneg=[inf inf];

% Select the optimum reaction point (least reaction force) for each direction motion
for b=1:2
    if abs(M(b)) < 0.0001, M(b)=0; end 
    if M(b)>0, Mpos(b)=M(b);end
    if M(b)<0, Mneg(b)=-M(b);end
end

% Reciprocal sum when both points react together
% This happens when the line of action is in the same direction for both locations
Rcpln_pos=1/(2*(1/Mpos(1)+1/Mpos(2)));
Rcpln_neg=1/(2*(1/Mneg(1)+1/Mneg(2)));
    


