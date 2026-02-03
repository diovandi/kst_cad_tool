% Close html result file
% filename: result_close.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

timestop=clock; 

totaltime=etime(timestop,timestart)/60; %total time in minutes
totaltime_min=fix(totaltime);
totaltime_sec=mod(totaltime,1)*60;
fprintf(result,'<p>\nTotal analysis time: %5.0f minutes %2.0f seconds \n<p>',totaltime_min,totaltime_sec);

% fprintf(result,'\n</T1>\n');
fprintf(result,'\n</font>\n');
fclose(result);