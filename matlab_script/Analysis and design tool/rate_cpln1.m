function [Rcpln_pos Rcpln_neg]=rate_cpln1(mot,react_wr_5,input_wr,cpln_row,cpln_prop_row)
% Rate the resistance quality of rectangular plane constraints
% filename: rate_cpln1.m
% Input variables: mot,react_wr_5,input_wr,cpln_row,cpln_prop_row
% Output variables: Rcpln_pos, Rcpln_neg
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% Rectangular plane span
rho=mot(7:9);
cpln_ctr=cpln_row(1:3); % plane midpoint coordinate
cpln_normal=cpln_row(4:6); % plane normal constraint direction

% Rectangular plane span
cpln_widthdir=cpln_prop_row(1:3);
cpln_heightdir=cpln_prop_row(5:7);
cpln_halfwidth=cpln_prop_row(4)/2; % plane half length
cpln_halfheight=cpln_prop_row(8)/2; % plane half length

% Plane end points
cpln_end1=cpln_ctr+(cpln_halfwidth.*cpln_widthdir)+(cpln_halfheight.*cpln_heightdir); % plane endpoint 1 coordinate
cpln_end2=cpln_ctr+(cpln_halfwidth.*cpln_widthdir)-(cpln_halfheight.*cpln_heightdir); % plane endpoint 1 coordinate
cpln_end3=cpln_ctr-(cpln_halfwidth.*cpln_widthdir)+(cpln_halfheight.*cpln_heightdir); % plane endpoint 1 coordinate
cpln_end4=cpln_ctr-(cpln_halfwidth.*cpln_widthdir)-(cpln_halfheight.*cpln_heightdir); % plane endpoint 1 coordinate

% Reaction wrenches
wr_cpln_end=[cpln_normal,cross((cpln_end1-rho),cpln_normal);
            cpln_normal,cross((cpln_end2-rho),cpln_normal);
            cpln_normal,cross((cpln_end3-rho),cpln_normal);
            cpln_normal,cross((cpln_end4-rho),cpln_normal)];

for a=1:4
    react_wr=[react_wr_5; wr_cpln_end(a,:)]';
    if rank(react_wr')==6 % If rank is not 6 then it is linearly dependent have infinite reaction
        static_sol=react_wr\input_wr; % Solve static equilibrium  
        M(a)=static_sol(end); % Capture lambda_6           
    else
        M(a)=inf;
    end
end

Mpos=inf(1,4);Mneg=inf(1,4);

% Select the optimum reaction point (least reaction force) for both direction motion
for b=1:4
    if abs(M(b)) < 0.0001, M(b)=0; end
    if M(b)>0, Mpos(b)=M(b);end
    if M(b)<0, Mneg(b)=-M(b);end
end

% Reciprocal sum when both points react together
% This happens when the line of action is in the same direction for both locations
Rcpln_pos=1/(1/Mpos(1)+1/Mpos(2)+1/Mpos(3)+1/Mpos(4));
Rcpln_neg=1/(1/Mneg(1)+1/Mneg(2)+1/Mneg(3)+1/Mneg(4)); 