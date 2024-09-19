# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a
import matplotlib 
matplotlib.rcParams['figure.facecolor'] = '1.'
matplotlib.use('Agg')
import ants
import numpy as np
import pandas as pd
import os
import imageio
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu 
import nibabel as nib
import shutil
import ntpath
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
import nipype.interfaces.io as nio
import matplotlib.pyplot as plt
import seaborn as sns
import inspect
import json
import re 
import time
import matplotlib.animation as animation
from skimage.feature import canny
from nibabel import resample_to_output
from sklearn.metrics import normalized_mutual_info_score
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from skimage.filters import threshold_otsu
from math import sqrt, log, ceil
from os import getcwd
from os.path import basename
from sys import argv, exit
from glob import glob
from src.outlier import  kde, MAD
from sklearn.neighbors import LocalOutlierFactor 
from src.utils import concat_df
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from scipy.ndimage.filters import gaussian_filter
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)


_file_dir, fn =os.path.split( os.path.abspath(__file__) )

def load_3d(fn, t=0):
    print('Reading Frame %d'%t,'from', fn)
    img = nib.load(fn)
    vol = img.get_fdata() 
    if len(vol.shape) == 4 :
        vol = vol[:,:,:,t]
    vol = vol.reshape(vol.shape[0:3] )
    img = nib.Nifti1Image(vol, img.affine)
    return img, vol

def get_spacing(aff, i) : 
    return aff[i, np.argmax(np.abs(aff[i,0:3]))] 
######################
#   Group-level QC   #
######################

#datasink for dist metrics
#check how the calc outlier measure node is implemented, may need to be reimplemented

final_dir="qc"

def group_level_qc(opts, args):
    #setup workflow
    workflow = pe.Workflow(name=qc_err+opts.preproc_dir)
    workflow.base_dir = opts.targetDir

    #Datasink
    datasink=pe.Node(interface=nio.DataSink(), name=qc_err+"output")
    datasink.inputs.base_directory= opts.targetDir +os.sep +"qc"
    datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]

    outfields=['coreg_metrics','tka_metrics','pvc_metrics']
    paths={'coreg_metrics':"*/coreg_qc_metrics/*_metric.csv", 'tka_metrics':"*/results_tka/*_3d.csv",'pvc_metrics':"*/pvc_qc_metrics/*qc_metric.csv"}

    #If any one of the sets of metrics does not exist because it has not been run at the scan level, then 
    #remove it from the list of outfields and paths that the datagrabber will look for.
    for  outfield, path in paths.items(): # zip(paths, outfields):
        full_path = opts.targetDir + os.sep + opts.preproc_dir + os.sep + path
        print(full_path)
        if len(glob(full_path)) == 0 :
            outfields.remove(outfield)
            paths.pop(outfield)

    #Datagrabber
    datasource = pe.Node( interface=nio.DataGrabber( outfields=outfields, raise_on_empty=True, sort_filelist=False), name=qc_err+"datasource")
    datasource.inputs.base_directory = opts.targetDir + os.sep +opts.preproc_dir
    datasource.inputs.template = '*'
    datasource.inputs.field_template = paths
    #datasource.inputs.template_args = dict( coreg_metrics = [['preproc_dir']] )

    ##################
    # Coregistration #
    ##################
    qc_err=''
    if opts.pvc_label_name != None :
        qc_err += "_"+opts.pvc_label_name
    if opts.quant_label_name != None :
        qc_err += "_"+opts.quant_label_name
    if opts.results_label_name != None :
        qc_err += "_"+opts.results_label_name
    qc_err += "_"

    if 'coreg_metrics' in outfields:
        #Concatenate distance metrics
        concat_coreg_metricsNode=pe.Node(interface=concat_df(), name=qc_err+"concat_coreg_metrics")
        concat_coreg_metricsNode.inputs.out_file="coreg_qc_metrics.csv"
        workflow.connect(datasource, 'coreg_metrics', concat_coreg_metricsNode, 'in_list')
        workflow.connect(concat_coreg_metricsNode, "out_file", datasink, 'coreg/metrics')

        #Plot Coregistration Metrics 
        plot_coreg_metricsNode=pe.Node(interface=plot_qcCommand(), name=qc_err+"plot_coreg_metrics")
        workflow.connect(concat_coreg_metricsNode, "out_file", plot_coreg_metricsNode, 'in_file')
        workflow.connect(plot_coreg_metricsNode, "out_file", datasink, 'coreg/metrics_plot')

        #Calculate Coregistration outlier measures
        outlier_measureNode = pe.Node(interface=outlier_measuresCommand(),  name=qc_err+"coregistration_outlier_measure")
        workflow.connect(concat_coreg_metricsNode, 'out_file', outlier_measureNode, 'in_file')
        workflow.connect(outlier_measureNode, "out_file", datasink, 'coreg/outlier')

        #Plot coregistration outlier measures
        plot_coreg_measuresNode=pe.Node(interface=plot_qcCommand(),name=qc_err+"plot_coreg_measures")
        workflow.connect(outlier_measureNode,"out_file",plot_coreg_measuresNode,'in_file')
        workflow.connect(plot_coreg_measuresNode,"out_file",datasink,'coreg/measures_plot')
    #######
    # PVC #
    #######
    if 'pvc_metrics' in outfields:
        #Concatenate PVC metrics
        concat_pvc_metricsNode=pe.Node(interface=concat_df(), name=qc_err+"concat_pvc_metrics")
        concat_pvc_metricsNode.inputs.out_file="pvc_qc_metrics.csv"
        workflow.connect(datasource, 'pvc_metrics', concat_pvc_metricsNode, 'in_list')
        workflow.connect(concat_pvc_metricsNode, "out_file", datasink, 'pvc/metrics')

        #Plot PVC Metrics 
        plot_pvc_metricsNode=pe.Node(interface=plot_qcCommand(), name=qc_err+"plot_pvc_metrics")
        workflow.connect(concat_pvc_metricsNode, "out_file", plot_pvc_metricsNode, 'in_file')
        workflow.connect(plot_pvc_metricsNode, "out_file", datasink, 'pvc/metrics_plot')

        #Calculate PVC outlier measures
        pvc_outlier_measureNode = pe.Node(interface=outlier_measuresCommand(),  name=qc_err+"pvc_outlier_measure")
        workflow.connect(concat_pvc_metricsNode, 'out_file', pvc_outlier_measureNode, 'in_file')
        workflow.connect(pvc_outlier_measureNode, "out_file", datasink, 'pvc/outlier')

       #Plot PVC outlier measures 
        plot_pvc_measuresNode=pe.Node(interface=plot_qcCommand(), name=qc_err+"plot_pvc_measures")
        workflow.connect(pvc_outlier_measureNode,"out_file",plot_pvc_measuresNode,'in_file')
        workflow.connect(plot_pvc_measuresNode, "out_file", datasink, 'pvc/measures_plot')


    #######
    # TKA #
    #######
    if 'tka_metrics' in outfields:
        #Concatenate TKA metrics
        concat_tka_metricsNode=pe.Node(interface=concat_df(), name=qc_err+"concat_tka_metrics")
        concat_tka_metricsNode.inputs.out_file="tka_qc_metrics.csv"
        workflow.connect(datasource, 'tka_metrics', concat_tka_metricsNode, 'in_list')
        workflow.connect(concat_tka_metricsNode, "out_file", datasink, 'tka/metrics')
        #Plot TKA Metrics 
        plot_tka_metricsNode=pe.Node(interface=plot_qcCommand(), name=qc_err+"plot_tka_metrics")
        workflow.connect(concat_tka_metricsNode, "out_file", plot_tka_metricsNode, 'in_file')
        workflow.connect(plot_tka_metricsNode, "out_file", datasink, 'tka/metrics_plot')
        #Calculate TKA outlier measures
        tka_outlier_measureNode = pe.Node(interface=outlier_measuresCommand(),  name=qc_err+"tka_outlier_measure")
        workflow.connect(concat_tka_metricsNode, 'out_file', tka_outlier_measureNode, 'in_file')
        workflow.connect(tka_outlier_measureNode, "out_file", datasink, 'tka/outlier')
        #Plot PVC outlier measures 
        plot_tka_measuresNode=pe.Node(interface=plot_qcCommand(), name=qc_err+"plot_tka_measures")
        workflow.connect(tka_outlier_measureNode,"out_file",plot_tka_measuresNode,'in_file')
        workflow.connect(plot_tka_measuresNode, "out_file", datasink, 'tka/measures_plot')

    workflow.run()



