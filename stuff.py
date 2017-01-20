import pandas as pd
import numpy as np
from Test.test_group_qc import calc_outlier_measures, outlier_measure_roc,plot_outlier_measures, plot_roc
import Quality_Control as qc
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from math import sqrt
from sys import exit

if True:
    label='v2' #sub01_no_brain_mask
    home_dir="/data1/projects/ohbm2017/"
    test_group_qc_csv=home_dir+"test_group_qc_"+label+"_metric.csv"
    test_group_qc_full_csv=home_dir+"test_group_qc_"+label+"_outliers.csv"
    test_group_qc_roc_csv=home_dir+"test_group_qc_"+ label+"_roc.csv"


    df=pd.read_csv(test_group_qc_full_csv)
    #df_roc=pd.read_csv(test_group_qc_roc_csv)

    #df.loc[:,'Score'] *= -1
    #subjects=np.unique(df.Subject)
    #n=len(subjects)
    #n0=n-1.0
    #z=sqrt((n+n0)/(n*n0))
    #c={0.2:1.07*z,  0.15:1.14*z, 0.10:1.22*z,0.05:1.36*z, 0.025:1.48*z, 0.01:1.63*z, 0.005:1.73*z, 0.001:1.95*z} 

    normal_param='0,0,0'


    outlier_measures={'MAD':qc.img_mad}
    distance_metrics={'NMI':qc.mi} #, 'XCorr':qc.xcorr }
    error_type_unit={"angle":"(degrees)",  "offset":'(mm)'} 
    error_type_name={"angle":'rotation',  "offset":'translation'} 
    min_mad=int(df.Score.min())
    max_mad=int(df.Score.max())
    step=0.2
    range_mad=np.arange(min_mad, max_mad+step, step)
    print range_mad 
    outlier_threshold={ 'MAD':range_mad}

    metric_df=pd.read_csv(test_group_qc_csv)
    metric_df.drop_duplicates(inplace=True)
    metric_df = metric_df[ ~ metric_df.Subject.isin(['C03', 'C04', 'C06', 'C07', 'C08']) ]
    metric_df.index=range(metric_df.shape[0])

    df=calc_outlier_measures(metric_df, outlier_measures, distance_metrics, normal_param)

    roc_df=outlier_measure_roc(df, outlier_threshold, normal_param)
    print df.Subject.unique()

    #plot_outlier_measures(df, outlier_measures, distance_metrics)


    #plot_roc(roc_df, error_type_unit, error_type_name)

plt.clf()
f = lambda  x : str(x).split(',')[-1]
c1 = df[ (df.Subject == "C01") & (df.ErrorType == "angle" ) ]
c1.Error=c1.Error.apply(f)  

fig, ax1 = plt.subplots(figsize=(13.5, 3))
ax1.scatter(range(c1.shape[0]),  list( c1.Value.values), c="b",  edgecolors="b" )
ax1.plot(range(c1.shape[0]), list( c1.Value.values), "b" )
ax1.set_xlabel('Angle (degrees) of rotation', fontsize=16)
ax1.set_ylabel('NMI', color='blue', fontsize=16)
ax1.set_xlim(0,int(c1.Error.max())-2 )
for tl in ax1.get_yticklabels():
        tl.set_color('b')

ax2 = ax1.twinx()
ax2.scatter( range(c1.shape[0]),list(c1.Score.values), c="g", edgecolors="g")
ax2.plot(range(c1.shape[0]), list(c1.Score.values), "g")
ax2.set_ylabel('MAD', color='green', fontsize=16)
ax2.set_xlim(0,int(c1.Error.max())-2 )
for tl in ax2.get_yticklabels():
        tl.set_color('g')


plt.xticks(range(c1.Score.shape[0]), c1.Error, size='small')
plt.tight_layout()
plt.savefig('/data1/projects/ohbm2017/c1.png')

'''
fn="/data1/projects/scott/test_group_qc.bkp.csv"
fn_full="/data1/projects/scott/test_group_qc_full.bkp.csv"
df=pd.read_csv(fn)
import ipdb; 


outlier_measures={'KSD':qc.kolmogorov_smirnov, 'MAD':qc.img_mad}
distance_metrics={'NMI':qc.mi, 'XCorr':qc.xcorr }



df=calc_outlier_measures(df, outlier_measures, distance_metrics)
df.to_csv(fn_full)

f=lambda x: float(x.split(',')[-1])

df.Error = df.Error.apply(f)
color=cm.spectral
nUnique=float(len(df.Subject.unique()))
d = {key : color(value/nUnique) for (value, key) in enumerate(df.Subject.unique()) }

nMetric=2
nMeasure=2
ax_list=[]
measures=[ 'KSD', 'MAD'  ]
nErrorType=len(np.unique(df.ErrorType))

fig=plt.figure(1)
fig.suptitle('Outlier detection of misaligned PET images')

n=1
for key, group in df.groupby(['ErrorType']):
    for measure in measures:    
        ax=plt.subplot(nMeasure,nErrorType,n)
        ax.set_title('Outlier detection based on '+measure)
        ax.set_ylabel(measure)
        ax.set_xlabel('Error in '+key)

        for key2, group2 in group.groupby(['Subject']):
            ax.plot(group2.Error, group2[measure], c=d[key2])
        n+=1
plt.show()
'''
