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
from sys import argv, exit
from itertools import product

class PETtoT1_group_qcOutput(TraitedSpec):
    out_file = traits.File( desc="Output files")

class PETtoT1_group_qcInput(BaseInterfaceInputSpec):
    pet_images = traits.List(exists=True, mandatory=True, desc="Native dynamic PET image")
    t1_images = traits.List(exists=True, mandatory=True, desc="MRI image")
    brain_masks = traits.List(exists=True, mandatory=True, desc="Binary images that mask out the brain")
    subjects = traits.List(exists=True, mandatory=True, desc="Subject names")
    conditions = traits.List(exists=True, mandatory=True, desc="Subject conditions")
    study_prefix = traits.List(mandatory=True, desc="Prefix of current study")
    out_file = traits.File(desc="Output file")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETtoT1_group_qc(BaseInterface):
    input_spec = PETtoT1_group_qcInput
    output_spec = PETtoT1_group_qcOutput

    def _run_interface(self, runtime):
        pet_images=self.inputs.pet_images
        t1_images=self.inputs.t1_images
        brain_masks=self.inputs.brain_masks
        subjects=self.inputs.subjects
        conditions=self.inputs.conditions
        study_prefix=self.inputs.study_prefix[0]
        out_file="PETtoT1_group_qc.csv"
        #print pet_images
        #print t1_images
        #print subjects 
        #print conditions

        df=group_coreg_qc(pet_images, t1_images, brain_masks, subjects, conditions, study_prefix, '')
        
        df.to_csv(out_file)
        self.inputs.out_file=out_file
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        
        return(outputs)


def group_coreg_qc(pet_images, t1_images, brain_masks, subjects, conditions, study_prefix, label):
    alpha=0.05
    out_files=[]
    unique_conditions=np.unique(conditions)
    nconditions=len(unique_conditions)
    
    combined=zip(subjects, conditions, pet_images, t1_images, brain_masks) #FIXME: Include sorting here, just in case
    df=pet2t1_coreg_qc(subjects, conditions, pet_images, t1_images, brain_masks, alpha)

    return(df)


###
### QC function to test if there are outliers in coregistered images
###

def pet2t1_coreg_qc(subjects, conditions, pet_images, t1_images,brain_masks, alpha):
	#pet_images=sorted(list_paths(pet_dir, "*.mnc"))
	#t1_images=sorted(list_paths(mri_dir, "*.mnc"))
	colnames= ["Subject", "Condition", "Metric", "Value"] 
	print(subjects)
	d={"Subjects": list(subjects)}
	print(d)
	names=pd.DataFrame(d)

	outlier_measures={'MAD':img_mad}
	distance_metrics={'NMI':mi} #, 'XCorr':qc.xcorr }

	metric_df = pd.DataFrame(columns=colnames)
	outlier_df = pd.DataFrame(columns=colnames)


	###Get distance metrics
	for metric_name, metric in zip(distance_metrics.keys(), distance_metrics.values()):
		for sub,cond, pet, t1, brain in zip(subjects,conditions, pet_images, t1_images, brain_masks):
			m=metric(pet, t1, brain)
			temp=pd.DataFrame([[sub,cond, metric_name, m]],columns=colnames  )
			metric_df = pd.concat([metric_df, temp ])
		

	n=metric_df.shape[0]
	empty_df = pd.DataFrame(np.zeros([n,1]), columns=['Score'], index=[0]*n) 
	df2 = pd.DataFrame([])
	for measure in outlier_measures.keys():
		m=pd.DataFrame( { 'Measure':[measure] * n} , index=[0]*n )
		d=pd.concat([metric_df, m, empty_df], axis=1)
		df2=pd.concat([df2,d], axis=0)
	outlier_df=df2
	###Get outlier measures
	for measure_name, measure in zip(outlier_measures.keys(), outlier_measures.values()):
		print outlier_df.Subject
		for n in range(len(outlier_df.Subject)):
			x=pd.Series(outlier_df.Value)
			r=measure(x,n)
			target_row=(outlier_df.Subject == outlier_df.Subject.iloc[n]) & (outlier_df.Metric == metric_name ) & (outlier_df.Measure == measure_name ) 
		#Insert r into the data frame
			outlier_df.loc[ target_row, 'Score' ] =r

	return(outlier_df)


###
### Some extra helper functions
###

def list_paths(mypath, string):
    output=[]
    try: files=os.listdir(mypath)
    except:
        print "Path does not exist:", mypath
        return output
    for f in files:
        if fnmatch.fnmatch(f, string):
            output.append(f)
        #files = [ f for f in os.listdir(mypath) if fnmatch.fnmatch(f, string) ]
    output=[mypath+"/"+f for f in output]
    return output

def mad(data):
    return np.median(np.abs(data.values - data.median()))

def img_mad(x, i):
    r=(x.values[i] - x.median()) / mad(x)
    return(r)

####################
# Distance Metrics #
####################
__NBINS=-1

def distance(pet_fn, mri_fn, brain_fn, dist_f):
    pet = pyminc.volumeFromFile(pet_fn)
    mri = pyminc.volumeFromFile(mri_fn)
    mask= pyminc.volumeFromFile(brain_fn)
    pet_data=pet.data.flatten()
    mri_data=mri.data.flatten()
    mask_data=mask.data.flatten()

    n=len(pet_data)
    masked_pet_data = [ pet_data[i] for i in range(n) if int(mask_data[i])==1 ]
    masked_mri_data = [ mri_data[i] for i in range(n) if int(mask_data[i])==1 ]
    del pet
    del mri
    del mask
    del mask_data
    dist=dist_f(masked_pet_data, masked_mri_data)
    return(dist)


def mi(masked_pet_data, masked_mri_data):
    masked_pet_data = [int(round(x)) for x in masked_pet_data ]
    masked_mri_data = [int(round(x)) for x in masked_mri_data ]
    
    nmi = normalized_mutual_info_score(masked_pet_data,masked_mri_data)
    print "NMI:", nmi
    return(val)


#def cc(pet_fn, mri_fn, brain_fn):
def cc(masked_pet_data, masked_mri_data):
    ###Ref: Studholme et al., (1997) Medical Physics 24, Vol 1
    pet_nbins=find_nbins(masked_pet_data) #len(masked_mri_data) /2 #/4 #1000 #len(masked_mri_data)/10
    mri_nbins=find_nbins(masked_mri_data)

    cc=0.0
    xd=0.0
    yd=0.0
    p=joint_dist(masked_pet_data, masked_mri_data,nbins )[0]

    pet_mean=np.mean(masked_pet_data)
    mri_mean=np.mean(masked_mri_data)
    xval=(masked_pet_data-pet_mean)
    yval=(masked_mri_data-mri_mean)
    num = np.sum( xval * yval * p)
    xd = np.sum( p * xval**2)
    yd = np.sum( p * yval**2)
    den=sqrt(xd*yd)
    cc = num / den 
    print "CC = " + str(cc)

    return(cc)

#%run mytest.py /data1/projects/Stroke/CIVET1.12/GPI-P02_S_Cortical_I/native/GPI_2MEDA45Initial_t1.mnc /data1/projects/Stroke/results/10480/pet/GPI-P02_S_Cortical_I_pet-coreg2t1-sum.mnc /data1/projects/Stroke/results/10480/srv/GPI-P02_S_Cortical_I_brain_mask_nat.mnc


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
    iv = np.sum(df.groupby(["Label"])["Normed"].agg( {'IV': lambda x: sqrt(x.sum()) } ) * mri_dist[0])
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
    nbins = h[0].shape[0] * h[0].shape[1]
    hi= np.array(h[0].flatten() / sum(h[0].flatten()) ).reshape( h[0].shape)
    x_bin = np.digitize(masked_pet_data, h[1]) - 1
    y_bin = np.digitize(masked_mri_data, h[2]) - 1
    x_bin[x_bin >= h[0].shape[0] ]=h[0].shape[0]-1
    y_bin[y_bin >= h[0].shape[1] ]=h[0].shape[1]-1
    pet_bin=x_bin
    mri_bin=y_bin

    x_idx=x_bin #v[:,0]
    y_idx=y_bin #v[:,1]
    p=hi[x_idx,y_idx]

    return [p, pet_bin, x_bin]

def find_nbins(array):
    r=max(array) - min(array)
    
    n=ceil(-np.log2(16/r))
    return n



###
## Code not used and can potentially be deleted
###


#Calculate Cross-correlation (xcorr) between co-registered PET and MRI images
def img_xcorr(pet_images, t1_images, brain_masks):
    xcorr_list=[]
    for pet_fn, mri_fn, brain_fn in zip(pet_images, t1_images, brain_masks):
        val=xcorr(pet_fn, mri_fn, brain_fn)
        #print "Cross-correlation:", xcorr
        xcorr_list.append(val)
    return(pd.Series(xcorr_list, name='Xcorr'))