####################
# Distance Metrics #
####################
__NBINS=-1
import copy
def pvc_mse(pvc_fn, pve_fn, fwhm):
    pvc = nib.load(pvc_fn)
    pvc.data = pvc.get_data()
    pve = nib.load(pve_fn)
    pve.data = pve.get_data()
    mse = 0 
    if len(pvc.data.shape) > 3 :#if volume has more than 3 dimensions
        t = int(pvc.data.shape[3]/2)
        #for t in range(pvc.sizes[0]):
        pve_frame = pve.data[:,:,:,t]
        pvc_frame = pvc.data[:,:,:,t]

        n = np.sum(pve.data[t,:,:,:]) # np.prod(pve.data.shape[0:4])
        pvc_blur = gaussian_filter(pvc_frame,fwhm) 
        m = np.sum(np.sqrt((pve_frame - pvc_blur)**2))
        mse += m
        print(t, m)
    else : #volume has 3 dimensions
        n = np.sum(pve.data) # np.prod(pve.data.shape[0:3])
        pvc_blur = gaussian_filter(pvc.data,fwhm) 
        m = np.sum(np.sqrt((pve.data - pvc_blur)**2))
        mse += m
    mse = -mse /  n #np.sum(pve.data)
    print("PVC MSE:", mse)
    return mse


####################
# Outlier Measures #
####################

def _IsolationForest(X):
    X = np.array(X)
    if len(X.shape) == 1 :
        X=X.reshape(-1,1)
    rng = np.random.RandomState(42)
    clf = IsolationForest(max_samples=X.shape[0], random_state=rng)
    return clf.fit(X).predict(X)

def _LocalOutlierFactor(X):
    X = np.array(X)
    if len(X.shape) == 1 :
        X=X.reshape(-1,1)
    n=int(round(X.shape[0]*0.2))

    clf = LocalOutlierFactor(n_neighbors=n)

    clf.fit_predict(X)

    return clf.negative_outlier_factor_

