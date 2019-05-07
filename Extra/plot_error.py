import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from glob import glob
from re import sub
from sys import argv, exit 
from os.path import splitext
import numpy as np
import os

def load(fn):
	df=pd.read_csv(fn)
	return(df)

def plot(df0, df, tracer) :
	out_fn = tracer + ".png"	
	plt.clf()
	sns.stripplot(x="roi", y="value", hue="sub", data=df, jitter=True, alpha=.6, zorder=1) 
	sns.pointplot(x="roi", y="value", data=df0, join=False, palette="dark", markers="d", scale=1.5)
	plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
	plt.savefig(out_fn)

def get_qc_metrics():
	fn_list = []
	df_list = []
	fn_list += glob("raclopride/out_rcl/groupLevelQC/coreg_roc/test_group_qc_auc.csv")
	#fn_list += glob("scott/out_fdg/groupLevelQC/coreg_roc/test_group_qc_auc.csv")
	#fn_list += glob("fmz/out_fmz/groupLevelQC/coreg_roc/test_group_qc_auc.csv")
	for fn in fn_list :
		temp=pd.read_csv(fn)
        print fn		
        args = fn.split("/")[4].split("_")
        if 'rcl' in fn : temp["tracer"] = ["rcl"] * temp.shape[0]
        elif 'fdg' in fn : temp["tracer"] = ["fdg"] * temp.shape[0]
        elif 'fmz' in fn : temp["tracer"] = ["fmz"] * temp.shape[0]
		#temp["frame"] = [0] * temp.shape[0]
		#temp["errortype"] = [args[1]] * temp.shape[0]
		#temp["error"] = [int(args[2])] * temp.shape[0]
        df_list += [temp]
	df = pd.concat(df_list)
	return(df)

def get_error():
	fn_list=[]
	fn_list += glob("fmz/out_fmz/preproc/_args_**/_angle_**/**/*_3d.csv")
	fn_list += glob("scott/out_fdg/preproc/_args_**/_angle_**/**/*_3d.csv")
	fn_list += glob("raclopride/out_rcl/preproc/_args_**/_angle_**/**/*_3d.csv")
	df_list = []
	for fn in fn_list :
		temp=pd.read_csv(fn)
		args = fn.split("/")[4].split("_")
		if 'rcl' in fn : temp["tracer"] = ["rcl"] * temp.shape[0]
		elif 'fdg' in fn : temp["tracer"] = ["fdg"] * temp.shape[0]
		elif 'fmz' in fn : temp["tracer"] = ["fmz"] * temp.shape[0]
		temp["frame"] = [0] * temp.shape[0]
		temp["errortype"] = [args[1]] * temp.shape[0]
		temp["error"] = [int(args[2])] * temp.shape[0]
		df_list += [temp]
	df = pd.concat(df_list)
	df["metric"].loc[ (df["tracer"] == "fmz") & (df["metric"] == "mean")] = "BPnd"
	df["metric"].loc[ (df["tracer"] == "fdg") & (df["metric"] == "mean")] = "Ki"
	df["metric"].loc[ (df["tracer"] == "rcl") & (df["metric"] == "mean")] = "BPnd"
	df["roi"].loc[ (df["tracer"] == "rcl") ]   = "Putamen"
	df["roi"].loc[ (df["tracer"] == "fmz") ] = "GM"
	df["roi"].loc[ (df["tracer"] == "fdg") ]   = "GM" 

	df.index = range(df.shape[0])
	df["%Accuracy"]= [0] * df.shape[0]   
	for name, df0 in df.groupby(['tracer','analysis', 'error', 'ses', 'task', 'sub', 'roi']) :
		sub=name[5]
		ses=name[3]
		task=name[4]
		error=name[2]
		idx =  (df.tracer == name[0]) & (df.analysis == name[1]) &  (df.ses == name[3]) & (df.task == name[4]) & (df.roi == name[6]) & (df["sub"] == name[5])
		zeros_df =  df.loc[ (df.tracer == name[0]) & (df.analysis == name[1]) &  (df.ses == name[3]) & (df.task == name[4]) & (df.roi == name[6]) & (df.error == 0) & (df["sub"] == name[5]) ]
		values = df0["value"].mean()
		zeros  = zeros_df["value"].mean()
		ratio = values / zeros
		df["%Accuracy"].loc[(df["error"] == name[2]) & idx] =  ratio
	return(df)

df_fn = os.getcwd() + os.sep + 'appian_error.csv'
qc_fn = os.getcwd() + os.sep + 'appian_qc.csv'

if not os.path.exists(df_fn) :
	df = get_error()
	df.to_csv(df_fn)
else : 
	df = pd.read_csv(df_fn)

if not os.path.exists(qc_fn) :
	qc = get_qc_metrics()
	qc.to_csv(qc_fn)
else : 
	qc = pd.read_csv(qc_fn)

print(qc)


exit(0)
df_mean = df.groupby(["analysis","tracer","error","errortype","frame","metric","roi"])["%Accuracy"].mean()
df_mean = df_mean.reset_index()
df_mean["tracer"].loc[ (df_mean["tracer"] == "rcl") ]   = "RCL"
df_mean["tracer"].loc[ (df_mean["tracer"] == "fdg") ]   = "FDG"
df_mean["tracer"].loc[ (df_mean["tracer"] == "fmz") ]   = "FMZ"
df_mean["analysis"].loc[ (df_mean["analysis"] == "tka") ]   = "TKA"
df_mean["analysis"].loc[ (df_mean["analysis"] == "pvc") ]   = "PVC"
df_mean["analysis"].loc[ (df_mean["analysis"] == "pet-coregistration") ]   = "Coregistration"
print df_mean
plt.clf()
plt.figure()
nTracer = len(df["tracer"].unique())
nROI= len(df["analysis"].unique())
i=1
df.rename(index=str, columns={"roi":"ROI","analysis":"Analysis","tracer":"Radiotracer"}, inplace=True)
sns.factorplot(x="error", y="%Accuracy", col="analysis", hue="tracer",  palette="muted",kind="swarm",col_order=['Coregistration','PVC','TKA'], sharey=True, data=df_mean)
		#for name, df3 in df2.groupby(['sub']) : 
		#	print df3
		#	sns.swarmplot(x="roi", y='groundtruth',data=df3, palette="bright")
		#	break
	
#ax = sns.factorplot(x="roi", y="diff", row="roi", hue="analysis",  data=df, palette="Set2", dodge=True)
#grid = sns.FacetGrid(df_mean, row="tracer", col="analysis", sharey=True, palette="muted", size=5)	
#grid = grid.map(plt.scatter, "roi", "value")
#grid = grid.map(plt.scatter, "groundtruth", "value")

plt.savefig("appian_error.png")

