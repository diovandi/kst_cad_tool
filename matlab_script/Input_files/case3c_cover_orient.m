%first case study
cp1 =[1 2 0 0 0 -1];
cp2 =[3 2 0 0 0 -1];
cp3 =[1 0 0 0 0 -1];
cp4 =[3 0 0 0 0 -1];

clin1=[0 1 0 0 1 0 1 0 0 2];
clin2=[4 1 0 0 1 0 -1 0 0 2];
clin3=[2 0 0 1 0 0 0 1 0 4];
clin4=[2 2 0 1 0 0 0 -1 0 4];

cpln1=[2 1 0 0 0 1 1];
cpln_prop1=[1 0 0 4 0 1 0 2];

cp = [cp1;cp2;cp3;cp4];
clin = [clin1;clin2;clin3;clin4];
cpln =cpln1;
cpln_prop = cpln_prop1;

%Optim variables
% grp_members=[1 3;
%              2 4];
% grp_rev_type=[5;5];
% grp_srch_spc=[  1 0 0 , 45;
%                 1 0 0 ,45];


grp_members=[1 2 3 4];
grp_rev_type=[6];      
grp_srch_spc=[  1 0 0 , 0 1 0 , 45,45];