def _OneClassSVM(X):
    clf = OneClassSVM(nu=0.1, kernel="rbf", gamma=0.1)
    clf.fit(X)
    return clf.predict(X)

def _dbscan(X):
    db = DBSCAN(eps=0.3)
    return db.fit_predict(X)

###########
# Globals #
###########

global distance_metrics  
global outlier_measures
global metric_columns  
global outlier_columns
outlier_measures={"KDE":kde, "LOF": _LocalOutlierFactor, "IsolationForest":_IsolationForest, "MAD":MAD} #, "DBSCAN":_dbscan, "OneClassSVM":_OneClassSVM } 

metric_columns  = ['analysis', 'sub','ses','task','run','trc','rec','roi','metric','value']
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
    run = traits.Str("Run")
    rec = traits.Str("Reconstruction")
    trc = traits.Str("Acquisition")
    out_file = traits.File(desc="Output file")

class pvc_qc_metrics(BaseInterface):
    input_spec = pvc_qc_metricsInput 
    output_spec = pvc_qc_metricsOutput

    def _gen_output(self, sid, ses, task,run,trc,rec, fname ="pvc_qc_metric.csv"):
        dname = os.getcwd() 
        fn = dname+os.sep+'sub-'+sid+'_ses-'+ses+'_task-'+task
        if isdefined(run) :
            fn += '_run-'+str(run)
        fn += "_trc-"+str(trc)+"_rec-"+str(rec)+fname
        return fn

    def _run_interface(self, runtime):
        sub = self.inputs.sub
        ses = self.inputs.ses
        task = self.inputs.task
        fwhm = self.inputs.fwhm
        run = self.inputs.run
        rec = self.inputs.rec
        trc = self.inputs.trc
        df = pd.DataFrame([], columns=metric_columns)
        pvc_metrics={'mse':pvc_mse }
        for metric_name, metric_function in pvc_metrics.items():
            mse = pvc_mse(self.inputs.pvc, self.inputs.pve, fwhm)
            temp = pd.DataFrame([['pvc', sub,ses,task,run,trc,rec,'02',metric_name,mse]], columns=metric_columns)
            df = pd.concat([df, temp])
        df.fillna(0, inplace=True)
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.sub, self.inputs.ses, self.inputs.task, self.inputs.run, self.inputs.trc, self.inputs.rec)
        df.to_csv(self.inputs.out_file, index=False)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self.inputs._gen_output(self.inputs.sid,self.inputs.ses, self.inputs.task, self.inputs.run, self.inputs.trc, self.inputs.rec)
        outputs["out_file"] = self.inputs.out_file
        return outputs

### Coregistration Metrics
class coreg_qc_metricsOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class coreg_qc_metricsInput(BaseInterfaceInputSpec):
    pet = traits.File(exists=True, mandatory=True, desc="Input PET image")
    t1 = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    brain_mask_space_mri = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    pet_brain_mask = traits.File(exists=True, mandatory=True, desc="Input T1 MRI")
    sid = traits.Str(desc="Subject")
    ses = traits.Str(desc="Session")
    task = traits.Str(desc="Task")
    run = traits.Str(desc="Run")
    rec = traits.Str(desc="Reconstruction")
    trc = traits.Str(desc="Acquisition")
    study_prefix = traits.Str(desc="Study Prefix")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)

class coreg_qc_metricsCommand(BaseInterface):
    input_spec = coreg_qc_metricsInput 
    output_spec = coreg_qc_metricsOutput

    def _gen_output(self, sid, ses, task, run, rec, trc, fname ="distance_metric.csv"):
        dname = os.getcwd() 
        fn = dname+os.sep+'sub-'+sid+'_ses-'+ses+'_task-'+task
        if isdefined(run) :
            fn += '_run-'+str(run)
        fn += "_trc-"+str(trc)+"_rec-"+str(rec)+fname
        return fn 

    def _run_interface(self, runtime):
        sub_df=pd.DataFrame(columns=metric_columns )
        pet = self.inputs.pet
        t1 = self.inputs.t1
        sid = self.inputs.sid
        ses = self.inputs.ses
        task = self.inputs.task
        run = self.inputs.run
        rec = self.inputs.rec
        trc = self.inputs.trc

        brain_mask_space_mri = self.inputs.brain_mask_space_mri
        pet_brain_mask = self.inputs.pet_brain_mask

        coreg_metrics=['MattesMutualInformation']

        path, ext = os.path.splitext(pet)
        base=basename(path)
        param=base.split('_')[-1]
        param_type=base.split('_')[-2]

        df=pd.DataFrame(columns=metric_columns )

        def image_read(fn) : 
            img, vol = load_3d(fn)
            vol = vol.astype(float)
            aff = img.affine
            origin = [ aff[0,3], aff[1,3], aff[2,3]]
            spacing = [ get_spacing(aff, 0), get_spacing(aff, 1), get_spacing(aff, 2) ]
            return ants.from_numpy( vol, origin=origin, spacing=spacing )

        for metric in coreg_metrics :
            print("t1 ",t1)
            fixed = image_read( t1  )
            moving = image_read( pet )
            try :
                metric_val = ants.create_ants_metric(    
                        fixed = fixed, 
                        moving= moving,
                        fixed_mask=ants.image_read( brain_mask_space_mri  ),
                        moving_mask=ants.image_read( pet_brain_mask ),
                        metric_type=metric ).get_value()
            except RuntimeError : 
                metric_val = np.NaN
            temp = pd.DataFrame([['coreg',sid,ses,task,run,trc,rec,'01',metric,metric_val]],columns=df.columns  ) 
            sub_df = pd.concat([sub_df, temp])

        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output(self.inputs.sid, self.inputs.ses, self.inputs.task,self.inputs.run,self.inputs.rec,self.inputs.trc)

        sub_df.to_csv(self.inputs.out_file,  index=False)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output(self.inputs.sid, self.inputs.ses, self.inputs.task,self.inputs.run,self.inputs.rec,self.inputs.trc)
        outputs["out_file"] = self.inputs.out_file
        return outputs

