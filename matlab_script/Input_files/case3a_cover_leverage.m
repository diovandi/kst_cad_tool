%first case study
cp1 =[0 2 0 0 0 -1];
cp2 =[4 2 0 0 0 -1];
cp3 =[0 0 0 0 0 -1];
cp4 =[4 0 0 0 0 -1];

clin1=[0 1 0 0 1 0 1 0 0 2];
clin2=[4 1 0 0 1 0 -1 0 0 2];
clin3=[2 0 0 1 0 0 0 1 0 4];
clin4=[2 2 0 1 0 0 0 -1 0 4];

cpln1=[2 1 0 0 0 1 1];
cpln_prop1=[1 0 0 4 0 1 0 2];

cp = [cp1;cp2;cp3;cp4];
% cp = [cp1;cp2;cp3];
% cpin=[2 2 0 0 0 1];
clin = [clin1;clin2;clin3;clin4];
cpln =cpln1;
cpln_prop = cpln_prop1;

%vary both side independently
% grp_members=[1 3 ;
%              2 4];    
% grp_rev_type=[2;2]; 
% grp_srch_spc=[  1 2 0 , 1 0 0 , 1;
%                 3 2 0 , 1 0 0 , 1];

% grp_members=[1];    
% grp_rev_type=[2]; 
% grp_srch_spc=[  1 2 0 , 1 0 0 , 1];


%2 lugs and 1 snap, move 2 lugs independently
% grp_members=[2 ;3];    
% grp_rev_type=[2;2]; 
% grp_srch_spc=[  1 0 0 , 1 0 0 , 1;
%                 3 0 0 , 1 0 0 , 1];

%only vary the left side
grp_members=[1 ;3] ;    
grp_rev_type=[2;2]; 
grp_srch_spc=[  1 2 0 , 1 0 0 , 1;
                1 0 0 , 1 0 0 , 1];