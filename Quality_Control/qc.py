# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a
import matplotlib
matplotlib.use('Agg')
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu 
import pyminc.volumes.factory as pyminc
from sklearn.metrics import normalized_mutual_info_score
import numpy as np
import pandas as pd
import os
from math import sqrt, log, ceil
from os import getcwd
from os.path import basename
from sys import argv, exit
from glob import glob
from Quality_Control.outlier import lof, kde, MAD, lcf
from pyminc.volumes.factory import *
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
import nipype.interfaces.io as nio
from Extra.concat import concat_df
import matplotlib.pyplot as plt
import seaborn as sns
import inspect
######################
#   Group-level QC   #
######################

#datasink for dist metrics
#check how the calc outlier measure node is implemented, may need to be reimplemented

def group_level_qc(opts, args):
    #setup workflow
    workflow = pe.Workflow(name=opts.preproc_dir)
    workflow.base_dir = opts.targetDir

    #Datasink
    datasink=pe.Node(interface=nio.DataSink(), name="output")
    datasink.inputs.base_directory= opts.targetDir +os.sep +"qc"
    datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]

    outfields=['coreg_metrics','tka_metrics','pvc_metrics']
    paths={'coreg_metrics':"*/coreg_qc_metrics/*_distance_metric.csv", 'tka_metrics':"*/results_tka/*_3d.csv",'pvc_metrics':"*/pvc_qc_metrics/*_pvc_qc_metric.csv"}

    #If any one of the sets of metrics does not exist because it has not been run at the scan level, then 
    #remove it from the list of outfields and paths that the datagrabber will look for.
    for  outfield, path in paths.items(): # zip(paths, outfields):
        full_path = opts.targetDir + os.sep + opts.preproc_dir + os.sep + path
        if len(glob(full_path)) == 0 :
            outfields.remove(outfield)
            paths.pop(outfield)

    #Datagrabber
    datasource = pe.Node( interface=nio.DataGrabber( outfields=outfields, raise_on_empty=True, sort_filelist=False), name="datasource")
    datasource.inputs.base_directory = opts.targetDir + os.sep +opts.preproc_dir
    datasource.inputs.template = '*'
    datasource.inputs.field_template = paths
    #datasource.inputs.template_args = dict( coreg_metrics = [['preproc_dir']] )

    ##################
    # Coregistration #
    ##################
    if 'coreg_metrics' in outfields:
        #Concatenate distance metrics
        concat_coreg_metricsNode=pe.Node(interface=concat_df(), name="concat_coreg_metrics")
        concat_coreg_metricsNode.inputs.out_file="coreg_qc_metrics.csv"
        workflow.connect(datasource, 'coreg_metrics', concat_coreg_metricsNode, 'in_list')
        workflow.connect(concat_coreg_metricsNode, "out_file", datasink, 'coreg/metrics')

        #Plot Coregistration Metrics 
        plot_coreg_metricsNode=pe.Node(interface=plot_qcCommand(), name="plot_coreg_metrics")
        plot_coreg_metricsNode.inputs.out_file=os.getcwd() + os.sep +"coreg_qc_metrics.png"
        workflow.connect(concat_coreg_metricsNode, "out_file", plot_coreg_metricsNode, 'in_file')
        workflow.connect(plot_coreg_metricsNode, "out_file", datasink, 'coreg/metrics_plot')

        #Calculate Coregistration outlier measures
        outlier_measureNode = pe.Node(interface=calc_outlier_measuresCommand(),  name="coregistration_outlier_measure")
        workflow.connect(concat_coreg_metricsNode, 'out_file', outlier_measureNode, 'in_file')
        workflow.connect(outlier_measureNode, "out_file", datasink, 'coreg/outlier')
        
        #Plot coregistration outlier measures
        plot_coreg_measuresNode=pe.Node(interface=plot_qcCommand(),name="plot_coreg_measures")
        plot_coreg_measuresNode.inputs.out_file=os.getcwd() + os.sep +"coreg_qc_measures.png"
        workflow.connect(outlier_measureNode,"out_file",plot_coreg_measuresNode,'in_file')
        workflow.connect(plot_coreg_measuresNode,"out_file",datasink,'coreg/measures_plot')
    #######
    # PVC #
    #######
    if 'pvc_metrics' in outfields:
        #Concatenate PVC metrics
        concat_pvc_metricsNode=pe.Node(interface=concat_df(), name="concat_pvc_metrics")
        concat_pvc_metricsNode.inputs.out_file="pvc_qc_metrics.csv"
        workflow.connect(datasource, 'pvc_metrics', concat_pvc_metricsNode, 'in_list')
        workflow.connect(concat_pvc_metricsNode, "out_file", datasink, 'pvc/metrics')

        #Plot PVC Metrics 
        plot_pvc_metricsNode=pe.Node(interface=plot_qcCommand(), name="plot_pvc_metrics")
        plot_pvc_metricsNode.inputs.out_file=os.getcwd() + os.sep +"pvc_qc_metrics.png"
        workflow.connect(concat_pvc_metricsNode, "out_file", plot_pvc_metricsNode, 'in_file')
        workflow.connect(plot_pvc_metricsNode, "out_file", datasink, 'pvc/metrics_plot')
        
        #Calculate PVC outlier measures
        pvc_outlier_measureNode = pe.Node(interface=pvc_outlier_measuresCommand(),  name="pvc_outlier_measure")
        workflow.connect(concat_pvc_metricsNode, 'out_file', pvc_outlier_measureNode, 'in_file')
        workflow.connect(pvc_outlier_measureNode, "out_file", datasink, 'pvc/outlier')

       #Plot PVC outlier measures 
        plot_pvc_measuresNode=pe.Node(interface=plot_qcCommand(), name="plot_pvc_measures")
        plot_pvc_measuresNode.inputs.out_file=os.getcwd() + os.sep + "pvc_qc_measures.png"
        workflow.connect(pvc_outlier_measureNode,"out_file",plot_pvc_measuresNode,'in_file')
        workflow.connect(plot_pvc_measuresNode, "out_file", datasink, 'pvc/measures_plot')


    #######
    # TKA #
    #######
    if 'tka_metrics' in outfields:
        #Concatenate TKA metrics
        concat_tka_metricsNode=pe.Node(interface=concat_df(), name="concat_tka_metrics")
        concat_tka_metricsNode.inputs.out_file="tka_qc_metrics.csv"
        workflow.connect(datasource, 'tka_metrics', concat_tka_metricsNode, 'in_list')
        workflow.connect(concat_tka_metricsNode, "out_file", datasink, 'tka/metrics')
        #Plot TKA Metrics 
        plot_tka_metricsNode=pe.Node(interface=plot_qcCommand(), name="plot_tka_metrics")
        plot_tka_metricsNode.inputs.out_file=os.getcwd() + os.sep + "tka_qc_metrics.png"
        workflow.connect(concat_tka_metricsNode, "out_file", plot_tka_metricsNode, 'in_file')
        workflow.connect(plot_tka_metricsNode, "out_file", datasink, 'tka/metrics_plot')
        #Calculate TKA outlier measures
        tka_outlier_measureNode = pe.Node(interface=tka_outlier_measuresCommand(),  name="tka_outlier_measure")
        workflow.connect(concat_tka_metricsNode, 'out_file', tka_outlier_measureNode, 'in_file')
        workflow.connect(tka_outlier_measureNode, "out_file", datasink, 'tka/outlier')
        #Plot PVC outlier measures 
        plot_tka_measuresNode=pe.Node(interface=plot_qcCommand(), name="plot_tka_measures")
        plot_tka_measuresNode.inputs.out_file=os.getcwd() + os.sep + "tka_qc_measures.png"
        workflow.connect(tka_outlier_measureNode,"out_file",plot_tka_measuresNode,'in_file')
        workflow.connect(plot_tka_measuresNode, "out_file", datasink, 'tka/measures_plot')
