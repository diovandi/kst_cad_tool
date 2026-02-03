% Checks input file for consistency
% filename: inputfile_check.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

inputfile_ok=true;

if isempty(cp)==1 && isempty(cpin)==1 && isempty(clin)==1 && isempty(cpln)==1
    inputfile_ok=false;
    inputfile_error='All CP variable is empty';
end

if isempty(cp)==0 && size(cp,2)~=6 
    inputfile_ok=false;
    inputfile_error='CP size is incorrect';
end

if isempty(cpin)==0 && size(cpin,2)~=6
    inputfile_ok=false;
    inputfile_error='CPIN size is incorrect';
end

if isempty(clin)==0 && size(clin,2)~=10
    inputfile_ok=false;
    inputfile_error='CLIN size is incorrect';
end

if isempty(cpln)==0 && size(cpln,2)~=7 && size(cpln_prop,2)~=8
    inputfile_ok=false;
    inputfile_error='CPLN or CPLN_PROP size is incorrect';
end
    
if size(cpln,1)~=size(cpln_prop,1)
    inputfile_ok=false;
    inputfile_error='CPLN and CPLN_PROP does not have the same number of constraints';
end


