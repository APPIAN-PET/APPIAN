import pandas as pd
import numpy as np
from Test.test_group_qc import calc_outlier_measures, outlier_measure_roc
import Quality_Control as qc
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from math import sqrt

fn="/data1/projects/scott/test_group_qc_v2_full.csv"

df=pd.read_csv(fn)
df.loc[:,'Score'] *= -1
subjects=np.unique(df.Subject)
n=len(subjects)
n0=n-1.0
z=sqrt((n+n0)/(n*n0))
c={0.2:1.07*z,  0.15:1.14*z, 0.10:1.22*z,0.05:1.36*z, 0.025:1.48*z, 0.01:1.63*z, 0.005:1.73*z, 0.001:1.95*z} 

normal_param='0,0,0'

outlier_measures={'KSD':qc.kolmogorov_smirnov, 'MAD':qc.img_mad}
outlier_threshold={'KSD':[c[0.05], c[0.10], c[0.15], c[0.2]] , 'MAD':[1,2,3,4]}
distance_metrics={'NMI':qc.mi, 'XCorr':qc.xcorr }



outlier_measure_roc(df, outlier_threshold, normal_param)

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