### Plot Metrics
#           analysis    sub     ses     task    metric  roi     value
#    0      coreg       19      F       1       CC      1       0.717873
class plot_qcOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class plot_qcInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")
    out_file = traits.File(desc="Output file")

class plot_qcCommand (BaseInterface):
    input_spec = plot_qcInput 
    output_spec = plot_qcOutput

    def _gen_output(self, basefile="metrics.png"):
        fname = ntpath.basename(basefile)
        dname = os.getcwd() 
        return dname+ os.sep+fname

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(plot_qcCommand, self)._parse_inputs(skip=skip)

    def _run_interface(self, runtime):
        df = pd.read_csv( self.inputs.in_file  )
        if "measure"  in df.columns:
            plot_type="measure"
        elif "metric"  in df.columns :
            plot_type = "metric"
        else:
            print("Unrecognized data frame")
            exit(1)
        df["sub"]="sub: "+df["sub"].map(str)+" task: "+df["task"].map(str)+" ses: "+df["ses"].map(str) 
        print(df)
        plt.clf()
        fig, ax = plt.subplots()
        plt.figure(1)
        nROI = len(np.unique(df.roi))

        if plot_type == "measure" : 
            unique_measure =np.unique(df.measure)
            nMeasure = np.unique(unique_measure)

        unique_metric = np.unique(df.metric)
        nMetric = len(unique_metric)
        for roi, i in zip(np.unique(df.roi), range(nROI)):
            df0=df[ (df.roi==roi)  ]
            for metric in unique_metric :
                x=df0.value[df.metric == metric]

            if plot_type == "measure" : 
                sns.factorplot(x="metric", col="measure", y="value", kind="swarm",  data=df0, legend=False, hue="sub")
            else : 
                sns.factorplot(x="metric", y="value",   data=df0,  kind="swarm",  hue="sub")
            plt.ylabel('')
            plt.xlabel('')

            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.ylim([-0.05,1.05])
            plt.legend(bbox_to_anchor=(1.05, 1), loc="upper right", ncol=1, prop={'size': 6})
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        print('Out file:', self.inputs.out_file)
        #plt.tight_layout()
        plt.savefig(self.inputs.out_file, bbox_inches="tight", dpi=300, width=2000)
        plt.clf()
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs



#########################
### Outlier measures  ###
#########################
class outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class outlier_measuresInput(BaseInterfaceInputSpec):
    in_file = traits.File(desc="Input file")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)


class outlier_measuresCommand(BaseInterface):
    input_spec = outlier_measuresInput 
    output_spec = outlier_measuresOutput

    def _gen_output(self, fname ="measures.csv"):
        dname = os.getcwd() + os.sep + fname
        return dname

    def _run_interface(self, runtime):
        df = pd.read_csv( self.inputs.in_file  )
        out_columns=['sub','ses','task','roi','metric','measure', 'value'] 
        df_out = pd.DataFrame(columns=out_columns)

        for ses, ses_df in df.groupby(['ses']):
            for task, task_df in ses_df.groupby(['task']):
                for measure, measure_name in zip(outlier_measures.values(), outlier_measures.keys()):
                    for metric_name, metric_df in task_df.groupby(['metric']):
                        metricValues = metric_df.value.values
                        if len(metricValues.shape) == 1 : metricValues = metricValues.reshape(-1,1)
                        if 'cdf' in inspect.getargspec(measure).args :
                            if 'coreg' or 'pvc' in metric_df.analysis: cdf=True
                            else : cdf=False
                            m=np.array(measure(metricValues, cdf=cdf))
                        else : m=np.array(measure(metricValues))
                        if len(m.shape) > 1 : m = m.flatten()
                        r=pd.Series(m)

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


#############
# Visual QC #
#############

def groupLevel_visual_qc(opts, args):
    #setup workflow
    file_dir, fn =os.path.split( os.path.abspath(__file__) )
    html_fn = file_dir + os.sep + 'qc.html' 

    if not os.path.exists(opts.targetDir+'/html'):
        os.makedirs(opts.targetDir+'/html')

    os.chdir(opts.targetDir+'/html')
    print('Writing html dashboard',opts.targetDir+'/html')
    if not os.path.exists('data'):
        os.makedirs('data')

    fn_list = glob(opts.targetDir+os.sep+opts.preproc_dir+os.sep+'*/visual_qc/*_summary.json')

    #initialize and run class for building html dashboard
    QCHTML(opts.targetDir, fn_list).build()



