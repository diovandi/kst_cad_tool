function []=table_mot(result, mot_list, TR)
% Create a table for screw axis motions
% filename: table_mot.m
% Input variables: result, mot_list, TR
% Output variables: -
% Called functions: -

% Copyright 2008 Leonard Rusli
% The Ohio State University

fprintf(result,'<TABLE BORDER=2>\n');
fprintf(result,'<b> <tr><th>Om(x)</th>  <th>Om(y)</th> <th>Om(z)</th> <th>Mu(x)</th> <th>Mu(y)</th> <th>Mu(z)</th> <th>Rho(x)</th><th>Rho(y)</th><th>Rho(z)</th> <th>Pitch</th>   <th>Total Resistance</th> <tr></b>\n');

for i=1:size(mot_list,1) 
    fprintf(result,'<tr><td>%7.4f</td>  <td>%7.4f</td>  <td>%7.4f</td>  <td>%7.4f</td>  <td>%7.4f</td>  <td>%7.4f</td>  <td>%7.4f</td>  <td>%7.4f</td>  <td>%7.4f</td>  <td>%5.4f</td>    ',...
        mot_list(i,:));
    fprintf(result,'<td>%7.4f</td></tr>\n',TR(i));
end
fprintf(result,'</TABLE>\n');