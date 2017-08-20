# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 mouse=a
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                     BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import pyminc.volumes.factory as pyminc
from sklearn.metrics import normalized_mutual_info_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import ks_2samp
from scipy.stats.stats import pearsonr, kendalltau  
import numpy as np
import pandas as pd
import fnmatch
import os
from math import sqrt, log, ceil
from os import getcwd
from os.path import basename
from sys import argv, exit
from itertools import product

from Quality_Control.outlier import lof, kde, MAD, lcf

####################
# Distance Metrics #
####################
__NBINS=-1
import copy
def distance(pet_fn, mri_fn, t1_brain_fn, pet_brain_fn, dist_f_list):
	pet = pyminc.volumeFromFile(pet_fn)
	mri = pyminc.volumeFromFile(mri_fn)
	t1_mask= pyminc.volumeFromFile(t1_brain_fn)
	pet_mask= pyminc.volumeFromFile(pet_brain_fn)

	pet_data=pet.data.flatten()
	mri_data=mri.data.flatten()
	t1_mask_data=t1_mask.data.flatten()
	pet_mask_data=pet_mask.data.flatten()

	n=len(pet_data)
	overlap =  t1_mask_data * pet_mask_data
	masked_pet_data = [ pet_data[i] for i in range(n) if int(overlap[i])  == 1 ] 
	masked_mri_data = [ mri_data[i] for i in range(n) if  int(overlap[i]) == 1 ] 
	del pet
	del mri
	del t1_mask
	del pet_mask
	del t1_mask_data
	del pet_mask_data
	dist_list=[]
	for dist_f in dist_f_list:
		dist_list.append(dist_f(masked_pet_data, masked_mri_data))
	return(dist_list)

def mse(masked_pet_data, masked_mri_data):
    mse=-(np.sum(( np.array(masked_pet_data) - np.array(masked_mri_data))**2) / len(masked_pet_data))
    return mse

def mi(masked_pet_data, masked_mri_data):
    masked_pet_data = [int(round(x)) for x in masked_pet_data ]
    masked_mri_data = [int(round(x)) for x in masked_mri_data ]
    
    pet_nbins=find_nbins(masked_pet_data)
    mri_nbins=find_nbins(masked_mri_data)
    #nmi = normalized_mutual_info_score(masked_pet_data,masked_mri_data)
    p, pet_bins, mri_bins=joint_dist(masked_pet_data, masked_mri_data,pet_nbins, mri_nbins )
    mri_dist = np.histogram(masked_mri_data, mri_nbins)
    mri_dist = np.array(mri_dist[0], dtype=float) / np.sum(mri_dist[0])
    pet_dist = np.histogram(masked_pet_data, pet_nbins)
    pet_dist = np.array(pet_dist[0], dtype=float) / np.sum(pet_dist[0])
    mi=sum(p*np.log2(p/(pet_dist[pet_bins] * mri_dist[mri_bins]) ))
    
    print "MI:", mi
    return(mi)


def cc(masked_pet_data, masked_mri_data):
    ###Ref: Studholme et al., (1997) Medical Physics 24, Vol 1
    pet_nbins=find_nbins(masked_pet_data)*2 #len(masked_mri_data) /2 #/4 #1000 #len(masked_mri_data)/10
    mri_nbins=find_nbins(masked_mri_data)*2

    cc=0.0
    xd=0.0
    yd=0.0
    p=joint_dist(masked_pet_data, masked_mri_data,pet_nbins, mri_nbins )[0]

    pet_mean=np.mean(masked_pet_data)
    mri_mean=np.mean(masked_mri_data)
    xval=(masked_pet_data-pet_mean)
    yval=(masked_mri_data-mri_mean)
    num = np.sum( xval * yval * p)
    xd = np.sum( p * xval**2)
    yd = np.sum( p * yval**2)
    den=sqrt(xd*yd)
    cc = abs(num / den)
    #r=pearsonr(masked_pet_data, masked_mri_data)[0]

    #print 'CC0:', r
    print "CC = " + str(cc)

    return(cc)

