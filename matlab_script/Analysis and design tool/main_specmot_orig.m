% Known loading condition analysis for original set of constraints
% filename: main_specmot_orig.m
% Called functions: input_wr_compose, rate_cp, rate_cpin, rate_clin, rate_cpln1, rate_cpln2, rating
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln 
global pts max_d d_proc wrench_proc input_wr_proc

% The procedure here is similar to main_loop, but only for a specified motion.
% See comments in main_loop.m

Rcp_pos=[];Rcp_neg=[];Rcpin=[];
Rclin_pos=[];Rclin_neg=[];
Rcpln_pos=[];Rcpln_neg=[];

no_specmot=size(specmot,1);

for m=1:no_specmot
    
    %reverse find imaginary pivot constraints
    omu=specmot(m,1:3)./norm(specmot(m,1:3));rho=specmot(m,4:6);h=specmot(m,7);
    if h~=inf
        mu=h*omu+cross(rho,omu);
    else
        mu=omu;
        omu=[0 0 0];
    end
    
    mot=[omu mu rho h];    
    rec_mot=[mu omu];
    pivot_wr=null(rec_mot)';    

    [input_wr d]=input_wr_compose(mot,pts,max_d);
    
    %Rate all constraints
    %Can use pivot_wr as react_wr_5 because everything is with respect to
    %origin
    for j = 1:no_cp
        [Rcp_pos(m,j) Rcp_neg(m,j)]=rate_cp(mot,pivot_wr, input_wr, cp(j,:));
    end

    for j = 1:no_cpin
        [Rcpin(m,j)]=rate_cpin(mot,pivot_wr,input_wr,cpin(j,:));
    end

    for j = 1:no_clin
        [Rclin_pos(m,j) Rclin_neg(m,j)]=rate_clin(mot,pivot_wr,input_wr,clin(j,:));
    end

    for j = 1:no_cpln
        if cpln(j,7)==1
            [Rcpln_pos(m,j) Rcpln_neg(m,j)]=rate_cpln1(mot,pivot_wr, input_wr,cpln(j,:),cpln_prop(j,:));
        elseif cpln(j,7)==2
            [Rcpln_pos(m,j) Rcpln_neg(m,j)]=rate_cpln2(mot,pivot_wr, input_wr,cpln(j,:),cpln_prop(j,:));
        end
    end
    
    d_proc(m,1)=d;
    wrench_proc{m}=pivot_wr;
    input_wr_proc{m}=input_wr;
    
end

Rcp=[Rcp_pos;Rcp_neg]; % Merge resistance value for fwd and rev motion for cp
Rcpin=[Rcpin;Rcpin]; % Resistance values for fwd and rev motion is the same for cpin
Rclin=[Rclin_pos;Rclin_neg];
Rcpln=[Rcpln_pos;Rcpln_neg];    
    
R=[Rcp Rcpin Rclin Rcpln];
    
Ri_specmot=1./R;
Ri_specmot=(round(Ri_specmot.*1e4)).*1e-4
rowsum_specmot=sum(Ri_specmot,2)
specmot_rev=[-specmot(:,1:3) specmot(4:7)];
mot_proc=[specmot;specmot_rev]

[Rating_all_org WTR_idx_org free_mot free_mot_idx best_cp rowsum]=rating(Ri_specmot, mot_proc);


    