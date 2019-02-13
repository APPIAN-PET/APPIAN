import pandas as pd
import numpy as np
from Test.test_group_qc import calc_outlier_measures, outlier_measure_roc,plot_outlier_measures, plot_roc,plot_distance_metrics, lof
import Quality_Control as qc
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from math import sqrt
from sys import exit

normal_param='0 0 0'
#outlier_measures={'MAD':qc.img_mad}
#outlier_threshold={ 'MAD':np.arange(-6,6,0.25)} #[-6,-5,-4,-3,-2.5,-2,-1.5,-1,-0.5,0, 0.5, 1, 1.5, 2, 2.5, 3,4,5,6]}
distance_metrics={'MI':qc.mi, 'FSE':qc.fse , 'IECC':qc.iecc, 'CC':qc.cc }  
distance_metrics={'MI':qc.mi, 'FSE':qc.fse }  
outlier_measures={"LOF": lof} 
outlier_threshold={"LOF":np.arange(0,1,0.05) } 
colnames=["Subject", "Condition", "ErrorType", "Error", "Metric", "Value"] 

df = pd.read_csv('/data1/projects/fmz/out_nuc/preproc/test_group_coreg_qc/outlier_measures/test_group_qc_outliers.csv',index_col=False)

df2 = outlier_measure_roc(df, outlier_threshold, normal_param)


df = pd.read_csv('/data1/projects/fmz/out_nuc/preproc/concat_dist_metrics/GPI_distance_metrics.csv',index_col=False)
#df = pd.read_csv('/data1/projects/scott/out2/preproc/concat_dist_metrics/t1_distance_metrics.csv',index_col=False)

df3 = df.pivot_table(rows=['Subject', 'Condition', 'ErrorType', 'Error'], cols='Metric', values='Value')
SUB='sub01'
SUB='P01'
n = len( np.unique(df.Metric))

#Normalize distance metric columns
for i in range(n):
        print np.mean( df3.iloc[:,i] ), np.std( df3.iloc[:,i] ) 
        df3.iloc[:,i] = (df3.iloc[:,i] - np.mean( df3.iloc[:,i] )) / np.std( df3.iloc[:,i] ) 
C = pd.DataFrame( np.corrcoef(df3.values.T),index=df3.columns, columns=df3.columns)
print C

dfa = pd.DataFrame([])
newCols= [ x in distance_metrics.keys() for x in df3.columns ]
dfa = df3.loc[:, newCols ]
dfa.reset_index(inplace=True)

### Outlier for all metrics

#temp_df = dfa[  ( dfa.ErrorType == 'angle'  ) & ((dfa.Error == '0,0,8') | (dfa.Error == '0,0,0')) ]
temp_df = dfa[ ( dfa.ErrorType == 'angle'  ) & (((dfa.Subject == SUB) &  (dfa.Error == '0,0,8')) | ((dfa.Subject != SUB) & (dfa.Error == '0,0,0'))) ]

temp_df['MI']=temp_df.FSE * 2
temp_df = pd.melt(temp_df, id_vars=['Subject','Condition','ErrorType','Error'], value_vars=['FSE','MI'], value_name='Value')
#temp_df.columns[5]='Value'
print temp_df
#df2base = calc_outlier_measures(temp_df, outlier_measures, distance_metrics, normal_param)
#temp_df['LOF'] = lof(temp_df.iloc[:,4:6])
#df2base.to_csv('/data1/projects/fmz/temp/df2base_'+name+'.csv',index=False)
#print df2base
#[roc_df,auc_df] = outlier_measure_roc(df2base, outlier_threshold, normal_param)   
#print temp_df[temp_df.Subject == SUB ]

### Outlier for each metric individually
#for name, metric in distance_metrics.items():
#    temp_distance_metrics = {name:metric}
    #temp_df = df[ ( df.ErrorType == 'angle'  ) & ( df.Metric == name ) & (((df.Subject == 'sub01') &  (df.Error == '0,0,8')) | (df.Error == '0,0,0')) ]
    #temp_df = dfa[ ( dfa.ErrorType == 'angle'  ) & ( dfa.Metric == name ) & (((dfa.Subject == 'sub01') &  (dfa.Error == '0,0,8')) | ((df.Subject != 'sub01') & (dfa.Error == '0,0,0'))) ]
#    print name
#    temp_df['LOF'] = lof( temp_df[name] )
#    print temp_df[ temp_df.Subject == SUB ]
df2 = calc_outlier_measures(temp_df, outlier_measures, distance_metrics, normal_param)
print df2
#    df2.to_csv('/data1/projects/fmz/temp/df2_'+name+'.csv',index=False)
    #print df2
#    [ roc_df, auc_df ] = outlier_measure_roc(df2, outlier_threshold, normal_param)
#    print auc_df.AUC
#    auc_df.to_csv('/data1/projects/fmz/temp/'+name+'.csv',index=False)


#df2.to_csv('sub0-30_outlier_measures.csv')
#df2=pd.read_csv('sub0-15_outlier_measures.csv')

#plot_outlier_measures(df2, outlier_measures, distance_metrics, "sub0-30_outlier_measures.png")
#print df2
#df3 = outlier_measure_roc(df2, outlier_threshold, normal_param)
#df3.to_csv('sub0-30_roc.csv', index=False)
#df3 = pd.read_csv('sub0-15_roc.csv')
#plot_roc(df3, error_type_unit, error_type_name)