#montage -mode Concatenate -tile 3x2 coreg_qc_metrics.png pvc_qc_metrics.png tka_qc_metrics.png coreg_qc_measures.png  pvc_qc_measures.png   tka_qc_measures.png concat.png

    workflow.run()



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

global distance_metrics  
global outlier_measures
global metric_columns  
global outlier_columns
distance_metrics={'MI':mi, 'FSE':fse, 'CC':cc }  
outlier_measures={"KDE":kde , 'LCF':lcf} 
metric_columns  = ['analysis', 'sub','ses','task','roi','metric','value']
outlier_columns = ['analysis', 'sub','ses','task','roi','metric','measure','value']

#######################
### Outlier Metrics ###
#######################


### PVC Metrics

class pvc_qc_metricsOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class pvc_qc_metricsInput(BaseInterfaceInputSpec):
    pve = traits.File(exists=True, mandatory=True, desc="Input PVE PET image")
    pvc = traits.File(exists=True, mandatory=True, desc="Input PVC PET")
    fwhm = traits.List(desc='FWHM of the scanner')
    sub = traits.Str("Subject ID")
    task = traits.Str("Task")
    ses = traits.Str("Ses")
    out_file = traits.File(desc="Output file")
from scipy.ndimage.filters import gaussian_filter

class pvc_qc_metrics(BaseInterface):
    input_spec = pvc_qc_metricsInput 
    output_spec = pvc_qc_metricsOutput

    def _gen_output(self, sid, ses, task, fname ="pvc_qc_metric.csv"):
        dname = os.getcwd() 
        return dname + os.sep + sid + '_' + ses + '_'+ task + "_" + fname

    def _run_interface(self, runtime):
        sub = self.inputs.sub
        ses = self.inputs.ses
        task = self.inputs.task
        fwhm = self.inputs.fwhm
        pvc = pyminc.volumeFromFile(self.inputs.pvc)
        pve = pyminc.volumeFromFile(self.inputs.pve)

        mse = 0 
        for t in range(pvc.sizes[0]):
            pve_frame = pve.data[t,:,:,:]
            pvc_frame = pvc.data[t,:,:,:]
            pvc_blur = gaussian_filter(pvc_frame,fwhm) 
            m = np.sum(np.sqrt((pve_frame - pvc_blur)**2))
            mse += m
            print t, m
        mse = -mse / (pve.data.shape[0]*pve.data.shape[1]*pve.data.shape[2]*pve.data.shape[3])
        metric = "MSE" #* pve.sizes[0] 
        df = pd.DataFrame([['pvc', sub,ses,task,01,metric,mse]], columns=metric_columns)
        df.fillna(0, inplace=True)
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.sub, self.inputs.ses, self.inputs.task)

        df.to_csv(self.inputs.out_file, index=False)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self.inputs._gen_output(self.inputs.sid, self.inputs.cid)
        outputs["out_file"] = self.inputs.out_file
        return outputs


