function optim_postproc(no_step,no_dim, WTR_optim_chg, MRR_optim_chg,...
    MTR_optim_chg, TOR_optim_chg,inputfile)
% Plot the response surface plots
% filename: optim_postproc.m
% Input variables: no_step,no_dim, WTR_optim_chg, MRR_optim_chg, MTR_optim_chg, TOR_optim_chg,inputfile
% Output variables: -
% Called functions: -
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% Prepare x and y axis array
x1_inc=-1:2/no_step:1;
x2_inc=-1:2/no_step:1;

if no_dim==1
    t=x1_inc;
    
    f2=figure('Position',[100,300,640,480]);
    subplot(2,2,1);plot(t,WTR_optim_chg,'LineWidth',2);xlabel('X1');ylabel('WTR Change (%)');grid on;
    subplot(2,2,2);plot(t,MRR_optim_chg,'LineWidth',2);xlabel('X1');ylabel('MRR Change (%)');grid on;
    subplot(2,2,3);plot(t,MTR_optim_chg,'LineWidth',2);xlabel('X1');ylabel('MTR Change (%)');grid on;
    subplot(2,2,4);plot(t,TOR_optim_chg,'LineWidth',2);xlabel('X1');ylabel('TOR Change (%)');grid on;
    
    % Automatically save the figures as fig and eps format
    saveas(f2,inputfile,'fig') 
    saveas(f2,inputfile,'eps')

elseif no_dim==2
    [u,v]=meshgrid(x1_inc,x2_inc);
    f2=figure('Position',[100,300,640,480]);
    subplot(2,2,1);surf(u,v,WTR_optim_chg);colormap cool;
    zlabel('WTR Change (%)');axis xy;
    xlabel('X2');
    ylabel('X1');
    subplot(2,2,2);surf(u,v,MRR_optim_chg);
    zlabel('MRR Change (%)');axis xy;
    xlabel('X2');
    ylabel('X1');
    subplot(2,2,3);surf(u,v,MTR_optim_chg);
    zlabel('MTR Change (%)');axis xy;
    xlabel('X2');
    ylabel('X1');   
    subplot(2,2,4);surf(u,v,TOR_optim_chg);
    zlabel('TOR Change (%)');axis xy;
    xlabel('X2');
    ylabel('X1');
    
    saveas(f2,inputfile,'fig')
    saveas(f2,inputfile,'eps')
    
elseif no_dim==3
    
    % Identify optimums based on different metric
    WTR_max=max(WTR_optim_all(:));
    WTR_max_idx=find(WTR_optim_all(:)==WTR_max);
    [WTR_max_x1 WTR_max_x2 WTR_max_x3]=ind2sub(size(WTR_optim_all),WTR_max_idx);
        
    MRR_max=max(MRR_optim_all(:));
    MRR_max_idx=find(MRR_optim_all(:)==MRR_max);
    [MRR_max_x1 MRR_max_x2 MRR_max_x3]=ind2sub(size(MRR_optim_all),MRR_max_idx);

    MTR_max=max(MTR_optim_all(:));
    MTR_max_idx=find(MTR_optim_all(:)==MTR_max);
    [MTR_max_x1 MTR_max_x2 MTR_max_x3]=ind2sub(size(MTR_optim_all),MTR_max_idx);
    
    TOR_max=max(TOR_optim_all(:));
    TOR_max_idx=find(TOR_optim_all(:)==TOR_max);
    [TOR_max_x1 TOR_max_x2 TOR_max_x3]=ind2sub(size(TOR_optim_all),TOR_max_idx);
    
    % Identify ratings at optimum point based on WTR optimum
    WTR_global_abs=WTR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1));
    WTR_global_chg=WTR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1));
    MRR_global_abs=MRR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1));
    MRR_global_chg=MRR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1));
    MTR_global_abs=MTR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1));
    MTR_global_chg=MTR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1));
    TOR_global_abs=TOR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1));
    TOR_global_chg=TOR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1));
    
elseif no_dim==4
    WTR_max=max(WTR_optim_all(:));
    WTR_max_idx=find(WTR_optim_all(:)==WTR_max);
    [WTR_max_x1 WTR_max_x2 WTR_max_x3 WTR_max_x4]=ind2sub(size(WTR_optim_all),WTR_max_idx);
    
    MRR_max=max(MRR_optim_all(:));
    MRR_max_idx=find(MRR_optim_all(:)==MRR_max);
    [MRR_max_x1 MRR_max_x2 MRR_max_x3 MRR_max_x4]=ind2sub(size(MRR_optim_all),MRR_max_idx);

    MTR_max=max(MTR_optim_all(:));
    MTR_max_idx=find(MTR_optim_all(:)==MTR_max);
    [MTR_max_x1 MTR_max_x2 MTR_max_x3 MTR_max_x4]=ind2sub(size(MTR_optim_all),MTR_max_idx);
    
    TOR_max=max(TOR_optim_all(:));
    TOR_max_idx=find(TOR_optim_all(:)==TOR_max);
    [TOR_max_x1 TOR_max_x2 TOR_max_x3 TOR_max_x4]=ind2sub(size(TOR_optim_all),TOR_max_idx);
    
    WTR_global_abs=WTR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1));
    WTR_global_chg=WTR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1));
    MRR_global_abs=MRR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1));
    MRR_global_chg=MRR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1));
    MTR_global_abs=MTR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1));
    MTR_global_chg=MTR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1));
    TOR_global_abs=TOR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1));
    TOR_global_chg=TOR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1));
    
elseif no_dim==5
    WTR_max=max(WTR_optim_all(:))
    WTR_max_idx=find(WTR_optim_all(:)==WTR_max);
    [WTR_max_x1 WTR_max_x2 WTR_max_x3 WTR_max_x4 WTR_max_x5]=ind2sub(size(WTR_optim_all),WTR_max_idx);
    
    MRR_max=max(MRR_optim_all(:));
    MRR_max_idx=find(MRR_optim_all(:)==MRR_max);
    [MRR_max_x1 MRR_max_x2 MRR_max_x3 MRR_max_x4 MRR_max_x5]=ind2sub(size(MRR_optim_all),MRR_max_idx);

    MTR_max=max(MTR_optim_all(:));
    MTR_max_idx=find(MTR_optim_all(:)==MTR_max);
    [MTR_max_x1 MTR_max_x2 MTR_max_x3 MTR_max_x4 MTR_max_x5]=ind2sub(size(MTR_optim_all),MTR_max_idx);
    
    TOR_max=max(TOR_optim_all(:))
    TOR_max_idx=find(TOR_optim_all(:)==TOR_max);
    [TOR_max_x1 TOR_max_x2 TOR_max_x3 TOR_max_x4 TOR_max_x5]=ind2sub(size(TOR_optim_all),TOR_max_idx);
    
    WTR_global_abs=WTR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1),WTR_max_x5(1));
    WTR_global_chg=WTR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1),WTR_max_x5(1));
    MRR_global_abs=MRR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1),WTR_max_x5(1));
    MRR_global_chg=MRR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1),WTR_max_x5(1));
    MTR_global_abs=MTR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1),WTR_max_x5(1));
    MTR_global_chg=MTR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1),WTR_max_x5(1));
    TOR_global_abs=TOR_optim_all(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1),WTR_max_x5(1));
    TOR_global_chg=TOR_optim_chg(WTR_max_x1(1), WTR_max_x2(1),WTR_max_x3(1),WTR_max_x4(1),WTR_max_x5(1));
    
end


