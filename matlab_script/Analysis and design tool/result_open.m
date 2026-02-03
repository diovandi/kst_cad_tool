function [result]=result_open(inputfile)
% Open html result file for writing
% filename: result_open.m
% Input variables: inputfile
% Output variables: result
% Called functions: -

% Copyright 2008 Leonard Rusli
% The Ohio State University

% Create filename according to inputfile
filename=['Result - ' inputfile '.html']; 
result = fopen(filename, 'wt');

% Result header for html format
fprintf(result,'<HEAD>\n<TITLE>\nResult file for %s\n</TITLE>\n\n',inputfile);
fprintf(result,'<STYLE TYPE="text/css">\n<!--\nT1\n   {\n');
fprintf(result,'font-family:sans-serif; \nfont-size:10pt;\n}\n-->\n</STYLE>\n');
fprintf(result,'\n</HEAD>\n');
fprintf(result,'<FONT SIZE=3 FACE="helvetica">\n');
