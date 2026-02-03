function [combo]=combo_preproc(total_cp,set)
% Create an exhaustive combination that form the five-system wrench
% filename: combo_preproc.m 
% Input variables: cp, cpin, clin, cpln, cp_rev, cpin_rev, clin_rev, cpln_rev
% Output variables: combo
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global cp cpin clin cpln cpln_prop
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev

combo2=[];combo3=[];combo4=[];

% This allows the function to be used for both the baseline analysis and the optimization routine
if strcmp(set,'original')==1
    set_cp=cp; set_cpin=cpin; set_clin=clin; set_cpln=cpln; 
    set_cpln_prop=cpln_prop; 
elseif strcmp(set,'revised')==1
    set_cp=cp_rev; set_cpin=cpin_rev; set_clin=clin_rev; 
    set_cpln=cpln_rev; set_cpln_prop=cpln_prop_rev;
end

% If there is a plane (3 DOF) constraint start with 2 constraint combinations because 2 planes can compose pivot constraint set
if isempty(set_cpln)==0 
    combo2=nchoosek(1:total_cp,2); % Combination involving 2 constraints
    combo2=[combo2,zeros(size(combo2,1),3)]; % Substitute blanks with zeros
    combo3=nchoosek(1:total_cp,3); % Combination involving 3 constraints
    combo3=[combo3,zeros(size(combo3,1),2)];
    combo4=nchoosek(1:total_cp,4); % Combination involving 4 constraints
    combo4=[combo4,zeros(size(combo4,1),1)];
    combo5=nchoosek(1:total_cp,5); % Combination involving 5 constraints

% If there is a pin or line (2 DOF) constraint,  start with 3 constraint combinations because 3 pins/lines can compose pivot constraint set
elseif isempty(set_cpin)==0 || isempty(set_clin)==0 
    combo3=nchoosek(1:total_cp,3); % Combination involving 3 constraints
    combo3=[combo3,zeros(size(combo3,1),2)];
    combo4=nchoosek(1:total_cp,4); % Combination involving 4 constraints
    combo4=[combo4,zeros(size(combo4,1),1)];
    combo5=nchoosek(1:total_cp,5); % Combination involving 5 constraints

% If there is no HOC, 5 point constraints are always needed to compose pivot constraint set
else
    combo5=nchoosek(1:total_cp,5);
end

combo=[combo2;combo3;combo4;combo5]; % Merge all combination