class visual_qcOutput(TraitedSpec):
    pet_3d_gif = traits.File(desc="Output file")
    pet_coreg_gif = traits.File(desc="Output file")
    pet_coreg_edge_2_gif = traits.File(desc="Output file")
    quant_labels_gif = traits.File( desc="Output File")
    results_labels_gif = traits.File(exists=True, mandatory=False, desc="Output File")
    pvc_labels_gif = traits.File( desc="Output File")
    pvc_gif = traits.List(desc="Output file")
    quant_gif = traits.File(desc="Output file")
    out_json = traits.File(desc="Output file")
    template_alignment_gif = traits.File(desc="Output file")

class visual_qcInput(BaseInterfaceInputSpec):
    targetDir = traits.File(mandatory=True, desc="Target directory")
    sourceDir = traits.File(mandatory=True, desc="Source directory")
    pvc_method = traits.Str(desc="PVC method")
    quant_method = traits.Str(desc="TKA method")
    analysis_space = traits.Str(desc="Analysis Space")
    pet_3d = traits.File(exists=True, mandatory=True, desc="PET image")
    pet = traits.File(exists=True, mandatory=True, desc="PET image")
    pet_space_mri = traits.File(exists=True, mandatory=True, desc="Output PETMRI image")
    pet_brain_mask = traits.File(exists=True, mandatory=True, desc="Output PET Brain Mask")
    mri_space_nat = traits.File(exists=True, mandatory=True, desc="Output T1 native space image")
    template_space_mri = traits.File(exists=True, mandatory=True, desc="Output T1 native space image")
    mri_brain_mask = traits.File(exists=True, mandatory=False, desc="MRI brain mask (t1 native space)")

    results_labels = traits.File(exists=True, mandatory=False, desc="Label volume used for results stage")
    quant_labels = traits.File( desc="Label volume used for quant stage")
    pvc_labels = traits.File( desc="Label volume used for pvc stage")

    t1_analysis_space = traits.File(exists=True, mandatory=True, desc="Output T1 in analysis space image")
    quant_plot = traits.File(exists=True, mandatory=False, desc="Quantification Plot")
    pvc = traits.File(exists=True, desc="Output PVC image")
    quant = traits.File(exists=True, desc="Output TKA image")
    sub =traits.Str(default_value='NA', mandatory=True)
    ses=traits.Str(default_value='NA',usedefault=True)
    task=traits.Str(default_value='NA',usedefault=True)
    run=traits.Str(default_value='NA',usedefault=True)
    pet_3d_gif = traits.File(desc="Output file")
    pet_coreg_edge_2_gif = traits.File(desc="Output file")
    pet_coreg_gif = traits.File(desc="Output file")
    pvc_gif = traits.List(desc="Output file")
    quant_gif = traits.File(desc="Output file")
    template_alignment_gif = traits.File(desc="Output file")

    quant_labels_gif = traits.File(desc="Output File")
    results_labels_gif = traits.File(desc="Output File")
    pvc_labels_gif = traits.File(desc="Output File")

    out_json = traits.File(desc="Output file")


class visual_qcCommand(BaseInterface):
    input_spec = visual_qcInput 
    output_spec = visual_qcOutput

    def _gen_output(self, fname):
        out_str = 'sub-'+self.inputs.sub

        if self.inputs.ses != 'NA' and self.inputs.ses != '' :
            out_str += '_'+ 'ses-' + self.inputs.ses
        if self.inputs.task != 'NA'  and self.inputs.task != ''  :
            out_str += '_'+'task-' + self.inputs.task
        if self.inputs.run != 'NA'  and self.inputs.run != ''  :
            out_str +=  '_'+'run-' + self.inputs.run
        dname = os.getcwd() + os.sep + out_str + fname
        return dname

    def _run_interface(self, runtime):
        #Set outputs
        self.inputs.pet_3d_gif = self._gen_output('_pet_3d.gif')
        self.inputs.pet_coreg_gif = self._gen_output('_coreg.gif')
        self.inputs.pet_coreg_edge_2_gif = self._gen_output('_coreg_edge_2.gif')
        self.inputs.results_labels_gif = self._gen_output('_results_labels.gif')
        self.inputs.template_alignment_gif = self._gen_output('_template_alignment.gif')
        self.inputs.out_json = self._gen_output('_summary.json')

        d={'sub':self.inputs.sub, 'ses':self.inputs.ses, 
                'task':self.inputs.task, 'run':self.inputs.run,
                'base':self._gen_output('')}
        d['pet_3d']=self.inputs.pet_3d_gif
        d['results_labels_gif']=self.inputs.results_labels_gif
        d['coreg']=self.inputs.pet_coreg_gif
        d['coreg_edge_2']=self.inputs.pet_coreg_edge_2_gif


        visual_qc_images=[  
                ImageParam(self.inputs.pet_3d , self.inputs.pet_3d_gif, self.inputs.pet_brain_mask, cmap1=plt.cm.Greys, cmap2=plt.cm.Reds, alpha=[0.3], duration=300),
                ImageParam(self.inputs.pet_space_mri , self.inputs.pet_coreg_gif, self.inputs.mri_space_nat, alpha=[0.55,0.70,0.85], duration=400,  nframes=15 ),
                ImageParam(self.inputs.pet_space_mri , self.inputs.pet_coreg_edge_2_gif, self.inputs.mri_space_nat, alpha=[0.4], duration=300, edge_2=1, cmap1=plt.cm.Greys, cmap2=plt.cm.Reds ),
                # Results Labels
                ImageParam(self.inputs.t1_analysis_space, self.inputs.results_labels_gif, self.inputs.results_labels, alpha=[0.4], duration=300, cmap1=plt.cm.Greys, cmap2=plt.cm.nipy_spectral ),
                ImageParam(self.inputs.mri_space_nat, self.inputs.template_alignment_gif, self.inputs.template_space_mri, alpha=[0.4], duration=300, cmap1=plt.cm.Greys, cmap2=plt.cm.Reds )
                ]

        if isdefined(self.inputs.pvc) :
            dims = nib.load(self.inputs.pvc).shape
            time_frames = 1 if len(dims) == 3 else dims[3]
            #
            self.inputs.pvc_gif = [ self._gen_output('_%d_pvc.gif'%f) for f in range(time_frames)]
            visual_qc_images.append( ImageParam(self.inputs.pvc , self.inputs.pvc_gif, self.inputs.t1_analysis_space, alpha=[0.25], duration=300, time_frames=time_frames, ndim=len(dims), nframes=15,colorbar=True))
            d['pvc'] = self.inputs.pvc_gif

            # PVC Labels
            self.inputs.pvc_labels_gif = self._gen_output('_pvc_labels.gif')
            visual_qc_images.append(ImageParam(self.inputs.t1_analysis_space, self.inputs.pvc_labels_gif, self.inputs.pvc_labels, alpha=[0.4], duration=300, cmap1=plt.cm.Greys, cmap2=plt.cm.nipy_spectral ))
            d['pvc_labels_gif']=self.inputs.pvc_labels_gif

        if isdefined(self.inputs.quant) :
            #
            self.inputs.quant_gif = self._gen_output('_quant.gif')
            visual_qc_images.append( ImageParam(self.inputs.quant , self.inputs.quant_gif, self.inputs.t1_analysis_space, alpha=[0.35], duration=300, colorbar=True ))
            d['quant'] = self.inputs.quant_gif
            d['quant_plot'] = self.inputs.quant_plot

            # Quant Labels
            print('\n\n\nQUANT LABELS\n\n\n')
            self.inputs.quant_labels_gif = self._gen_output('_quant_labels.gif')
            visual_qc_images.append(ImageParam(self.inputs.t1_analysis_space, self.inputs.quant_labels_gif, self.inputs.quant_labels, alpha=[0.4], duration=300, cmap1=plt.cm.Greys, cmap2=plt.cm.nipy_spectral ))
            print(self.inputs.quant_labels_gif)
            print(os.path.exists(self.inputs.quant_labels_gif))
            d['quant_labels_gif']=self.inputs.quant_labels_gif
            
        for image in visual_qc_images :
            image.volume2gif() 

        json.dump( d, open(self.inputs.out_json,'w+'))
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["pet_3d_gif"] = self.inputs.pet_3d_gif
        outputs["pet_coreg_gif"] = self.inputs.pet_coreg_gif
        outputs["pet_coreg_edge_2_gif"] = self.inputs.pet_coreg_edge_2_gif
        outputs["template_alignment_gif"] = self.inputs.template_alignment_gif

        outputs["results_labels_gif"] = self.inputs.results_labels_gif
        outputs["pvc_labels_gif"] = self.inputs.pvc_labels_gif
        outputs["quant_labels_gif"] = self.inputs.quant_labels_gif

        outputs["out_json"] = self.inputs.out_json
        if isdefined(self.inputs.pvc) :
            outputs["pvc_gif"] = self.inputs.pvc_gif

        if isdefined(self.inputs.quant) :
            outputs["quant_gif"] = self.inputs.quant_gif

        return outputs

def get_slices(vol,  dim, i) :

    if dim == 0:
        r = vol[i, :, : ]
    elif dim == 1 :
        r = vol[ :, i, : ]
    else :
        r = vol[ :, :, i ]
    return r

class ImageParam():
    def __init__(self,in_fn,out_fn, overlay_fn=None, alpha=[1.], dpi=100, duration=100, cmap1=plt.cm.nipy_spectral, cmap2=plt.cm.gray, colorbar=False, edge_1=-1, edge_2=-1,nframes=15, time_frames=1, ndim=3):
        self.in_fn = in_fn
        self.out_fn = out_fn
        self.alpha = alpha
        self.dpi = dpi
        self.overlay_fn = overlay_fn
        self.duration = duration
        self.cmap1 = cmap1
        self.cmap2 = cmap2
        self.colorbar=colorbar
        self.edge_1 = edge_1
        self.edge_2 = edge_2
        self.nframes = nframes
        self.ndim = ndim
        self.time_frames=time_frames

    def load_isotropic(self,in_fn,t=0):
        aff = nib.load(in_fn).affine
        vol_img, vol = load_3d(in_fn,t)
        sep =[ get_spacing(vol_img.affine, i) for i in range(3) ]
        min_unit=np.min(np.abs(sep))
        #new_units=[min_unit*np.sign(sep[0]), min_unit*np.sign(sep[1]), min_unit*np.sign(sep[2]) ] 
        vol_img = resample_to_output(vol, aff, [min_unit]*3,order=1 )
        vol=vol_img.get_fdata()
        return vol_img, vol

    def volume2gif(self):
        in_fn = self.in_fn
        out_fn = self.out_fn
        overlay_fn = self.overlay_fn
        alpha  = self.alpha
        dpi = self.dpi
        duration  = self.duration
        cmap1 = self.cmap1
        cmap2 = self.cmap2

        def apply_tfm(img, sigma):
            if sigma >= 0  : 
                img = gaussian_filter(img, sigma)
                img = np.sqrt(np.sum(np.abs(np.gradient(img)),axis=0)) 
                img[ img < threshold_otsu(img) ] =0 
            return img
        img = nib.load(in_fn)
        ndim=len(img.shape)
        full_vol = img.get_data()
        vmin, vmax  = (np.min(full_vol)*.02, np.max(full_vol)*0.98 )
        tmax=1
        if ndim == 4 :
            tmax = nib.load(in_fn).shape[3]
        for t in range(tmax) :
            vol_img, vol = self.load_isotropic(in_fn,t)
            vol = apply_tfm(vol,self.edge_1)

            if overlay_fn != None :
                overlay_img, overlay_vol = self.load_isotropic(overlay_fn)
                overlay_vol = apply_tfm(overlay_vol,self.edge_2)
                omin, omax  = (np.min(overlay_vol), np.max(overlay_vol) )#np.percentile(vol, [1,99])

            #np.percentile(vol, [1,99])

            frames=[]
            plt.clf()
            fig = plt.figure()

            axes=[fig.add_subplot(1, 3, ii) for ii in [1,2,3]]
            axes[0].axis("off")
            axes[1].axis("off")
            axes[2].axis("off")

            frame=[ axes[ii].imshow(get_slices(vol,ii,0), cmap=cmap1, animated=True,origin='lower', vmin=vmin, vmax=vmax, interpolation='gaussian' ) for ii in [0,1,2]]
            nframes_per_alpha= self.nframes
            total_frames=nframes_per_alpha * len(alpha) 
            def animate(i):
                alpha_level = int(i / nframes_per_alpha)
                ii = i % nframes_per_alpha
                for dim in [0,1,2] :
                    idx = np.round(vol.shape[dim] * ii / (self.nframes+0.0)).astype(int)
                    r = get_slices(vol, dim, idx)

                    frame[dim] = axes[dim].imshow(r.T, cmap=cmap1, animated=True,origin='lower', vmin=vmin, vmax=vmax, interpolation='gaussian' )

                    if overlay_fn != None :
                        m = get_slices(overlay_vol, dim, idx)
                        frame[dim] = axes[dim].imshow(m.T,alpha=alpha[alpha_level], cmap=cmap2, vmin=omin, vmax=omax, interpolation='gaussian', origin='lower', animated=True)
                return frame

            if self.colorbar :
                fig.colorbar(frame[2], shrink=0.35 )
            plt.tight_layout()
            stime=time.time()
            ani = animation.FuncAnimation(fig, animate, frames=total_frames, interval=duration, blit=True, repeat_delay=1000)
            if ndim == 4 :
                out_fn = self.out_fn[t] 
            ani.save(out_fn, dpi=self.dpi) #, writer='imagemagick')
            #print(time.time()-stime)  
            print('Writing', out_fn)