class pvc_outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class pvc_outlier_measuresInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)


class pvc_outlier_measuresCommand(BaseInterface):
    input_spec = pvc_outlier_measuresInput 
    output_spec = pvc_outlier_measuresOutput
  
    def _gen_output(self, fname ="pvc_measures.csv"):
        dname = os.getcwd() + os.sep + fname
        return dname

    def _run_interface(self, runtime):
        metric_name='MSE'
        df = pd.read_csv( self.inputs.in_file  )
        out_columns=['sub','ses','task','roi','metric','measure', 'value'] 
        df_out = pd.DataFrame(columns=out_columns)

        for measure, measure_name in zip(outlier_measures.values(), outlier_measures.keys()):
            meanValues = df.value[df['metric'] == metric_name]
            r=pd.Series(measure(meanValues).flatten())
            #r=measure(metric_df.Value.values)
            #Get column number of the current outlier measure Reindex the test_df from 0 to the number of rows it has
            #Get the series with the calculate the distance measure for the current measure
            df.index=range(df.shape[0])
            df['value'] = r 
            df['measure'] = [measure_name] * df.shape[0] 
            df_out = pd.concat([df_out, df], axis=0)
        if not isdefined( self.inputs.out_file ) : 
            self.inputs.out_file = self._gen_output()
        df_out.to_csv(self.inputs.out_file,index=False)
        
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs





### Coregistration Metrics
class coreg_qc_metricsOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class coreg_qc_metricsInput(BaseInterfaceInputSpec):
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

class coreg_qc_metricsCommand(BaseInterface):
    input_spec = coreg_qc_metricsInput 
    output_spec = coreg_qc_metricsOutput
  
    def _gen_output(self, sid, ses, task, fname ="distance_metric.csv"):
        dname = os.getcwd() 
        return dname + os.sep +'sub-'+ sid + '_ses-' + ses + '_task-' + task + '_' + fname

    def _run_interface(self, runtime):
        sub_df=pd.DataFrame(columns=metric_columns )
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

        df=pd.DataFrame(columns=metric_columns )
        for m,metric_name,metric_func in zip(mis_metric, distance_metrics.keys(), distance_metrics.values()):
            temp=pd.DataFrame([['coreg',sid,ses,task,'01',metric_name,m]],columns=df.columns  ) 
            sub_df = pd.concat([sub_df, temp])
        
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output(self.inputs.sid, self.inputs.ses, self.inputs.task)
        
        sub_df.to_csv(self.inputs.out_file,  index=False)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output( self.inputs.sid, self.inputs.cid)

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
        df_out = pd.DataFrame(columns=outlier_columns)
        for ses, ses_df in df.groupby(['ses']):
            for task, task_df in ses_df.groupby(['task']):
                for measure, measure_name in zip(outlier_measures.values(), outlier_measures.keys()):
                    for metric_name, metric_df in task_df.groupby(['metric']):
                        #print metric_df
                        if 'cdf' in inspect.getargspec(measure).args:
                            if 'coreg' or 'pvc' in metric_df.analysis: cdf=True
                            else : cdf=False
                            m=measure(metric_df.value.values, cdf=cdf).flatten()
                        else: m=measure(metric_df.value.values).flatten()

                        r=pd.Series(m)

                        metric_df.index=range(metric_df.shape[0])
                        metric_df['value'] = r
                        metric_df['measure'] = [measure_name] * metric_df.shape[0]
                        df_out = pd.concat([df_out, metric_df], axis=0)
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