#Calculate mutual information between co-registered PET and MRI images
def img_mi(pet_images, t1_images, brain_masks):
    mi_list=[]
    for pet_fn, mri_fn, brain_fn in zip(pet_images, t1_images, brain_masks):
        #print "PET:", pet_fn
        #print "MRI:", mri_fn
        #print "Brain Mask:", brain_fn
        mi_val=mi(pet_fn, mri_fn, brain_fn)
        #print "Mutual Information:", mi
        mi_list += [mi_val]
    return(pd.Series(mi_list, name='MI'))


#Calculate Kolmogorov-Smirnov's D
'''def kolmogorov_smirnov( x, alpha=0.05):
    c={0.05:1.36, 0.10:1.22, 0.025:1.48, 0.01:1.63, 0.005:1.73, 0.001:1.95}
    n=100
    x_max=max(x)
    x.sort_values(inplace=True)
    l0=float(len(x))
    l1=float(l0-1)
    pvalues=np.repeat(1., l0).cumsum() / l0
    dvalues=np.repeat(0., l0)
    C=c[alpha]*sqrt( (l0+l1) / (l0*l1))
    C_list=np.repeat(C, len(x))
    x0=np.arange(0.,x_max, x_max/n)

    df0=pd.concat( [ pd.Series(list(x.index), name='Index'), pd.Series(dvalues, name='D'), pd.Series(C_list, name='C' )], axis=1)
    df0.set_index('Index', inplace=True)
    y0=np.interp( x0, x.values, pvalues   )
    for i in x.index:
        x_temp=x.drop([i])
        p1=np.repeat(1., len(x_temp)).cumsum() / len(x_temp)
        y1=np.interp( x0, x_temp, p1 )
        d=abs(max(y0-y1))
        df0.D[i]=d
    df0.sort_index(inplace=True)
    
    return(df0.D)
'''


def kolmogorov_smirnov( x, i, alpha=0.05):
    c={0.05:1.36, 0.10:1.22, 0.025:1.48, 0.01:1.63, 0.005:1.73, 0.001:1.95}
    n=100
    x_max=max(x)
    x.sort_values(inplace=True)
    l0=float(len(x))
    l1=float(l0-1)
    pvalues=np.repeat(1., l0).cumsum() / l0
    dvalues=np.repeat(0., l0)
    C=c[alpha]*sqrt( (l0+l1) / (l0*l1))
    C_list=np.repeat(C, len(x))
    x0=np.arange(0.,x_max, x_max/n)

    df0=pd.concat( [ pd.Series(list(x.index), name='Index'), pd.Series(dvalues, name='D'), pd.Series(C_list, name='C' )], axis=1)
    df0.set_index('Index', inplace=True)
    y0=np.interp( x0, x.values, pvalues   )
   
    
    x_temp=x.drop([i])
    p1=np.repeat(1., len(x_temp)).cumsum() / len(x_temp)
    y1=np.interp( x0, x_temp, p1 )
    d=abs(max(y0-y1))
    
    return(d)


###
###Function to plot the results of 
###
def plot_pet2t1_coreg(mi, xcorr, alpha, out_file):
	plt.close()
	font_size=8
	fig, ax = plt.subplots()
	plt.figure(1)
        font_size=7 
        fig, axes = plt.subplots(nrows=3, ncols=2)
        #Mutual Information Raw
        mi['MI'].plot(ax=axes[0,0], subplots=True, sharex=True, fontsize=8); 
        axes[0,0].set_title('Mutual Information')


        #Xcorr Raw
        xcorr['Xcorr'].plot(ax=axes[0,1], color='g', fontsize=8); 
        axes[0,1].set_title('Cross-correlation')
        #Mutual Information - Median Average Difference

        mi['MAD'].plot(ax=axes[1,0], fontsize=8); 
        axes[1,0].set_ylabel('MAD')

        #Cross-correlation - Median Average Difference

        xcorr['MAD'].plot(ax=axes[1,1], color='g', fontsize=8); 

        mi['D'].plot(ax=axes[2,0], fontsize=8); 
        mi['C'].plot(ax=axes[2,0], color='r', rot=90, fontsize=8); 
        axes[2,0].set_ylabel('Kolmogorov\nSmirnov\'s D')
        
        xcorr['D'].plot(ax=axes[2,1], color='g'); 
        xcorr['C'].plot(ax=axes[2,1], color='r', rot=90, fontsize=8); 

        print "\n\nSaving to ", os.getcwd(), out_file, "\n\n"
	plt.savefig(out_file, dpi=2000,  bbox_inches='tight' )
	return(0)

