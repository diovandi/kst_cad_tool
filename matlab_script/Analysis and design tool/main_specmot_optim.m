% Known loading condition optimization
% filename: main_specmot_optim.m
% Called functions: rate_specmot
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln 
global cp_rev cpin_rev clin_rev cpln_rev cpln_prop_rev
global pts max_d d_proc wrench_proc input_wr_proc 
global grp_members grp_rev_type grp_srch_spc cp_rev_all

% The procedure here is similar to optim_main_rev, but we are only evaluating a specific motion

no_step=10; % default step size

WTR_optim_specmot=[]; MRR_optim_specmot=[]; MTR_optim_specmot=[];
prog_bar=waitbar(0,'Optimization iteration progress'); % display progress bar

% Mapping parameter x
row=1;
x_map=zeros(size(grp_rev_type,1),2);
for i=1:size(grp_rev_type,1)
    if grp_rev_type(i)==4 || grp_rev_type(i) ==6 || grp_rev_type(i) ==9
        %dim=2
        x_map(i,:)=[row row+1];
        row=row+2;
    else
        %dim=1
        x_map(i,:)=[row 0];
        row=row+1;
    end
end

% Count number of dimension
no_dim=row-1;
tot_i=0; %counters for each for loop
tot_it=(no_step+1)^no_dim; %total iteration is # of variable * no_step

[dummy3 dummy4 cp_rev_all]=find(grp_members');

ai=1;
for a=-1:2/no_step:1    

    bi=1;
    for b=-1:2/no_step:1

        if no_dim<2
            break

        elseif no_dim==2

            x=[a;b];             
            waitbar(tot_i/tot_it,prog_bar);
            
            % Calculate constraints quality for each increment in the search space
            [Rating_all_rev Ri_specmot mot_specmot_all]=rate_specmot(x,x_map,specmot);
            
            % Collect ratings
            WTR_optim_specmot(ai,bi)=Rating_all_rev(1);
            MRR_optim_specmot(ai,bi)=Rating_all_rev(2);
            MTR_optim_specmot(ai,bi)=Rating_all_rev(3);  
            TOR_optim_specmot(ai,bi)=Rating_all_rev(4);
            
            Ri_specmot_col{:,:,ai,bi}=Ri_specmot;
            Ri_specmot_rowsum{:,:,ai,bi}=sum(Ri_specmot,2);
            mot_specmot_col{:,:,ai,bi}=mot_specmot_all;
            tot_i=tot_i+1;
        end
        bi=bi+1;

    end

    if no_dim<1
        break
    elseif no_dim==1

        x=a;
        waitbar(tot_i/tot_it,prog_bar);

        [Rating_all_rev Ri_specmot mot_specmot_all]=rate_specmot(x,x_map,specmot);

        WTR_optim_specmot(ai)=Rating_all_rev(1);
        MRR_optim_specmot(ai)=Rating_all_rev(2);
        MTR_optim_specmot(ai)=Rating_all_rev(3);
        TOR_optim_specmot(ai)=Rating_all_rev(4);
        
        Ri_specmot_col{:,:,ai}=Ri_specmot;
        Ri_specmot_rowsum{:,:,ai}=sum(Ri_specmot,2);
        mot_specmot_col{:,:,ai}=mot_specmot_all;
        tot_i=tot_i+1;
    end
    ai=ai+1;

end   
close(prog_bar); %close the progress bar
TOR_optim_specmot=MTR_optim_specmot./MRR_optim_specmot;

% The plot procedure below is similar to optim_postproc. See comments in optim_postproc.m

x1_inc=-1:2/no_step:1;
x2_inc=-1:2/no_step:1;

if no_dim==1
    t=x1_inc;
    
    f2=figure('Position',[100,300,640,480]);
    subplot(2,2,1);plot(t,WTR_optim_specmot,'LineWidth',2);xlabel('X1','fontweight','b');ylabel('WTR','fontweight','b');grid on;
    subplot(2,2,2);plot(t,MRR_optim_specmot,'LineWidth',2);xlabel('X1','fontweight','b');ylabel('MRR','fontweight','b');grid on;
    subplot(2,2,3);plot(t,MTR_optim_specmot,'LineWidth',2);xlabel('X1','fontweight','b');ylabel('MTR','fontweight','b');grid on;
    subplot(2,2,4);plot(t,TOR_optim_specmot,'LineWidth',2);xlabel('X1','fontweight','b');ylabel('TOR','fontweight','b');grid on;
    
    saveas(f2,inputfile,'fig') 
    saveas(f2,inputfile,'eps')

elseif no_dim==2
    [u,v]=meshgrid(x1_inc,x2_inc);
    f2=figure('Position',[100,300,640,480]);
    subplot(2,2,1);surf(u,v,WTR_optim_specmot);colormap cool;
    zlabel('WTR','fontweight','b');axis xy;
    xlabel('X2','fontweight','b');
    ylabel('X1','fontweight','b');
    subplot(2,2,2);surf(u,v,MRR_optim_specmot);
    zlabel('MRR','fontweight','b');axis xy;
    xlabel('X2','fontweight','b');
    ylabel('X1','fontweight','b');
    subplot(2,2,3);surf(u,v,MTR_optim_specmot);
    zlabel('MTR','fontweight','b');axis xy;
    xlabel('X2','fontweight','b');
    ylabel('X1','fontweight','b');   
    subplot(2,2,4);surf(u,v,TOR_optim_specmot);
    zlabel('TOR','fontweight','b');axis xy;
    xlabel('X2','fontweight','b');
    ylabel('X1','fontweight','b');
    
    saveas(f2,inputfile,'fig')
    saveas(f2,inputfile,'eps')
end

    
