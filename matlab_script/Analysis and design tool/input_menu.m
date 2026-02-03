function [cp, cpin, clin, cpln, cpln_prop, inputfile,...
    grp_members, grp_rev_type, grp_srch_spc,...
    add_cp_type, add_cp]=input_menu()
% Menu to select input file
% filename: input_menu.m
% Purpose: 
% - Request input file from user 
% - Store the input for report filename
% 
% Input variables: -
% Output variables: cp, cpin, clin, cpln, cpln_prop, inputfile, 
%                   grp_members, grp_rev_type, grp_srch_spc,
%                   add_cp_type,add_cp
% Called functions: - 
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

cp=[]; cpin=[]; clin=[]; cpln=[]; cpln_prop=[];
cp_rev_allow=[]; pt_srch=[]; lin_srch=[]; pln_srch=[]; dir_srch=[];
lin_size_srch=[]; pln_size_srch=[];
cp_rev_grp=[];cp_grp_prop=[];
grp_members=[];
grp_rev_type=[]; 
grp_srch_spc=[];
add_cp_type=[];
add_cp=[];

% Create labels for each input file
f1='case1a_chair_height';
f2='case1b_chair_height_angle';
f3='case2a_cube_scalability';
f4='case2b_cube_tradeoff';
f5='case3a_cover_leverage';
f6='case3b_cover_symmetry';
f7='case3c_cover_orient';
f8='case4a_endcap_tradeoff';
f9='case4b_endcap_circlinsrch';
f10='case5a_printer_4screws_orient';
f11='case5b_printer_4screws_line';
f12='case5c_printer_snap_orient';
f13='case5d_printer_snap_line';
f14='case5e_printer_partingline';
f15='case5f1_printer_line_size';
f16='case5f2_printer_sideline_size';
f17='case5g_printer_5d';
f18='case5rev_a_printer_2screws';
f19='case5_printer_allscrews';
f20='case5rev_d_printer_remove2_bot_screw';
f21='case5rev_b_printer_flat_partingline';


% Display input file choices & prompt user
fprintf('\n1: %s\n2: %s\n3: %s\n4: %s\n5: %s\n6: %s\n7: %s\n8: %s\n9: %s\n10: %s\n'...
    ,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10);
fprintf('11: %s\n12: %s\n13: %s\n14: %s\n15: %s\n16: %s\n',f11,f12,f13,f14,f15,f16);
fprintf('17: %s\n18: %s\n19: %s\n20: %s\n21: %s\n\n',f17,f18,f19,f20,f21);
cp_set = input('Which input file to run? ');

if cp_set == 1
    case1a_chair_height
    inputfile=f1;
elseif cp_set == 2
    case1b_chair_height_angle
    inputfile=f2;
elseif cp_set == 3
    case2a_cube_scalability
    inputfile=f3;
elseif cp_set == 4
    case2b_cube_tradeoff
    inputfile=f4;
elseif cp_set == 5
    case3a_cover_leverage
    inputfile=f5;
elseif cp_set == 6
    case3b_cover_symmetry
    inputfile=f6;
elseif cp_set == 7
    case3c_cover_orient
    inputfile=f7;
elseif cp_set == 8
    case4a_endcap_tradeoff
    inputfile=f8;
elseif cp_set == 9
    case4b_endcap_circlinsrch
    inputfile=f9;
elseif cp_set ==10
    case5a_printer_4screws_orient
    inputfile=f10;
elseif cp_set ==11
    case5b_printer_4screws_line
    inputfile=f11;
elseif cp_set ==12
    case5c_printer_snap_orient
    inputfile=f12;
elseif cp_set ==13
    case5d_printer_snap_line
    inputfile=f13;
elseif cp_set == 14
    case5e_printer_partingline
    inputfile=f14;
elseif cp_set ==15
    case5f1_printer_line_size
    inputfile=f15;
elseif cp_set ==16
    case5f2_printer_sideline_size
    inputfile=f16;
elseif cp_set ==17
    case5g_printer_5d
    inputfile=f17;
elseif cp_set ==18
    case5rev_a_printer_2screws
    inputfile=f18;
elseif cp_set == 19
    case5_printer_allscrews
    inputfile=f19;
elseif cp_set == 20
    case5rev_d_printer_remove2_bot_screw
    inputfile=f20;
elseif cp_set == 21
    case5rev_b_printer_flat_partingline
    inputfile=f21;
end

