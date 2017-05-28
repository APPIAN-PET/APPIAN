import pandas as pd
import numpy as np
from Test.test_group_qc import calc_outlier_measures, outlier_measure_roc,plot_outlier_measures, plot_roc,plot_distance_metrics
import Quality_Control as qc
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from math import sqrt
from sys import exit

normal_param='0,0,0'
outlier_measures={'MAD':qc.img_mad}
outlier_threshold={ 'MAD':np.arange(-6,6,0.25)} #[-6,-5,-4,-3,-2.5,-2,-1.5,-1,-0.5,0, 0.5, 1, 1.5, 2, 2.5, 3,4,5,6]}
distance_metrics={'MI':qc.mi, 'CC':qc.cc, 'IV':qc.iv, 'FSE':qc.fse, 'MSE':qc.mse } 
error_type_unit={"angle":"(degrees)",  "offset":'(mm)'} 
error_type_name={"angle":'rotation',  "offset":'translation'} 
colnames=["Subject", "Condition", "ErrorType", "Error", "Metric", "Value"] 

dfa = pd.read_csv('test_group_qc_metric.csv',index_col=False)
dfb = pd.read_csv('test_group_qc_metric_sub16-30.csv', index_col=False)
df = pd.concat([dfa, dfb])
df.to_csv('test_group_qc_metric_sub0-30.csv')
df.index=range(df.shape[0])

#plot_distance_metrics(df,distance_metrics, 'sub0-30_distance_metrics.png', color=cm.spectral)

df2 = calc_outlier_measures(df, outlier_measures, distance_metrics, normal_param)
df2.to_csv('sub0-30_outlier_measures.csv')
#df2=pd.read_csv('sub0-15_outlier_measures.csv')

#plot_outlier_measures(df2, outlier_measures, distance_metrics, "sub0-30_outlier_measures.png")
print df2
df3 = outlier_measure_roc(df2, outlier_threshold, normal_param)
df3.to_csv('sub0-30_roc.csv', index=False)
#df3 = pd.read_csv('sub0-15_roc.csv')
plot_roc(df3, error_type_unit, error_type_name)