### TKA outlier measures

class tka_outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class tka_outlier_measuresInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)


class tka_outlier_measuresCommand (BaseInterface):
    input_spec = tka_outlier_measuresInput 
    output_spec = tka_outlier_measuresOutput
  
    def _gen_output(self, fname ="tka_measures.csv"):
        dname = os.getcwd() + os.sep + fname
        return dname

    def _run_interface(self, runtime):
                
        df = pd.read_csv( self.inputs.in_file  )
        out_columns=['sub','ses','task','roi','metric','measure','value'] 
        df_out = pd.DataFrame(columns=out_columns)
        print df
        for roi, roi_df in df.groupby('roi'):
        #    for ses, ses_df in roi_df.groupby('ses'):
        #        for task, task_df in df.groupby('task'):
            for measure, measure_name in zip(outlier_measures.values(), outlier_measures.keys()):
                meanValues = roi_df.value[roi_df['metric'] == 'mean']
                r=pd.Series(measure(meanValues).flatten())
                roi_df.index=range(roi_df.shape[0])
                roi_df['value'] = r                     
                roi_df['measure'] = [measure_name] * roi_df.shape[0] 
                df_out = pd.concat([df_out, roi_df], axis=0)
        if not isdefined( self.inputs.out_file ) : 
            self.inputs.out_file = self._gen_output()
        df_out.fillna(0, inplace=True)
        df_out.to_csv(self.inputs.out_file,index=False)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs

### Plot Metrics
#           analysis    sub     ses     task    metric  roi     value
#    0      coreg       19      F       1       CC      1       0.717873
class plot_qcOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class plot_qcInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")


class plot_qcCommand (BaseInterface):
    input_spec = tka_outlier_measuresInput 
    output_spec = tka_outlier_measuresOutput
  
    def _gen_output(self, fname ="metrics.png"):
        dname = os.getcwd() + os.sep + fname
        return dname

    def _run_interface(self, runtime):
        df = pd.read_csv( self.inputs.in_file  )
        if "measure"  in df.columns:
            plot_type="measure"
        elif "metric"  in df.columns :
            plot_type = "metric"
        else:
            print("Unrecognized data frame")
            print df
            exit(1)
        
        plt.clf()
        fig, ax = plt.subplots()
        plt.figure(1)
        nROI = len(np.unique(df.roi))
        
        if plot_type == "measure" : 
            unique_measure =np.unique(df.measure)
            nMeasure = np.unique(unique_measure)

        unique_metric = np.unique(df.metric)
        nMetric = len(unique_metric)
        #fig, axes = plt.subplots(nrows=nROI, ncols=nMetric)
        for roi, i in zip(np.unique(df.roi), range(nROI)):
            df0=df[ (df.roi==roi)  ]
            for metric in unique_metric :
                x=df0.value[df.metric == metric]
                #df0.value.loc[df.metric == metric]= (x-np.mean(x))/np.std(x)
                df0.value.loc[df.metric == metric]= (x-np.min(x))/(np.max(x)-np.min(x))

            print(df0)
            if plot_type == "measure" : 
                sns.factorplot(x="metric", col="measure", y="value", kind="swarm",  data=df0, legend=False, hue="sub")
                plt.title("Outlier Measure: "+df0.analysis.iloc[0] )
            else : 
                sns.factorplot(x="metric", y="value",   data=df0, legend=False, kind="swarm",  hue="sub")
                plt.title("QC Metric: " + df0.analysis.iloc[0] )
            plt.ylabel('')
            plt.xlabel('')
            if nROI > 1 : plt.title("ROI Label: "+str(roi))
            
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.ylim([-0.05,1.05])
            plt.legend(bbox_to_anchor=(1.05, 1), loc="upper right", ncol=1, prop={'size': 6})
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        print('Out file:', self.inputs.out_file)
        #plt.tight_layout()
        plt.savefig(self.inputs.out_file, bbox_inches="tight", dpi=1000, width=2000)
        plt.clf()
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs
