import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from glob import glob
from sys import argv
from re import sub,split
from src.qc import outlier_measures
from sklearn.metrics import roc_auc_score

def read_df(out_dir, error_type='rot', df_fn='metric_df.csv', clobber=False) :
    if not os.path.exists(df_fn) or clobber : 
        file_strings=out_dir + '/preproc/_*/*'+error_type+'*_qc_metrics*/*csv'
        files = glob(file_strings)
        
        df_list=[]
        for fn in files :
            df = pd.read_csv(fn)
            fn_split= split('_|/', fn)
            error_level =  float([  sub(error_type+'-', '', x) for x in fn_split if error_type+'-' in x ][0])

            df['error_type']=[error_type]*df.shape[0]
            df['error_level']=error_level
            df_list.append(df)
        df = pd.concat(df_list)
        df.to_csv(df_fn, index=False)
    else :
        df = pd.read_csv(df_fn)
        
    
    return df

def outlier_factor(df, out_fn='outlier_df.csv', n_steps=10, clobber=False):
    if not os.path.exists(out_fn) or clobber :
        df_list=[]
        for metric, df_metric in df.groupby(['metric']):
            df_no_error = df_metric.loc[ df_metric['error_level'] == 0 ]
            df_error = df_metric.loc[ df_metric['error_level'] != -1 ]
            
            for columns, df2 in df_error.groupby(['error_type','error_level','analysis','roi']):
                for (sub,ses), df_sub in df2.groupby(['sub','ses']) :
                    df_test=df_no_error.copy()
                    df_test.loc[(df_test['sub'] == sub) & (df_test['ses']==ses), : ] = df_sub
                    df_test.reset_index(inplace=True)
                    idx= df_test[(df_test['sub'] == sub) & (df_test['ses']==ses)   ].index[0]

                    for name, function in outlier_measures.items() :
                        df_sub['outlier_metric'] = name
                        
                        outlier_values = function(df_test['value'])
                        
                        if type( outlier_values[idx]) == np.ndarray : 
                            x = outlier_values[idx][0]
                        else :
                            x = outlier_values[idx]

                        df_sub['outlier_value'] = x
                        df_list.append(pd.DataFrame({'error_type':columns[0],'error_level':columns[1],'analysis':columns[2],'roi':columns[3],'sub':[sub], 'ses':[ses], 'metric':[metric], 'metric_value':df_sub['value'], 'outlier':[name], 'outlier_value':[x] }))
                        
        outlier_df = pd.concat(df_list)
        outlier_df.to_csv(out_fn,index=False)
    else :
        outlier_df = pd.read_csv(out_fn)

    return outlier_df

def auc(df,auc_fn='auc_df.csv', clobber=True):
    if not os.path.exists(auc_fn) or clobber :
        df_list=[]
        for metric, df2 in df.groupby(['metric','outlier']):
            df_no_error = df2.loc[ df2['error_level'] == 0 ]
            df_error = df2.loc[ df2['error_level'] != -1 ]

            for columns, df3 in df_error.groupby(['error_type','error_level','analysis','roi', 'metric']):
                for (sub,ses), df_sub in df3.groupby(['sub','ses']) :
                    df_test=df_no_error.copy()
                    df_test.index = [2]*df_test.shape[0]
                    df_sub.index = [2]*df_sub.shape[0]
                    sub_idx = (df_test['sub'] == sub) & (df_test['ses']==ses)
                    df_test.loc[sub_idx, : ] = df_sub
                    df_test.reset_index(inplace=True)
                    
                    idx = df_test[(df_test['sub'] == sub) & (df_test['ses']==ses)   ].index[0]
                    
                    y_predicted = df_test['outlier_value'].values
                    
                    y_true = np.zeros(df_test.shape[0])
                    y_true[idx] = 1

                    auc = roc_auc_score(y_true, y_predicted)
                    
                    df_list.append(pd.DataFrame({'error_type':columns[0],'error_level':columns[1],'analysis':columns[2],'roi':columns[3],'sub':[sub], 'ses':[ses], 'metric':df_sub['metric'], 'metric_value':df_sub['metric_value'], 'outlier':df_sub['outlier'], 'outlier_value':df_sub['outlier_value'],'auc':[auc] }))

        auc_df = pd.concat(df_list)
        auc_df.to_csv(auc_fn, index=False)
    else :
        auc_df = pd.read_csv(auc_fn)


    return auc_df

def plot(df):
    g = sns.FacetGrid(df,  row='analysis', col='metric',hue="sub", sharey=False)
    g.map(plt.scatter, "error_level", "metric_value")
    plt.savefig('qc_metric.png') #show()

    g = sns.FacetGrid(df, col="outlier", row='analysis', hue="metric")
    g.map(plt.plot, "error_level", "outlier_value")
    plt.savefig('qc_outlier.png') #show()
    #for (error_type, analysis, metric, outlier), df2  in df.groupby(['error_type','analysis','metric','outlier']):
    #    plt.subplot(n,m,i)
    #    plt.scatter(df2['error_level'])

    df_mean = df.groupby(['error_type','analysis','roi','metric','outlier','error_level']).mean()
    print(df_mean)

if __name__ == '__main__':        
    out_dir = argv[1]
    clobber=False
    df = read_df(out_dir, error_type='rot')
    outlier_df = outlier_factor(df, clobber=clobber)
    auc_df = auc(outlier_df)
    plot(auc_df)