def iecc(masked_pet_data, masked_mri_data):
    masked_pet_data = [int(round(x)) for x in masked_pet_data ]
    masked_mri_data = [int(round(x)) for x in masked_mri_data ]
    
    pet_nbins=find_nbins(masked_pet_data)
    mri_nbins=find_nbins(masked_mri_data)
    #nmi = normalized_mutual_info_score(masked_pet_data,masked_mri_data)
    p, pet_bins, mri_bins=joint_dist(masked_pet_data, masked_mri_data,pet_nbins, mri_nbins )
    mri_dist = np.histogram(masked_mri_data, mri_nbins)
    mri_dist = np.array(mri_dist[0], dtype=float) / np.sum(mri_dist[0])
    pet_dist = np.histogram(masked_pet_data, pet_nbins)
    pet_dist = np.array(pet_dist[0], dtype=float) / np.sum(pet_dist[0])
    num=p*np.log2( p / (pet_dist[pet_bins] * mri_dist[mri_bins]) )
    den=pet_dist[pet_bins]*np.log2(pet_dist[pet_bins]) + mri_dist[mri_bins]*np.log2(mri_dist[mri_bins])
    iecc = np.sum(num / den) 
    print "IEEC:", num, '/', den, '=', iecc
    return(iecc)

def ec(masked_pet_data, masked_mri_data):
    ###Ref: Kalinic, 2011. A novel image similarity measure for image registration. IEEE ISPA
    pet_mean=np.mean(masked_pet_data)
    mri_mean=np.mean(masked_mri_data)
    xval=np.exp(masked_pet_data-pet_mean)-1
    yval=np.exp(masked_mri_data-mri_mean)-1
    ec = np.sum((xval*yval)) / (len(xval) * len(yval))
    print "EC = " + str(ec)

    return(ec)

def iv(masked_pet_data, masked_mri_data):
    ###Ref: Studholme et al., (1997) Medical Physics 24, Vol 1
    pet_nbins=find_nbins(masked_pet_data)
    mri_nbins=find_nbins(masked_mri_data)

    p, pet_bin, mri_bin=joint_dist(masked_pet_data, masked_mri_data, pet_nbins, mri_nbins)
    df=pd.DataFrame({ 'Value':masked_pet_data , 'p':p, 'Label':mri_bin})


    #Intensity variation:
    #
    #              p(n,m)(n - mean{n}(m))^2
    #sum{sqrt(sum[ ------------------------ ]) * p(m)}
    #                   mean{n}(m)^2
    #


    # 1)
    #      p(n,m)(n - mean{n}(m))^2
    # X =  ------------------------
    #           mean{n}(m)^2
    df["Normed"]=df.groupby(["Label"])['Value'].transform( lambda x: (x - x.mean())**2 / x.mean()**2 ) * df.p

    # 2)
    #          
    #sum{sqrt(sum[ X ]) * p(m)}
    #
    mri_dist = np.histogram(masked_mri_data, mri_nbins)
    mri_dist = np.array(mri_dist[0], dtype=float) / np.sum(mri_dist[0])
    iv = - float(np.sum(df.groupby(["Label"])["Normed"].agg( {'IV': lambda x: sqrt(x.sum()) } ) * mri_dist[0]))
    print "IV:", iv
    return iv

def fse(masked_pet_data, masked_mri_data):
    ###Ref: Studholme et al., (1997) Medical Physics 24, Vol 1
    pet_nbins=find_nbins(masked_pet_data)
    mri_nbins=find_nbins(masked_mri_data)

    p, pet_bin, mri_bin=joint_dist(masked_pet_data, masked_mri_data, pet_nbins, mri_nbins)
    fse=-np.sum(p*map(np.log, p))
    print "FSE:", fse
    return fse




def joint_dist(masked_pet_data, masked_mri_data, pet_nbins, mri_nbins):
    #return joint probability for pair of pet and mri value
    n=len(masked_pet_data)
    h=np.histogram2d(masked_pet_data, masked_mri_data, [pet_nbins, mri_nbins])
    #print h
    nbins = h[0].shape[0] * h[0].shape[1]
    hi= np.array(h[0].flatten() / sum(h[0].flatten()) ).reshape( h[0].shape)
    #Binarized PET data
    x_bin = np.digitize(masked_pet_data, h[1]) - 1
    #Binarized MRI data
    y_bin = np.digitize(masked_mri_data, h[2]) - 1
    #Reduce max bins by 1
    x_bin[x_bin >= h[0].shape[0] ]=h[0].shape[0]-1
    y_bin[y_bin >= h[0].shape[1] ]=h[0].shape[1]-1

    pet_bin=x_bin
    mri_bin=y_bin
    x_idx=x_bin #v[:,0]
    y_idx=y_bin #v[:,1]
    p=hi[x_idx,y_idx]

    return [p, pet_bin, mri_bin]

def find_nbins(array):
    r=float(max(array)) - min(array)
    
    n=ceil(-np.log2(16/r))
    return n


###########
# Globals #
###########

distance_metrics={'MI':mi, 'FSE':fse, 'CC':cc }  

outlier_measures={"KDE":kde } #{'LCF':lcf, "KDE":kde , 'MAD':MAD} #, 'LCF':lcf}

#########
# Nodes #
#########

class calc_distance_metricsOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class calc_distance_metricsInput(BaseInterfaceInputSpec):
    pet = traits.File(exists=True, mandatory=True, desc="Input PET image")
    t1 = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    t1_brain_mask = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    pet_brain_mask = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    sid = traits.Str(desc="Subject")
    ses = traits.Str(desc="Session")
    task = traits.Str(desc="Task")
    study_prefix = traits.Str(desc="Study Prefix")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)

class calc_distance_metricsCommand(BaseInterface):
    input_spec = calc_distance_metricsInput 
    output_spec = calc_distance_metricsOutput
  
    def _gen_output(self, sid, ses, task, fname ="distance_metric.csv"):
        dname = os.getcwd() 
        return dname + os.sep +'sub-'+ sid + '_ses-' + ses + '_task-' + task + '_' + fname

    def _run_interface(self, runtime):
        colnames=["Subject", "Session","Task", "Metric", "Value"] 
        sub_df=pd.DataFrame(columns=colnames)
        pet = self.inputs.pet
        t1 = self.inputs.t1
        sid = self.inputs.sid
        ses = self.inputs.ses
        task = self.inputs.task
        t1_brain_mask = self.inputs.t1_brain_mask
        pet_brain_mask = self.inputs.pet_brain_mask

        path, ext = os.path.splitext(pet)
        base=basename(path)
        param=base.split('_')[-1]
        param_type=base.split('_')[-2]

        mis_metric=distance(pet, t1, t1_brain_mask, pet_brain_mask, distance_metrics.values())

        df=pd.DataFrame(columns=colnames)
        for m,metric_name,metric_func in zip(mis_metric, distance_metrics.keys(), distance_metrics.values()):
            temp=pd.DataFrame([[sid,ses,task,metric_name,m]],columns=df.columns  ) 
            sub_df = pd.concat([sub_df, temp])
        
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output(self.inputs.sid, self.inputs.ses, self.inputs.task)
        
        sub_df.to_csv(self.inputs.out_file,  index=False)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output( self.inputs.sid, self.inputs.cid,)

        outputs["out_file"] = self.inputs.out_file
        return outputs

class calc_outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class calc_outlier_measuresInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)

class calc_outlier_measuresCommand(BaseInterface):
    input_spec = calc_outlier_measuresInput 
    output_spec = calc_outlier_measuresOutput
  
    def _gen_output(self, fname ="coreg_measures.csv"):
        dname = os.getcwd() + os.sep + fname
        return dname

    def _run_interface(self, runtime):
		df = pd.read_csv( self.inputs.in_file  )
		#out_columns=['Subject','Session','Task', 'Measure','Metric', 'Value']
		out_columns=['sub','ses','task','roi','metric','measure','value'] 
		df_out = pd.DataFrame(columns=out_columns)
		for ses, ses_df in df.groupby(['ses']):
			for task, task_df in ses_df.groupby(['task']):
				for measure, measure_name in zip(outlier_measures.values(), outlier_measures.keys()):
					for metric_name, metric_df in task_df.groupby(['metric']):
						r=pd.Series(measure(task_df.Value.values).flatten())
						task_df.index=range(task_df.shape[0])
						task_df['value'] = r
						task_df['measure'] = [measure_name] * task_df.shape[0]
						df_out = pd.concat([df_out, task_df], axis=0)
		df_out.fillna(0, inplace=True)
		if not isdefined( self.inputs.out_file) :
			self.inputs.out_file = self._gen_output()
		df_out.to_csv(self.inputs.out_file,index=False)
		return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs


