% Input file preprocessor
% filename: input_preproc.m
% Function: 
% - Normalizes the constraint normal vectors 
% - Count the number of constraints for each constraint type
%
% Input variables: cp, cpin, clin, cpln
% Output variables: no_cp, no_cpin, no_clin, no_cpln, total_cp
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% Normalize direction cosines for each constraint type
for i=1:size(cp,1)
    cp(i,4:6)=cp(i,4:6)./norm(cp(i,4:6));
end

for i=1:size(cpin,1)
    cpin(i,4:6)=cpin(i,4:6)./norm(cpin(i,4:6));
end

for i=1:size(clin,1)
    clin(i,4:6)=clin(i,4:6)./norm(clin(i,4:6));
    clin(i,7:9)=clin(i,7:9)./norm(clin(i,7:9));
end

for i=1:size(cpln,1)
    cpln(i,4:6)=cpln(i,4:6)./norm(cpln(i,4:6));
end

no_cp=size(cp,1); % no_cp is the number of contact points
no_cpin=size(cpin,1); % no_cpin is the number of contact pins
no_clin=size(clin,1); % no_clin is the number of contact line
no_cpln=size(cpln,1); % no_cpln is the number of contact plane
total_cp = no_cp+no_cpin+no_clin+no_cpln; % total_cp is the total number of constraints