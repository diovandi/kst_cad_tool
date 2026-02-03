% Post-process sensitivity analysis results
% filename: sens_analysis_postproc.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

% Using average
for k=1:total_cp
    
    WTR(:,:)=SAO_WTR(k,:,:);MRR(:,:)=SAO_MRR(k,:,:);MTR(:,:)=SAO_MTR(k,:,:);TOR(:,:)=SAO_TOR(k,:,:);
    WTRO_avg(k)=mean(mean(WTR));
    MRRO_avg(k)=mean(mean(MRR));
    MTRO_avg(k)=mean(mean(MTR));
    TORO_avg(k)=mean(mean(TOR));
    
    WTR(:,:)=SAP_WTR(k,:,:);MRR(:,:)=SAP_MRR(k,:,:);MTR(:,:)=SAP_MTR(k,:,:);TOR(:,:)=SAP_TOR(k,:,:);
    WTRP_avg(k)=mean(mean(WTR));
    MRRP_avg(k)=mean(mean(MRR));
    MTRP_avg(k)=mean(mean(MTR));
    TORP_avg(k)=mean(mean(TOR));
    
end

[WTRO_min WTRO_min_idx]=min(WTRO_avg)
[WTRP_min WTRP_min_idx]=min(WTRP_avg)

% Using worst change
for k=1:total_cp
    
    WTR(:,:)=SAO_WTR(k,:,:);MRR(:,:)=SAO_MRR(k,:,:);MTR(:,:)=SAO_MTR(k,:,:);TOR(:,:)=SAO_TOR(k,:,:);
    WTRO_avg(k)=min(min(WTR));
    MRRO_avg(k)=min(min(MRR));
    MTRO_avg(k)=min(min(MTR));
    TORO_avg(k)=min(min(TOR));
    
    WTR(:,:)=SAP_WTR(k,:,:);MRR(:,:)=SAP_MRR(k,:,:);MTR(:,:)=SAP_MTR(k,:,:);TOR(:,:)=SAP_TOR(k,:,:);
    WTRP_avg(k)=min(min(WTR));
    MRRP_avg(k)=min(min(MRR));
    MTRP_avg(k)=min(min(MTR));
    TORP_avg(k)=min(min(TOR));
    
end

x1_inc=-1:2/no_step:1;
x2_inc=-1:2/no_step:1;
[u,v]=meshgrid(x1_inc,x2_inc);

WTRP(:,:)=SAP_WTR(WTRP_min_idx,:,:);
WTRO(:,:)=SAO_WTR(WTRO_min_idx,:,:);

figure;
surf(u,v,WTRO);colormap cool;
zlabel('WTR Change (%)','fontweight','b');axis xy;
xlabel('X2','fontweight','b');
ylabel('X1','fontweight','b');

figure;
surf(u,v,WTRP);colormap cool;
zlabel('WTR Change (%)','fontweight','b');axis xy;
xlabel('X2','fontweight','b');
ylabel('X1','fontweight','b');
    