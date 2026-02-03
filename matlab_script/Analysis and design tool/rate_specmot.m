function [Rating_all_rev Ri_specmot mot_specmot_all]=rate_specmot(x,x_map,spec_mot)
% Known loading condition main processor to calculate constraint effectiveness
% filename: rate_specmot.m
% Called functions: move_pt_srch, move_lin_srch, move_circlin_srch, move_pln_srch
%                   orient1d_srch, orient2d_srch, line_orient1d_srch, resize_lin_srch
%                   resize_rectpln_srch, resize_circpln_srch, cp_rev_to_wrench, rating
%                   rate_cp, rate_cpin, rate_clin, rate_cpln1, rate_cpln2, rating
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev
global d_proc wrench_proc input_wr_proc
global wr_all 
global grp_members grp_rev_type grp_srch_spc cp_rev_all

% The procedure here is a combination of optim_rev and main_loop procedures to analyze constraints

% Initialize variables
Rcp_pos=[];Rcp_neg=[];Rcpin=[];
Rclin_pos=[];Rclin_neg=[];
Rcpln_pos=[];Rcpln_neg=[];

no_spec_mot=size(spec_mot,1);

for m=1:no_spec_mot
     
    % Find null space for pseudo-pivot constraints
    omu=spec_mot(m,1:3)./norm(spec_mot(m,1:3));rho=spec_mot(m,4:6);h=spec_mot(m,7);
    mu=h*omu+cross(rho,omu);
    mot=[omu mu rho h];    
    rec_mot=[mu omu];
    pivot_wr=null(rec_mot)';  
    
    % Initialize constraint variables with original for each motion
    cp_rev=cp; cpin_rev=cpin; clin_rev=clin;
    cpln_rev=cpln; cpln_prop_rev=cpln_prop;

    for i=1:size(grp_members,1) 
        rev_type=grp_rev_type(i);
        cp_rev_in_group=nonzeros(grp_members(i,:));
        if rev_type==1
            x_grp=x(x_map(i,1));
            move_pt_srch(x_grp,cp_rev_in_group, grp_srch_spc);  
        elseif rev_type==2
            x_grp=x(x_map(i,1));
            move_lin_srch(x_grp,cp_rev_in_group,grp_srch_spc(i,:));
        elseif rev_type==3
            x_grp=x(x_map(i,1));
            move_circlin_srch(x_grp,cp_rev_in_group,grp_srch_spc(i,:));
        elseif rev_type==4
            x_grp=x(x_map(i,1:2));
            move_pln_srch(x_grp,cp_rev_in_group,grp_srch_spc(i,:));
        elseif rev_type==5
            x_grp=x(x_map(i,1));
            orient1d_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
        elseif rev_type==6
            x_grp=x(x_map(i,1:2));
            orient2d_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
        elseif rev_type==7
            x_grp=x(x_map(i,1));
            line_orient1d_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
        elseif rev_type==8
            x_grp=x(x_map(i,1));
            resize_lin_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
        elseif rev_type==9
            x_grp=x(x_map(i,1));
            resize_rectpln_srch(x_grp(1:2),cp_rev_in_group, grp_srch_spc(i,:));
        elseif rev_type==10
            x_grp=x(x_map(i,1));
            resize_circpln_srch(x_grp,cp_rev_in_group, grp_srch_spc(i,:));
        end
    end
    
    % Transform constraints into wrenches
    [wr_all_new pts_rev max_d_rev]=cp_rev_to_wrench(wr_all,cp_rev_all, ...
            cp_rev, cpin_rev, clin_rev, cpln_rev, cpln_prop_rev);

    omu=mot(1:3)';mu=mot(4:6)';rho=mot(7:9)';h=mot(10);
    
    % Calculate d for motion
    if h~=inf
        [d]=calc_d(omu,rho,pts_rev,max_d_rev);
    else
        d=inf;
    end

    %Set up input wrench with true origin, unlike main_loop
    hs=h; hw=1/h;
    if abs(hw)>=d
        %rotation dominant torque input
        fi=hs*d*omu;
        ti=d*omu+hs*d*cross(rho,omu);
    elseif h==inf     
        %pure translation , force dominant
        fi=mu;  %mu already normalized in rec_mot
        ti=[0;0;0];                    
    else
        %force dominant force input
        fi=omu;
        ti=hw*omu+cross(rho,omu);
    end
    input_wr=-[fi;ti];

    % Rate all constraints
    % We can use pivot_wr as react_wr_5 because everything is with respect to origin
    for j = 1:no_cp
        [Rcp_pos(m,j) Rcp_neg(m,j)]=rate_cp(mot,pivot_wr, input_wr, cp_rev(j,:));
    end

    for j = 1:no_cpin
        [Rcpin(m,j)]=rate_cpin(mot,pivot_wr,input_wr,cpin_rev(j,:));
    end

    for j = 1:no_clin
        [Rclin_pos(m,j) Rclin_neg(m,j)]=rate_clin(mot,pivot_wr,input_wr,clin_rev(j,:));
    end

    for j = 1:no_cpln
        if cpln_rev(j,7)==1
            [Rcpln_pos(m,j) Rcpln_neg(m,j)]=rate_cpln1(mot,pivot_wr, input_wr,cpln_rev(j,:),cpln_prop_rev(j,:));
        elseif cpln_rev(j,7)==2
            [Rcpln_pos(m,j) Rcpln_neg(m,j)]=rate_cpln2(mot,pivot_wr, input_wr,cpln_rev(j,:),cpln_prop_rev(j,:));
        end
    end

    mot_specmot(m,:)=mot;
    mot_specmot_rev(m,:)=[-mot(1:6) mot(7:10)];     % Add reverse motion
    
    % Collect processed d, pivot wrenches, and input wrenches
    d_proc(m,1)=d;
    wrench_proc{m}=pivot_wr;
    input_wr_proc{m}=input_wr;

end

mot_specmot_all=[mot_specmot;mot_specmot_rev]; % Collect motions

Rcp=[Rcp_pos;Rcp_neg]; % Merge resistance value for fwd and rev motion for constraints
Rcpin=[Rcpin;Rcpin]; % Resistance values for fwd and rev motion is the same for cpin
Rclin=[Rclin_pos;Rclin_neg];
Rcpln=[Rcpln_pos;Rcpln_neg];    

R=[Rcp Rcpin Rclin Rcpln]; % Merge all ratings

Ri_specmot=1./R;
Ri_specmot=(round(Ri_specmot.*1e4)).*1e-4;

% Calculate final ratings
[Rating_all_rev WTR_idx_org free_mot free_mot_idx best_cp rowsum]=rating(Ri_specmot, mot_specmot);