class QCHTML() :
    '''
    This class serves to create an html file with visual qc. It requires extracting images and gifs from the output data produced by a run of APPIAN.

    Inputs:
        fn_list :   list of json files that contains paths to images/gifs used for qc
        targetDir : output directory where html files will be saved 
    '''

    def __init__(self, targetDir, fn_list):
        self.fn_list = fn_list
        self.targetDir=targetDir
        self.d = {} #dictionary that keeps track of html files that are created for each of the scans in fn_list
        for fn in fn_list :
            #populate dictionary with name of scan
            self.d[fn] = json.load(open(fn,'r'))
            #set the html filename for this scan
            self.d[fn]['html_fn'] = targetDir + '/html/' + os.path.basename(self.d[fn]['base'])+'.html' 

    def sidebar(self, vol_list):
        '''
        Create a sidebar with the names of the subjects. Allows user to switch between subjects.
        '''
        out_str=''

        for i, fn in enumerate(self.fn_list) :
            base = os.path.basename(self.d[fn]['base'])
            stage_string = self.get_stage_list(vol_list, base)
            subject_string = re.sub( '_', ' ', re.sub('-',': ', base))

            out_str +='<div><buttonclass="w3-button w3-block w3-left-align" onclick="myAccFunc(\'accordion%d\')">%s </button>\n' % (i, subject_string)
            out_str +='<div  id=\'accordion%d\'   class="w3-bar-block w3-hide w3-black w3-card-4">\n' % i
            out_str +='%s\n' % stage_string

            out_str +='\t\t\t</div>\n\t\t</div>\n' 
        out_str+='\t</div>\n'
        return out_str

    def get_stage_list(self, vol_list,base):
        'read list of stages that were run based on vol_list'
        stage_list=''
        for i, (ID, H1, H2) in enumerate(vol_list) :
            valid_id=False
            for fn in self.fn_list :
                try :
                    self.d[fn][ID] #check if valid entry in dictionary
                    valid_id=True
                    break
                except KeyError :
                    continue
            if valid_id and H1 != None :
                var = './'+base+'.html#'+H1
                stage_list += '\t\t<a href="%s" class="w3-bar-item w3-button">%s</a>\n' % (var, H1)
        
        return stage_list

    def build(self) :
        '''
            This method creates an html file for each scan in self.d. To do this it looks at which qc images/gifs
            are defined for this scan. 

        '''
        #qc_stages contains the qc stages. for each stage there is an ID for the stage, a header H1, and a subheader H2 
        qc_stages = (
                ('pet_3d','Initialization','3D Volume + Brain Mask'), 
                ('template_alignment_gif','Template Alignment','MRI Vs aligned template'), 
                ('coreg', 'Coregistration', 'PET + MRI Overlap' ), 
                ('coreg_edge_2', None, 'PET + MRI Edge' ),
                ('results_labels_gif', 'Labels','Results'),
                ('pvc_labels_gif', None,'PVC'),
                ('quant_labels_gif', None, 'Reference Region'),
                ('pvc', 'Partial-volume Correction', 'Volume' ),
                ('quant', 'Quantification', 'Volume'),
                ('quant_plot', None, 'Time Activity Curves' ))

        #copy some cores css files to target directory so that we can use their formatting 
        shutil.copy(_file_dir+'/w3.css', self.targetDir+'/html/w3.css')
        shutil.copy(_file_dir+'/font-awesome.min.css', self.targetDir+'/html/font-awesome.min.css')

        #for each scan in the dictionary
        for fn, scan_dict in self.d.items() :
            #here we create the output html file
            with open(scan_dict['html_fn'],'w') as html_file:
                #write some standard output to the html file that is common to all scans
                html_file.writelines( self.start())
                #write the sidebar to the html file. 
                #the sidebar contains information about which scans and stages were run
                html_file.writelines(self.sidebar(qc_stages))
                #single line that is common to all html files
                html_file.writelines('<div style="margin-left:260px">\n')
                #for each qc stages, write the html to include it in dashboard
                for ID, H1, H2 in  qc_stages :
                    self.vol(ID, scan_dict, html_file, h1=H1, h2=H2)
                self.end(html_file)

    def start(self):
        out_str='''<!DOCTYPE html>
<html lang="en">
<head>
<title>APPIAN</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="w3.css">

<meta charset="UTF-8">
<style>
body { font-family: Verdana, Helvetica, sans-serif;  }
.w3-button{white-space:normal; padding:4px 8px }
.mySlides {display:none;}
</style>
</head>
<body>

<div class="w3-sidebar w3-bar-block w3-collapse w3-card w3-animate-left w3-black" style="width:200px;" id="mySidebar">
'''
        return out_str
    
    def vol(self, src, d, html_file, h1=None, h2=None):
        try :
            out_str=''
            if h1 != None : 
                out_str+='<div id=%s> <h1>%s</h1>\n' % (h1, h1)
                out_str+='<hr class="dashed">\n'
            if h2 != None : 
                out_str+='<h2>'+h2+'</h2>\n'

            #QC gifs can either be a filepath or a list of filepaths
            #Lists of file paths are used for displaying volumes with multiple frames
            if not type(d[src]) == list :
                out_str+='<img src="'+'data/'+os.path.basename(d[src])+'" style="width:50%">\n'
                shutil.copy(d[src], 'data/'+os.path.basename(d[src]))
            else : 
                out_str += '<div class="w3-content w3-display-container">\n'
                for fn in d[src] : 
                    shutil.copy(fn, 'data/'+os.path.basename(fn))
                    out_str += '<img class=mySlides src=\"data/%s\" style="width:100">\n'%os.path.basename(fn)
                out_str+='<button class="w3-button w3-black w3-display-left" onclick="plusDivs(-1)">&#10094;</button>\n'
                out_str+='<button class=\"w3-button w3-black w3-display-right\" onclick=\"plusDivs(1)\">&#10095;</button>\n'
                out_str+='</div>'
            html_file.writelines(out_str)  
        except KeyError :
            pass

    def end(self, html_file):
        out_str='''</div>
<script>


function myAccFunc(id) {
  console.log(id)
  var x = document.getElementById(id);
  console.log(x)
  console.log(x.className.indexOf("w3-show"))
  
  if (x.className.indexOf("w3-show") == -1) {
    x.className += " w3-show";
    x.previousElementSibling.className = 
    x.previousElementSibling.className.replace("w3-black", "w3-red");
  }
   else { 
    x.previousElementSibling.className = 
    x.previousElementSibling.className.replace("w3-red", "w3-black");
  }
}

var slideIndex = 1;
showDivs(slideIndex);

function plusDivs(n) {
  showDivs(slideIndex += n);
}

function showDivs(n) {
  var i;
  var x = document.getElementsByClassName("mySlides");
  if (n > x.length) {slideIndex = 1}
  if (n < 1) {slideIndex = x.length} ;
  for (i = 0; i < x.length; i++) {
    x[i].style.display = "none";
  }
  x[slideIndex-1].style.display = "block";
}


</script>
</body>
</html>'''
        html_file.writelines(out_str)  
