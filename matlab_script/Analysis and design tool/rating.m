function [rat WTR_idx free_mot free_mot_idx best_cp rowsum]=rating(Ri, mot_all)
% Calculate the assembly rating metrics
% filename: rating.m
% Input variables: Ri, mot_all
% Output variables: rat, WTR_idx, free_mot, free_mot_idx, best_cp, rowsum
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

[max_of_row best_cp]=max(Ri,[],2); % Identify maximum of each row
rowsum=sum(Ri,2); % Sum the rows (row refers to motions)

%Find unconstrained motion
free_mot_idx=find(rowsum==0); %find any motion that is rated zero and classify as free motion
free_mot=mot_all(free_mot_idx,:);

%Redundancy ratio
if min(rowsum)~=0 % If no unconstrained motion exists
    MRR=mean(rowsum./max_of_row);
    WTR=min(rowsum);
    WTR_idx=find(rowsum>=WTR & rowsum<=WTR*1.1);   
    MTR=mean(rowsum);
else
    WTR=0;WTR_idx=0;
    MRR=0;
    MTR=0;
end

% Report all rating
rat=[WTR MRR MTR MTR/MRR];