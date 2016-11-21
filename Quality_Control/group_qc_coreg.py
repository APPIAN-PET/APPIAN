import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)


import pyminc.volumes.factory as pyminc
import matplotlib
import matplotlib.pyplot as plt
from scipy.stats import ks_2samp
import numpy as np
import pandas as pd
import fnmatch
import os
from math import sqrt
from os import getcwd
from sklearn.metrics import mutual_info_score
from sys import argv, exit


class PETtoT1_group_qcOutput(TraitedSpec):
    out_file = File(desc="Output file")

class PETtoT1_group_qcInput(BaseInterfaceInputSpec):
    pet_images = File(exists=True, mandatory=True, desc="Native dynamic PET image")
    t1_images = File(exists=True, mandatory=True, desc="MRI image")
    out_file = File(desc="Output file")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETtoT1_group_qc(BaseInterface):
    input_spec = PETtoT1_group_qcInput
    output_spec = PETtoT1_group_qcOutput


    def _run_interface(self, runtime):
        inputs = self.input_spec().get()
	if inputs.out_file == None: inputs.out_file="PETtoT1_coreg_qc.png"
	df=pet2t1_coreg_qc(pet_images, t1_images, alpha=0.05)
	plot_pet2t1_coreg(df, inputs.out_file)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file_img
        
        return outputs

###
### QC function to test if there are outliers in coregistered images
###

def pet2t1_coreg_qc(pet_images, t1_images, alpha=0.05):
	#pet_dir=argv[1]
	#mri_dir=argv[2]
	#pet_images=sorted(list_paths(pet_dir, "*.mnc"))
	#t1_images=sorted(list_paths(mri_dir, "*.mnc"))

	#mi_list=img_mi(pet_images, t1_images)

	mi_list=pd.Series([1.94565299994 , 1.78677021816, 1.71681652919, 1.79284928896, 1.69685169594 , 1.8925707379, 1.91150087673, 1.91351946117, 1.68566111062, 1.39356149443, 1.5448906024, 1.5223863097, 1.82259812813, 1.37758014175, 1.91019564353, 1.9053690547, 1.91770161416, 1.62592415566, 1.88027600008 ,  1.89351525464, 2.06085761606, 1.85919235056, 1.774951614, 1.64781175331, 1.92539419348, 1.83281566499, 1.63495527526, 1.7754404866, 1.69857611697, 1.91274275946, 1.81477196656, 1.79953422437, 1.84789498858, 1.92349638563])

	###Calculate Mean Absolute Difference
	mad_list=img_mad(mi_list)

	###Calculate Kolmogorov-Smirnov D
	c={0.05:1.36, 0.10:1.22, 0.025:1.48, 0.01:1.63, 0.005:1.73, 0.001:1.95}
	mi_list.sort()
	n=100
	mi_max=max(mi_list)

	l0=float(len(mi_list))
	l1=float(l0-1)
	pvalues=np.repeat(1., len(l0)).cumsum() / len(l0)
	dvalues=np.repeat(0., len(l0))

	C=c[alpha]*sqrt( (l0+l1) / (l0*l1))
	C_list=np.repeat(C, len(mi_list))
	x0=np.arange(0.,mi_max, mi_max/n)
	df0=pd.DataFrame({"Value":mi_list, "p":pvalues, "D":dvalues, "MAD": mad_list , 'C':C_list} )
	y0=np.interp( x0, df0.Value, df0.p   )

	for i in mi_list.index:
	    mi_temp=mi_list.drop(i)
	    p1=np.repeat(1., len(mi_temp)).cumsum() / len(mi_temp)
	    y1=np.interp( x0, mi_temp, p1 )
	    d=abs(max(y0-y1))
	    df0.D[i]=d
	df0=df0.sort_index()
	return(df0)

###
###Function to plot the results of 
###
def plot_pet2t1_coreg(df):
	plt.close()
	font_size=8
	fig, ax = plt.subplots()
	plt.figure(1)

	plt.subplot(311)
	plt.plot(df.Value, 'r', label='Mutual\nInformation')
	legend = plt.legend(loc='right', prop={'size':font_size},  bbox_to_anchor=(1.2, 0.5))
	plt.title('PET-MRI Coregistration')

	plt.subplot(312)
	plt.plot(df.MAD, 'b', label='Median\nAbsolute\nDeviation')
	legend = plt.legend(loc='right',prop={'size':font_size}, bbox_to_anchor=(1.2, 0.5))

	plt.subplot(313)
	plt.plot(df.D, 'g', label='Kolmogorov\nSmirnov\'s D')
	plt.plot(df.C, 'black', label='$\\alpha$='+str(alpha))
	legend = plt.legend(loc='right',prop={'size':font_size},fancybox=True, bbox_to_anchor=(1.2, 0.5))
	plt.xlabel('Subject Number')

	plt.savefig("group_mi_coreg.png", dpi=500,  bbox_inches='tight' )
	return(0)

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

def mad(data, axis=None):
    return np.mean(np.abs(data - np.mean(data, axis)), axis)

def img_mad(x):
    mad_list= abs(x - np.median(x)) / mad(x)
    return(mad_list)

def img_mi(pet_images, t1_images):
    mi_list=[]
    for pet_fn, mri_fn in zip(pet_images, t1_images):
        print "PET:", pet_fn
        print "MRI:", mri_fn
        pet = pyminc.volumeFromFile(pet_fn)
        mri = pyminc.volumeFromFile(mri_fn)
        mi = mutual_info_score(pet.data.flatten(), mri.data.flatten(), None)
        print "Mutual Information:", mi
        mi_list += [mi]
    
    return(mi_list)


