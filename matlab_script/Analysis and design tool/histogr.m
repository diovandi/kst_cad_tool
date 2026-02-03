function histogr(Rating_all_org, rowsum)
% Plot the total resistance histogram
% filename: histogr.m
% Input variables: Rating_all_org, rowsum
% Output variables: -
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

if Rating_all_org(1)~=0
figure('Position',[100,500,600,300]);
hist(rowsum,length(rowsum)*2^.5);    
xlabel('Total Resistance Value','fontweight','b');ylabel('Number of motions','fontweight','b');
end
