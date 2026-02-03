function [wrench]=form_combo_wrench(i,combo, wr_all)
% Creates wrench matrix for a given pivot constraint combination
% 
% Input variables: i,combo, wr_all
% Output variables: wrench
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% Form the combination set from constraint wrenches
% Compose wrench based on the number of constraints in the combination
if nnz(combo(i,:))==2 
    wrench = [wr_all{combo(i,1)};wr_all{combo(i,2)}];
elseif nnz(combo(i,:))==3
    wrench = [wr_all{combo(i,1)};wr_all{combo(i,2)};wr_all{combo(i,3)}];
elseif nnz(combo(i,:))==4
    wrench = [wr_all{combo(i,1)};wr_all{combo(i,2)};wr_all{combo(i,3)};
              wr_all{combo(i,4)}];
else
    wrench = [wr_all{combo(i,1)};wr_all{combo(i,2)};wr_all{combo(i,3)};
              wr_all{combo(i,4)};wr_all{combo(i,5)}];
end