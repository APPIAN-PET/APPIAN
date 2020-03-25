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
from argparse import ArgumentParser

def read_df(out_dir, error_type='rot', df_fn='metric_df.csv', clobber=False) :
    if not os.path.exists(df_fn) or clobber : 
        file_strings=out_dir + '/preproc/_*/*'+error_type+'*_qc_metrics*/*csv'
        files = glob(file_strings)
        
        df_list=[]
        for fn in files :
            df0 = pd.read_csv(fn)
            for metric, df in df0.groupby(['metric']) :
                
                fn_split= split('_|/', fn)
                error_level =  np.array( [ sub(error_type+'-', '', x).split('-') for x in fn_split if error_type+'-' in x ]).astype(float)[0]
                for i, dim in enumerate(['x','y','z']) :
                    df2 = df.copy()
                    df2['error_type']=[error_type]*df2.shape[0]
                    df2['error_level']=error_level[i]
                    df2['axis']=dim
                    df_list.append(df2)
        df = pd.concat(df_list)
        df.to_csv(df_fn, index=False)
    else :
        df = pd.read_csv(df_fn)
        
    
    return df

def outlier_factor(df, out_fn='outlier_df.csv', n_steps=10, axis_list=['x'], clobber=False):
    if not os.path.exists(out_fn) or clobber :
        df_list=[]
        for (metric, axis), df_metric in df.groupby(['metric','axis']):
            if not axis in axis_list : continue

            df_no_error = df_metric.loc[ df_metric['error_level'] == 0 ]
            df_error = df_metric.loc[ df_metric['error_level'] != -1 ]
            
            for columns, df2 in df_error.groupby(['error_type','error_level','analysis','roi']):
                for sub_idx, df_sub in df2.groupby(['sub_idx']) :
                    df_test=df_no_error.copy()
                    metric_list = df_test['value'].values 
                    metric_list[ df_test['sub_idx'] == sub_idx ] = df_sub['value'].values

                    idx=np.arange(df_test.shape[0])[ df_test['sub_idx'] == sub_idx  ].astype(int)   #df_test[(df_test['sub'] == sub) & (df_test['ses']==ses)   ].index[0]

                    for name, function in outlier_measures.items() :
                        df_sub['outlier_metric'] = name
                        
                        outlier_values = function(metric_list)

                        
                        if type( outlier_values[idx]) == np.ndarray or type( outlier_values[idx]) == list : 
                            x = float(outlier_values[idx][0])
                        else :
                            x = outlier_values[idx]
                        #if name == 'KDE'     :
                        #    print(outlier_values.shape)
                        #    print(type(outlier_values), type( outlier_values[idx]) == np.ndarray)
                        #    print(outlier_values[idx])
                        #    print(x)
                        df_sub['outlier_value'] = x
                        df_list.append(pd.DataFrame({'error_type':columns[0],'error_level':columns[1],'analysis':columns[2],'roi':columns[3],'sub_idx':[sub_idx], 'metric':[metric], 'metric_value':df_sub['value'], 'outlier':[name], 'outlier_value':[x], 'axis':[axis] }))
                        
        outlier_df = pd.concat(df_list)
        outlier_df.to_csv(out_fn,index=False)
    else :
        outlier_df = pd.read_csv(out_fn)

    return outlier_df

def auc(df,auc_fn='auc_df.csv', clobber=False):
    if not os.path.exists(auc_fn) or clobber :
        df_list=[]
        for metric, df2 in df.groupby(['metric','outlier']):
            df_no_error = df2.loc[ df2['error_level'] == 0 ]
            df_error = df2.loc[ df2['error_level'] != -1 ]

            for columns, df3 in df_error.groupby(['error_type','error_level','analysis','roi', 'metric', 'axis']):
                for sub_ses, df_sub in df3.groupby(['sub_idx']) :
                    df_test=df_no_error.copy()
                    df_test.index = [2]*df_test.shape[0]
                    df_sub.index = [2]*df_sub.shape[0]
                    sub_idx = df_test['sub_idx'] == sub_ses
                    df_test.loc[sub_idx, : ] = df_sub
                    df_test.reset_index(inplace=True)
                    
                    idx = df_test[df_test['sub_idx'] == sub_idx   ].index[0]
                    
                    y_predicted = df_test['outlier_value'].values
                    
                    y_true = np.zeros(df_test.shape[0])
                    y_true[idx] = 1

                    auc = roc_auc_score(y_true, y_predicted)
                    
                    df_list.append(pd.DataFrame({'error_type':columns[0],'error_level':columns[1],'analysis':columns[2],'roi':columns[3],'axis':[columns[5]],'sub_idx':[sub_idx], 'metric':df_sub['metric'], 'metric_value':df_sub['metric_value'], 'outlier':df_sub['outlier'], 'outlier_value':df_sub['outlier_value'],'auc':[auc] }))

        auc_df = pd.concat(df_list)
        auc_df.to_csv(auc_fn, index=False)
    else :
        auc_df = pd.read_csv(auc_fn)


    return auc_df

def plot(df, out_fn='df.png', variables=['outlier','metric'], y='outlier_value', row='outlier', col='metric', hue='sub' ):
    df_mean = df.groupby(['axis', 'error_type','analysis','roi'] + variables + ['error_level']).mean()
    print(df_mean)
    plt.figure(figsize=(8,12))
    g = sns.FacetGrid(df, row=row, col=col, hue=hue, sharey=False)
    g.map(plt.plot, "error_level", y)
    plt.savefig(out_fn)


if __name__ == '__main__':        
    parser = ArgumentParser(usage="useage: ")
    parser.add_argument("-s","--source","--sourcedir",dest="sourceDir",  help="Path for input file directory", required=True)
    parser.add_argument("-c","--clobber", dest="clobber", action='store_true', help="Clobber", default=False)
    parser.add_argument("-a","--axis", dest="axis", type=str, help="Error Axis", default='x')
    
    args = parser.parse_args() 

    out_dir = args.sourceDir
    clobber= args.clobber
    axis = args.axis

    metric_df = read_df(out_dir, error_type='rot', clobber=clobber)
    metric_df = metric_df.loc[metric_df['axis']==axis]
    metric_df = metric_df.loc[metric_df['metric']=='MattesMutualInformation']
    metric_df['sub_idx']= metric_df['sub'].astype(str) +'_'+metric_df['ses']

    plot(metric_df, variables=['sub_idx'], out_fn='qc_metric.png', y='value', col='metric', row='analysis',hue='sub_idx' )

    outlier_df = outlier_factor(metric_df, clobber=clobber)
    print(outlier_df)
    exit(0)
    plot(outlier_df, variables=['sub_idx','metric'], out_fn='qc_outlier.png', y='outlier_value', col='outlier',row='metric', hue='sub_idx' )

    auc_df = auc(outlier_df, clobber=clobber)
    plot(auc_df, variables=['metric','outlier'], y='auc', col='outlier', hue='metric', out_fn='qc_auc.png' )
