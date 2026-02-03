cp1 =[9.375 18 0.377 0 0 -1];
cp2 =[10.299 2.5 0.125 0 0 -1];
cp3 =[2.375 18 4.045 0 0 -1];
cp4 =[2.375 0 4.045 0 0 -1];
cp5 =[7.5 0 2.125 0 0 -1];
cp6=[8.625 13.875 1.744 0 0 1];
cp7=[8.625 13.875 1.744 0 0 -1];
cp8=[8.625 4.125 1.744 0 0 1];
cp9=[8.625 4.125 1.744 0 0 -1];
cp10=[0.322 14.75 4.25 1 0 0];
cp11=[0.322 14.75 4.25 -1 0 0];
cp12=[0.322 3.25 4.25 1 0 0];
cp13=[0.322 3.25 4.25 -1 0 0];
cpin1=[8.625 13.875 1.744 0 0 1];
cpin2=[8.625 4.125 1.744 0 0 1];
cpin3=[0.322 14.75 4.25 1 0 0];
cpin4=[0.322 3.25 4.25 1 0 0];
clin1=[7.125 18 3.2 -3.093 0 3.441 0.7437    0    0.6685 8.941];
clin2=[7.125 0 3.2 -3.093 0 3.441   0.7437    0    0.6685 8.941];
clin3=[1.551 18 4.754 2 0 0.431 -0.2107         0    0.9776 3];
clin4=[1.551 0 4.754 2 0 0.431 -0.2107         0    0.9776 3];
clin5=[0 9 4.42 0 1 0 0 0 1 11.5];
clin6=[11 9 0 0 1 0 0 0 1 18];

cp = [cp1;cp2;cp3;cp4;cp5;cp6;cp7;cp8;cp9;cp10;
    cp11;cp12;cp13];
cpin=[cpin1;cpin2;cpin3;cpin4];
clin=[clin1;clin2;clin3;clin4;clin5;clin6];

% case 5a - 4 screws orientation search (grouped by 2)
% grp_members=[6 7 14 8 9 15;
%                10 11 16 12 13 17];      
% grp_rev_type=[5;5]; 
% grp_srch_spc=[  0 1 0 ,90;
%                 0 1 0 ,90];

% case 5b - 2 bottom screw line search 
% grp_members=[6 7 14;
%             8 9 15];      
% grp_rev_type=[2;2]; 
% grp_srch_spc=[  8.625 9 1.744 ,0	1	0, 4.875;    
%                 8.625 9 1.744, 0	1	0, 4.875];

% case 5c - 2 top screw line search
% grp_members=[10 11 16;
%             12 13 17];      
% grp_rev_type=[2;2]; 
% grp_srch_spc=[  0.322 9 4.25 ,0	1	0, 5.75;    
%                 0.322 9 4.25, 0	1	0, 5.75];

% case 5d - Line direction parting line search  (done)
% grp_members=[18 19 0 0  0 0 0 0 0 0 0 0;
%                  22 20 21 10 11 12 13 16 17];
% grp_rev_type=[7;2]; 
% grp_srch_spc=[0 1 0, 60 0 0 0;
%                 0 9.000 2, 0 0 1, 2 ];

% case 5e - 4 snap line search (grouped by 2)
% grp_members=[1 5;
%             3 4];      
% grp_rev_type=[2;2]; 
% grp_srch_spc=[  6.6775	18	2.5295,7.169	0	-5.059, 3;    
%                 1.4885	18	4.751, -2.977	0	-0.622, 1.5];
            
% case 5f - 2 snap angle1d search  (done)
grp_members=[1 5;
            3 4];      
grp_rev_type=[5;5]; 
grp_srch_spc=[  0 1 0 , 60;    
                0 1 0 , 60];

% case 5g - 3 snap group line search 
% grp_members=[1 5;
%             3 4;
%             2 0 ];       
% grp_rev_type=[2;2;2]; 
% grp_srch_spc=[  6.6775	18	2.5295,7.169	0	-5.059, 3;    
%                 1.4885	18	4.751, -2.977	0	-0.622, 1.5;
%                 11	2	0, 0 1 0, 1.5];



