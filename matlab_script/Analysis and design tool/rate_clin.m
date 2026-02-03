function [Rclin_pos Rclin_neg]=rate_clin(mot,react_wr_5,input_wr,clin_row)
% Rate the resistance quality of line constraints
% filename: rate_clin.m
% Input variables: mot,react_wr_5,input_wr,clin_row
% Output variables: Rclin_pos, Rclin_neg
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

rho=mot(7:9);
clin_ctr=clin_row(1:3); % Line midpoint coordinate
clin_dir=clin_row(4:6)./norm(clin_row(4:6)); % Line direction
clin_normal=clin_row(7:9); % Line normal constraint direction
clin_halflen=clin_row(10)/2; % Line half length

% Line constraint end points
clin_end1=clin_ctr+(clin_halflen.*clin_dir); 
clin_end2=clin_ctr-(clin_halflen.*clin_dir); 

% Reaction wrenches
wr_clin_end1=[clin_normal,cross((clin_end1-rho),clin_normal)]; 
wr_clin_end2=[clin_normal,cross((clin_end2-rho),clin_normal)]; 

% Merge the constraining wrenches from pivot constraints and reaction constraints 
react_wr1=[react_wr_5; wr_clin_end1]'; 
react_wr2=[react_wr_5; wr_clin_end2]'; 

if rank(react_wr1')==6 % If rank is not 6 then it is linearly dependent have infinite reaction
    static_sol=react_wr1\input_wr; % Solve static equilibrium                     
    M(1)=static_sol(end); % Capture lambda_6                   
else
    M(1)=inf;
end

if rank(react_wr2')==6 
    static_sol=react_wr2\input_wr;                    
    M(2)=static_sol(end);                    
else
    M(2)=inf;
end

Mpos=[inf inf];Mneg=[inf inf];

% Select the optimum reaction point (least reaction force) for each direction motion
for b=1:2
    if abs(M(b)) < 0.0001, M(b)=0; end 
    if M(b)>0, Mpos(b)=M(b);end
    if M(b)<0, Mneg(b)=-M(b);end
end

% Reciprocal sum when both points react together
% This happens when the line of action is in the same direction for both locations
Rclin_pos=1/(1/Mpos(1)+1/Mpos(2)); 
Rclin_neg=1/(1/Mneg(1)+1/Mneg(2)); 