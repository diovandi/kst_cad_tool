% Generate analysis report
% filename: report.m
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

global totaltime_min totaltime_sec timestart 

fprintf(result,'<b>Input File: %s <p>\n\n</b>',inputfile);

%Print Main Ratings
fprintf(result,'Weakest Total Resistance rating (WTR): %5.4f (LAR: %6.3f)<br>\n',Rating_all_org(1), 1/Rating_all_org(1));
fprintf(result,'Mean Redundancy Ratio (MRR): %5.4f <br>\n',Rating_all_org(2));
fprintf(result,'Mean Total Resistance Rating (MTR): %5.4f (LAR: %6.3f)<br>\n',Rating_all_org(3),1/Rating_all_org(3));
fprintf(result,'Trade Off Ratio (TOR): %5.4f <p>\n\n',Rating_all_org(4));

% Print unconstrained motion if exists
if isempty(free_mot)==0
    fprintf(result,'<b>Unconstrained Motion: </b><br>\n');
    free_mot_idx_dummy=zeros(size(free_mot,1),1);
    dummy=zeros(size(free_mot,1),1);
    table_mot(result, free_mot, dummy);
    return

% Print most weakly constrained motion
else
    fprintf(result,'<b>There is no unconstrained motion. </b><p>\n\n');
    
    fprintf(result,'<p>\n<b>Weakest Constrained Motion (according to WTR): <br></b>\n');
    WTR_mot=mot_all_org_uniq(WTR_idx_org,:);
    TR=rowsum(WTR_idx_org);  
    WTR_cp=best_cp(WTR_idx_org);  
    table_mot(result, WTR_mot, TR); % Print motion in tabular format
end

% Identify best resistance constraints for each motion
for i=1:size(Ri_uniq,2)
    non_zero_cnt_in_col(i)=nnz(Ri_uniq(:,i)); %#ok<AGROW>
    b=find(best_cp==i);
    cp_best_count(i)=size(b,1); %#ok<AGROW> %Counter for # of times a cp provide best resistance
end

%  Individual CP rating
cp_col=1:total_cp;
cp_indv_rat = sum(Ri_uniq,1)./non_zero_cnt_in_col;

% Calculate CA% and CBR%
cp_active_pct=non_zero_cnt_in_col/no_mot*100;
cp_best_pct=cp_best_count./no_mot.*100;

% Merge constarints ratings in a matrix
cp_table=[cp_col', cp_indv_rat', cp_active_pct', cp_best_pct'];

fprintf(result,'<p><TABLE BORDER=2>\n');
fprintf(result,'<b> <FONT SIZE=3 FACE="helvetica"><tr><th>CP#</th>  <th>Individual Rating</th> <th>Active %%</th> <th>Best Resistance %%</th> <tr></b>\n');

% Print constraints' individual ratings
for i=1:size(cp_table,1) 
    fprintf(result,'<tr><td>%d</td>  <td>%5.4f</td>  <td>%4.1f%%</td>  <td>%4.1f%%</td>  </tr>\n',cp_table(i,:));
end

% Print computation information
fprintf(result,'</font></TABLE><p>\n');
total_combo=size(combo,1);
fprintf(result,'Total Possible Combination: %8.0f <br>\n',total_combo);
fprintf(result,'Total Linearly Independent Combination Processed: %8.0f <br>\n\n',size(combo_proc_org,1));
fprintf(result,'Total Unique screw motion found: %8.0f<p>\n\n',size(mot_all_org_uniq,1)./2);


    