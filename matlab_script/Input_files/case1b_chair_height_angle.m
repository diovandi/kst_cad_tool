%  Coordinates of Snapfit Assembly  -  Contact Points
%  For the Thompson Chair Example
%  Example given in Bausch paper

%  External variable interaction
%  Input:  none
%  Output: cp

%  Contact Points
%  Position x    y    z

cp1  =  [ 3.57 -0.75 -0.50  0.43  0.75  0.50];  
cp2  =  [ 4.87  0.00 -0.50 -0.87  0.00  0.50]; 
cp3  =  [ 3.57  0.75 -0.50  0.43 -0.75  0.50];  
cp4  =  [-1.57  4.21 -0.50 -0.43 -0.75  0.50];
cp5  =  [-2.43  2.71 -0.50  0.43  0.75  0.50]; 
cp6  =  [-2.00 -3.46 -1.00  0.00  0.00  1.00]; 
cp7  =  [ 0.00  0.00  4.00  0.00  0.00 -1.00]; 

% n=[0.497384112	0.867530429	0           ]; %0 deg groove
% n=[0.493146769	0.860139714	0.130253353 ]; %15 deg groove
% n=[0.480494004	0.838070937	0.258384629 ]; %30 deg groove
% n=[0.459479398	0.801417555	0.382895006 ]; %45 deg groove
% n=[0.430795351	0.75138724	0.499832553 ]; %60 deg groove
% n=[0.394500315	0.688081945	0.609026057 ]; %75 deg groove
% n=[0.351703679	0.613436649	0.707106781 ]; %90 deg groove
% n=[0.30250905	0.527632065	0.793783773 ]; %105 deg groove
% n=[0.249080506	0.434442743	0.865574032 ]; %120 deg groove
% n=[0.189640192	0.330767776	0.924461614 ]; %135 deg groove
% n=[0.128362152	0.223887475	0.966125021 ]; %150 deg groove
% n=[0.065001963	0.113375518	0.991423591 ]; %165 deg groove
% n=[0            0           1           ]; %180 deg groove 

% cp4  =  [-1.57  4.21 -0.50 -n(1) -n(2)  n(3)];
% cp5  =  [-2.43  2.71 -0.50  n(1) n(2)  n(3)]; 

% cp1 =[0 2 0 0.43 0.75 0.5];
% cp2 =[0 2 0 -0.87 0 0.5];
% cp3 =[0 2 0 0.43 -0.75 0.5];
% cp4 =[1.732 1 0 -0.43 -0.75 0.5];
% cp5 =[1.732 1 0 0.43 0.75 0.5];
% cp6 =[-1.732 1 0 0 0 1];
% cp7 =[0 0 4 0 0 -1];

cp = [cp1;cp2;cp3;cp4;cp5;cp6;cp7];

% scale=input('Scaling factor = ');
% cp(:,1:3)=cp(:,1:3).*scale;

%change chair height
% grp_members=[7];
% grp_rev_type=[2]; 
% grp_srch_spc=[0 0 4 0 0 1 1 ];

%change cp6 orientation 1d
% grp_members=[6];
% grp_rev_type=[5]; 
% grp_srch_spc=[0 1 0 , 45, 0 0 0 ];

%change cp6 orientation 2d
% grp_members=[6];
% grp_rev_type=[6]; 
% grp_srch_spc=[0 1 0 , 1 0 0 , 45, 45 ];

%change height and cp6 orient
% grp_members=[7;6];
% grp_rev_type=[2;5]; 
% grp_srch_spc=[0 0 6, 0 0 1, 1;
%             0 1 0 , 45, 0 0 0 ];

%change height and angle of cp2 independently
grp_members=[7;
               2 ];
grp_rev_type=[2;5]; 
grp_srch_spc=[0 0 6 0 0 1 1;
                0 1 0 , 30, 0 0 0 ];
% grp_members=[7 4];
% grp_rev_type=[2;5]; 
% grp_srch_spc=[0 0 6 0 0 1 1;
%               .751 -.431 0 ,45 0 0 0 ];
            
            
