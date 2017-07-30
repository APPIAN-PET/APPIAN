import nipype
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,  BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import pyminc.volumes.factory as pyminc

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.cm as cm
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import fnmatch
import os
import shutil
from math import sqrt, floor, ceil
from os import getcwd
from os.path import basename
from sys import argv, exit
from re import sub
from Quality_Control.outlier import lof, kde, MAD, lcf
import nipype.interfaces.minc.resample as rsl
import Quality_Control as qc
import random



# Name: group_coreg_qc_test
# Purpose: Test the ability of group_coreg_qc to detect misregistration of T1 and PET images. This is done by
#          creating misregistered PET images for each subject by applying translations and rotations to the PET
#          image. For each misregistered PET image, we run group_coreg_qc to see how much the misregistration 
#          affects group qc metrics.


normal_param='0 0 0'
def get_misalign_pet_workflow(name, opts):
    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    #FIXME: Should have angles and offsets defined by user. Use ';' to seperate elements
    angles=['0 0 0', '0 0 2', '0 0 4', '0 0 8', '0 0 16', '0 0 32', '0 0 64'] #X,Y,Z angle of rotation
    #angles=['0,0,0', '0,0,2', '0,0,4', '0,0,8', '0,0,16'#, '0,0,32', '0,0,64'] #X,Y,Z angle of rotation
    offsets=['0 0 0', '0 0 2', '0 0 4', '0 0 8', '0 0 10', '0 0 12', '0 0 14' ] #X,Y,Z offset of translation (in mm)
    #offsets=['0,0,0', '0,0,2', '0,0,4', '0,0,8', '0,0,10']#, '0,0,12', '0,0,14' ] #X,Y,Z offset of translation (in mm)
    
    inputnode=pe.Node(interface=niu.IdentityInterface(fields=['pet', 'brainmask', 'sid', 'cid', 'study_prefix']), name='inputnode')
    outputnode=pe.Node(interface=niu.IdentityInterface(fields=['translated_pet', 'rotated_pet', 'rotated_brainmask', 'translated_brainmask']), name='outputnode')
    #########################
    # 1. Create param files #
    #########################
    ### A. Rotate
    ###Use iterables to split the list of angles into seperate streams
    angle_splitNode = pe.Node(interface=niu.IdentityInterface(fields=['angle']), name='angle_splitNode')
    angle_splitNode.iterables=('angle', angles)
    ###Create rotation xfm files based on rotation angle
    rotateNode = pe.Node(interface=rsl.param2xfmCommand(), name='rotateNode')
    workflow.connect(angle_splitNode, 'angle', rotateNode, 'rotation')
    ###Apply transformation to PET file
    rotate_resampleNode=pe.Node(interface=rsl.ResampleCommand(), name="rotate_resampleNode" )
    rotate_resampleNode.inputs.use_input_sampling=True;
    workflow.connect(rotateNode, 'out_file', rotate_resampleNode, 'transformation')
    workflow.connect(inputnode, 'pet', rotate_resampleNode, 'in_file')
    ###Rename resampled pet image
    rrotate_resampleNode=pe.Node(interface=myIdent(param_type='angle'),  name="rrotate_resampleNode")
    workflow.connect(rotate_resampleNode, 'out_file', rrotate_resampleNode, 'in_file')
    workflow.connect(angle_splitNode, 'angle', rrotate_resampleNode, 'param')
    ###Rotate brain mask
    rotate_brainmaskNode=pe.Node(interface=rsl.ResampleCommand(), name="rotate_brainmaskNode" )
    rotate_brainmaskNode.inputs.use_input_sampling=True;
    workflow.connect(rotateNode, 'out_file', rotate_brainmaskNode, 'transformation')
    workflow.connect(inputnode, 'brainmask', rotate_brainmaskNode, 'in_file')   
    ###Rename rotated  brain mask 
    rrotate_brainmaskNode=pe.Node(interface=myIdent(param_type='angle'),  name="rrotate_brainmaskNode")
    workflow.connect(rotate_brainmaskNode, 'out_file', rrotate_brainmaskNode, 'in_file')
    workflow.connect(angle_splitNode, 'angle', rrotate_brainmaskNode, 'param')

    ###Join the rotation nodes back together
    join_rotationsNode = pe.JoinNode(interface=niu.IdentityInterface(fields=["angle","rotated_brainmask"]), joinsource="angle_splitNode", joinfield=["angle", "rotated_brainmask"], name="join_rotationsNode")
    join_rotationsNode.inputs.angle=[]
    workflow.connect(rrotate_resampleNode, 'out_file', join_rotationsNode, 'angle')
    workflow.connect(rrotate_brainmaskNode, 'out_file', join_rotationsNode, 'rotated_brainmask')
    ###Send rotated pet images to output node
    workflow.connect(join_rotationsNode, 'rotated_brainmask', outputnode, 'rotated_brainmask')
    workflow.connect(join_rotationsNode, 'angle', outputnode, 'rotated_pet')

    ### B. Translate
    ###Use iterables to split the list of offsets into seperate streams
    offset_splitNode = pe.Node(interface=niu.IdentityInterface(fields=['offset']), name='offset_splitNode')
    offset_splitNode.iterables=('offset', offsets)
    ###Create translation xfm files based on translation offset
    translateNode = pe.Node(interface=rsl.param2xfmCommand(), name='translateNode')
    workflow.connect(offset_splitNode, 'offset', translateNode, 'translation')
    ###Apply translation to PET image
    translate_resampleNode=pe.Node(interface=rsl.ResampleCommand(), name="translate_resampleNode" )
    translate_resampleNode.inputs.use_input_sampling=True;
    workflow.connect(inputnode, 'pet', translate_resampleNode, 'in_file')
    workflow.connect(inputnode, 'pet', translate_resampleNode, 'model_file')
    workflow.connect(translateNode, 'out_file', translate_resampleNode, 'transformation')
    ###Rename translated resampled pet image
    rtranslate_resampleNode=pe.Node(interface=myIdent(param_type='offset'),  name="rtranslate_resampleNode")
    workflow.connect(translate_resampleNode, 'out_file', rtranslate_resampleNode, 'in_file')
    workflow.connect(offset_splitNode, 'offset', rtranslate_resampleNode, 'param')
    ###Apply translation to brain mask image
    translate_brainmaskNode=pe.Node(interface=rsl.ResampleCommand(), name="translate_brainmaskNode" )
    translate_brainmaskNode.inputs.use_input_sampling=True;
    workflow.connect(inputnode, 'brainmask', translate_brainmaskNode, 'in_file')
    workflow.connect(inputnode, 'pet', translate_brainmaskNode, 'model_file')
    workflow.connect(translateNode, 'out_file', translate_brainmaskNode, 'transformation')
    ###Rename translated brain mask
    rtranslate_brainmaskNode=pe.Node(interface=myIdent(param_type='offset'),  name="rtranslate_brainmaskNode")
    workflow.connect(translate_brainmaskNode, 'out_file', rtranslate_brainmaskNode, 'in_file')
    workflow.connect(offset_splitNode, 'offset', rtranslate_brainmaskNode, 'param')

    ###Join the translations nodes back together
    join_translateNode = pe.JoinNode(interface=niu.IdentityInterface(fields=["offset", "translated_brainmask"]), joinsource="offset_splitNode", joinfield=["offset", "translated_brainmask"], name="join_translateNode")

    join_translateNode.inputs.offset=[]
    workflow.connect(rtranslate_resampleNode, 'out_file', join_translateNode, 'offset')
    workflow.connect(rtranslate_brainmaskNode, 'out_file', join_translateNode, 'translated_brainmask')
    ###Send translated pet images to output node 
    workflow.connect(join_translateNode, 'offset', outputnode,'translated_pet')
    workflow.connect(join_translateNode, 'translated_brainmask', outputnode,'translated_brainmask')

    return(workflow)


############################################################################
# Workflow to calculate distance metrics, outlier measures, and ROC curves #
############################################################################
distance_metrics={'MI':qc.mi, 'FSE':qc.fse, 'CC':qc.cc }  
#distance_metrics={'FSE':qc.fse }  
#outlier_measures={"LOF":lof} 
#outlier_threshold={"LOF":np.arange(0,1,0.05) } 

outlier_measures={"KDE":kde } #{'LCF':lcf, "KDE":kde , 'MAD':MAD} #, 'LCF':lcf}
outlier_threshold={"KDE":np.arange(0,1,0.05)}#, 'LCF':np.arange(-2,2,0.05),"MAD":np.arange(-10,10,1) } 

### NODES

#
# Distance metric
#
class distance_metricOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class distance_metricInput(BaseInterfaceInputSpec):
    M=False
    rotated_pet = traits.List( mandatory=M, desc="Input list of translated PET images")
    translated_pet = traits.List( mandatory=M, desc="Input list of rotated PET images") 
    rotated_brainmask = traits.List( mandatory=M, desc="Input list of translated brain mask images")
    translated_brainmask = traits.List( mandatory=M, desc="Input list of rotated brain mask images")
    t1_images = traits.File( mandatory=M, desc="Input list of T1 images")
    pet_images = traits.File( mandatory=M, desc="Input list of PET images")
    brain_masks = traits.File( mandatory=M, desc="Input list of brain masks images")
    subjects= traits.Str( mandatory=M, desc="Input list of subjects")
    conditions= traits.Str( mandatory=M, desc="List of conditions")
    study_prefix= traits.Str( mandatory=M, desc="Prefix of study")
    colnames = traits.List(mandatory=M,desc="Column names for Pandas DataFrame")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)

class distance_metricCommand(BaseInterface):
    input_spec = distance_metricInput 
    output_spec = distance_metricOutput
  
    def _gen_output(self,fname ="test_group_qc_metric.csv"):
        dname = os.getcwd() 
        return dname+ os.sep+fname

    def _run_interface(self, runtime):
        #######################################################
        # Create lists of misaligned PET images to pass to QC #
        #######################################################

        study_prefix=self.inputs.study_prefix
        rotated_brainmask=self.inputs.rotated_brainmask
        subjects=self.inputs.subjects
        conditions=self.inputs.conditions
        pet_images=self.inputs.pet_images
        t1_images=self.inputs.t1_images
        t1_brain_masks=self.inputs.brain_masks
        translated_pet=self.inputs.translated_pet
        translated_brainmask=self.inputs.translated_brainmask
        rotated_pet=self.inputs.rotated_pet
        outlier_measure_list=[]
        flatten = lambda  l: [ j for i in l for j in i]
        #rotated_pet = flatten(rotated_pet)
        #translated_pet=flatten(translated_pet)
        misaligned=rotated_pet + translated_pet 
        
        #rotated_brainmask    = flatten(rotated_brainmask)
        #translated_brainmask = flatten(translated_brainmask)
        misaligned_brainmask = rotated_brainmask + translated_brainmask

        
        
        colnames = list(self.inputs.colnames)
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()

        df=pd.DataFrame(columns=colnames)
        df=calc_distance_metrics(df, subjects, conditions, misaligned, pet_images, t1_images, t1_brain_masks, misaligned_brainmask, distance_metrics)
        df.to_csv(self.inputs.out_file, index=False)
        #shutil.copy("/data0/projects/scott/test_group_qc_metric.csv", self.inputs.out_file) 
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()

        outputs["out_file"] = self.inputs.out_file
        return outputs

#
# Outlier measures 
#

class outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class outlier_measuresInput(BaseInterfaceInputSpec):
    normal_param = traits.Str(mandatory=True, desc="Normal alignment parameter (eg 0,0,0)")
    out_file = traits.File(desc="Output file")
    in_file = traits.File(exists=True,mandatory=True,desc="In file")

class outlier_measuresCommand(BaseInterface):
    input_spec = outlier_measuresInput 
    output_spec= outlier_measuresOutput
  
    def _gen_output(self, fname = "test_group_qc_outliers.csv"):
        dname = os.getcwd() 
        return dname+ os.sep+fname

    def _run_interface(self, runtime):
        #######################################################
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        normal_param = self.inputs.normal_param

        df=pd.read_csv(self.inputs.in_file)
        #Calculate the outlier measures based on group values of each distance metric
        df=calc_outlier_measures(df, outlier_measures, distance_metrics, normal_param)
        df.to_csv(self.inputs.out_file, index=False )
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs
#
# Outlier measures ROC
#

class outlier_measures_rocOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")
    auc_file = traits.File(desc="Output AUC file")

class outlier_measures_rocInput(BaseInterfaceInputSpec):
    outlier_threshold = traits.Dict(mandatory=True, desc="List of thresholds for outlier measures")
    normal_param = traits.Str(mandatory=True,desc="Normal alignment parameter (eg 0,0,0)")
    out_file = traits.File(desc="Output file")
    auc_file = traits.File(desc="Output AUC file")
    in_file = traits.File(exists=True,mandatory=True,desc="Input file")

class outlier_measures_rocCommand(BaseInterface):
    input_spec = outlier_measures_rocInput 
    output_spec= outlier_measures_rocOutput
    
    def _gen_output(self,fname = "test_group_qc_roc.csv" ):
        dname = os.getcwd() 
        return dname+ os.sep+fname
    
    def _run_interface(self, runtime):
        #Calculate ROC curves based on outlier measures
        outlier_threshold = self.inputs.outlier_threshold
        normal_param = self.inputs.normal_param
        df=pd.read_csv(self.inputs.in_file)
        self.inputs.out_file = self._gen_output()
        self.inputs.auc_file = self._gen_output("test_group_qc_auc.csv")
        [ roc_df, auc_df ]=outlier_measure_roc(df, outlier_threshold, normal_param)
        roc_df.to_csv(self.inputs.out_file, index=False)
        auc_df.to_csv(self.inputs.auc_file, index=False)

        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        outputs["auc_file"] = self.inputs.auc_file
        return outputs
#
# Plot distance metrics
#
class plot_distance_metricsOutput(TraitedSpec):
    out_files = traits.List(desc="Output file")

class plot_distance_metricsInput(BaseInterfaceInputSpec):
    #distance_metrics = traits.Dict(mandatory=True,desc="Dictionary with distance metrics")
    out_files = traits.List(desc="Output file")
    in_file = traits.File(exists=True, mandatory=True,desc="Input file")

class plot_distance_metricsCommand(BaseInterface):
    input_spec = plot_distance_metricsInput 
    output_spec= plot_distance_metricsOutput
  
    def _gen_output(self, fname = 'distance_metrics.png'):
        dname = os.getcwd() 
        return dname+ os.sep+fname

    def _run_interface(self, runtime):
        #distance_metrics = self.inputs.distance_metrics

        df=pd.read_csv(self.inputs.in_file)

        out_file  = self._gen_output()
        self.inputs.out_files =  plot_distance_metrics(df, distance_metrics, out_file, color=cm.spectral)
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_files"] = self.inputs.out_files
        return outputs

#
# Plot outlier measures
#

class plot_outlier_measuresOutput(TraitedSpec):
    out_files = traits.List(desc="Output file")

class plot_outlier_measuresInput(BaseInterfaceInputSpec):
    #outlier_measures = traits.Dict(mandatory=True, desc="Dictionary with outlier measures")
    #distance_metrics = traits.Dict(mandatory=True,desc="Dictionary with distance metrics")
    out_files = traits.List(desc="Output file")
    in_file = traits.File(exists=True, mandatory=True,desc="Input file")

class plot_outlier_measuresCommand(BaseInterface):
    input_spec = plot_outlier_measuresInput 
    output_spec= plot_outlier_measuresOutput
  
    def _gen_output(self, fname = 'outlier_measures.png' ):
        dname = os.getcwd() 
        return dname+ os.sep+fname

    def _run_interface(self, runtime):
        #outlier_measures= self.inputs.outlier_measures
        #Calculate ROC curves based on outlier measures
        df=pd.read_csv(self.inputs.in_file)
        out_file = self._gen_output()
        self.inputs.out_files = plot_outlier_measures(df, outlier_measures, out_file, color=cm.spectral)

        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_files"] = self.inputs.out_files
        return outputs

#
# Plot ROC curves
#

class plot_rocOutput(TraitedSpec):
    out_files = traits.List(desc="Output files")

class plot_rocInput(BaseInterfaceInputSpec):
    error_type_unit=traits.Dict(desc="Error units")
    error_type_name=traits.Dict(desc="Error type")
    out_files = traits.List(desc="Output files")
    in_file = traits.File(desc="Input file")
    auc_file = traits.File(desc="AUC input file")

class plot_rocCommand(BaseInterface):
    input_spec = plot_rocInput 
    output_spec= plot_rocOutput
 

    def _run_interface(self, runtime):
        #Calculate ROC curves based on outlier measures
        df=pd.read_csv(self.inputs.in_file)
        df_auc=pd.read_csv(self.inputs.auc_file)
        error_type_unit=self.inputs.error_type_unit
        error_type_name=self.inputs.error_type_name
        self.inputs.out_files=plot_roc(df,df_auc, error_type_unit, error_type_name)

        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_files"] = self.inputs.out_files
        return outputs


### WORKFLOW

def get_test_group_coreg_qc_workflow(name, opts):
    workflow = pe.Workflow(name=name)
    params=['distance_metrics_df']
    inputnode=pe.Node(interface=niu.IdentityInterface(fields=params) , name='inputnode')
    outputnode=pe.Node(interface=niu.IdentityInterface(fields=['outlier_measures_df', 'roc_df', 'distance_metrics_plot', 'outlier_measures_plot', 'roc_plot']), name='outputnode')
    error_type_unit={"angle":"(degrees)",  "offset":'(mm)'} 
    error_type_name={"angle":'rotation',  "offset":'translation'} 
    colnames=["Subject", "Condition", "ErrorType", "Error", "Metric", "Value"] 
    
    #plot_distance_metricsCommand
    plot_distance_metricsNode=pe.Node(plot_distance_metricsCommand(), name="plot_distance_metrics")
    workflow.connect(inputnode, 'distance_metrics_df', plot_distance_metricsNode, 'in_file')
    
    #calculate outlier measures node
    outlier_measuresNode=pe.Node(interface=outlier_measuresCommand(), name="outlier_measures")
    workflow.connect(inputnode, 'distance_metrics_df', outlier_measuresNode, 'in_file')
    outlier_measuresNode.inputs.normal_param = normal_param
    
    #plot outlier measures node
    plot_outlier_measuresNode=pe.Node(plot_outlier_measuresCommand(), name="plot_outlier_measures")
    workflow.connect(outlier_measuresNode, 'out_file', plot_outlier_measuresNode, 'in_file')

    #calculate ROC for outlier measures
    rocNode=pe.Node(outlier_measures_rocCommand(), name="roc")
    rocNode.inputs.outlier_threshold=outlier_threshold
    rocNode.inputs.normal_param = normal_param
    workflow.connect(outlier_measuresNode, 'out_file', rocNode, 'in_file')

    #plot roc node
    plot_rocNode=pe.Node(plot_rocCommand(), name="plot_roc")
    plot_rocNode.inputs.error_type_unit = error_type_unit
    plot_rocNode.inputs.error_type_name = error_type_name
    workflow.connect(rocNode, 'out_file', plot_rocNode, 'in_file')
    workflow.connect(rocNode, 'auc_file', plot_rocNode, 'auc_file')

    workflow.connect(outlier_measuresNode, 'out_file', outputnode, 'outlier_measures_df')
    workflow.connect(rocNode, 'out_file', outputnode, 'roc_df')
    workflow.connect(plot_distance_metricsNode, 'out_files', outputnode, 'distance_metrics_plot')
    workflow.connect(plot_outlier_measuresNode, 'out_files', outputnode, 'outlier_measures_plot')
    workflow.connect(plot_rocNode, 'out_files', outputnode, 'outlier_measures_roc_plot')

    return workflow
    
### FUNCTIONS
def plot_roc(dfi, df_auc, error_type_unit, error_type_name, color=cm.spectral, DPI=500):
    df = dfi.copy()
    figs=[]
    fn_list=[]
    nMeasure=len(np.unique(df.Measure))
    #nMetric=len(np.unique(df.Metric))
    
    f=lambda x: float( str(x).split(' ')[-1] )

    df.Error = df.Error.apply(f)
    df_auc.Error = df_auc.Error.apply(f)
    nErrorType = len(np.unique(df.ErrorType) )
    for metric_name, metric in df.groupby(['Metric']):
        for measure_type_key, measure_type in metric.groupby(['Measure']):
        #    for metric_type_key, metric_type in measure_type.groupby(['Metric']):
            nUnique = float(len(measure_type.Error.unique() ))
            d = {key : color(value/nUnique) for (value, key) in enumerate(measure_type.Error.unique()) }

            for error_type_key, error_type in measure_type.groupby(['ErrorType']):
                plt.clf()
                fig=plt.figure()
                #ax = plt.subplot(nErrorType,1, 1)
                plt.title('ROC for outlier detection for error in ' +error_type_name[error_type_key])
                plt.ylabel('True positive rate')
                plt.xlabel('False positive rate')
                plt.plot([0,1], [0,1], 'k--', c='red')
                for key, test in error_type.groupby(['Error']):
                    x=test.FalsePositive#.append(pts)
                    y=test.TruePositive #.append(pts)
                    plt.plot(x,y, c=d[key], label=key)
                    plt.xlim(0,1)
                    plt.ylim(0,1)
                    #fig.alpha(0.25)
                    plt.legend(loc="lower right", fontsize=8, title='Error '+ error_type_unit[error_type_key])
                fn=os.getcwd()+os.sep + metric_name+'_'+error_type_key+'_'+measure_type_key+'_roc.png'
                fn_list += fn
                print  'saving roc plot to ' + fn
                plt.savefig(fn, width=1000, dpi=DPI)

    for metric_name, metric in df_auc.groupby(['Metric']):
        for measure_type_key, measure_type in metric.groupby(['Measure']):
            for error_type_key, error_type in measure_type.groupby(['ErrorType']):
                plt.clf()
                plt.title('AUC for outlier detection '+ measure_type_key +' for error in ' + error_type_key)
                plt.ylabel('AUC')
                plt.xlabel('Error')
                plt.scatter( error_type.Error, error_type.AUC)

                auc_fn=os.getcwd()+os.sep+metric_name+'_'+measure_type_key+'_'+error_type_key+'_auc.png'
                plt.savefig(auc_fn, width=1000, dpi=DPI)
                fn_list += auc_fn
    return(fn_list)


def  outlier_measure_roc(df, outlier_threshold, normal_error):
    subjects=np.unique(df.Subject)
    roc_columns=['ErrorType', 'Measure','Metric', 'Error','Threshold', 'FalsePositive', 'TruePositive' ]
    auc_columns=['ErrorType', 'Measure','Metric', 'Error', 'AUC' ]
    roc_df=pd.DataFrame(columns=roc_columns )
    auc_df=pd.DataFrame(columns=auc_columns )
    for metric_name, metric in df.groupby(['Metric']):
        for error_type_key, error_type in metric.groupby(['ErrorType']):
            for measure_type_key, measure_type in error_type.groupby(['Measure']):
                #for metric_type_key, metric_type in measure_type.groupby(['Metric']):
                #print measure_type
                normal=measure_type[measure_type.Error == normal_error]
                misaligned=measure_type[ ~(measure_type.Error == normal_error) ]
                for key, test in misaligned.groupby(['Error']):
                    last_fp=0
                    last_tp=0  
                    auc = 0
                    for threshold in outlier_threshold[measure_type_key]:
                        #Given an error type (e.g., rotation), an error parameter (e.g., degrees of rotation), a distance metric (e.g., mutual information ),
                        #that defines a set of misaligned PET images, if we take all of the normal (i.e., correctly aligned data) and pool it with the misaligned data
                        [tp, fp] = estimate_roc(test, normal, threshold)
                        temp=pd.DataFrame([[error_type_key, measure_type_key,metric_name, key, threshold, fp, tp]], columns=roc_columns)
                        roc_df=pd.concat([roc_df, temp])
                        dfp = fp - last_fp
                        dtp = (tp + last_tp)/2
                        last_fp = fp
                        last_tp = tp
                        auc += dfp * dtp
                    temp = pd.DataFrame( [[error_type_key, measure_type_key,metric_name, key, auc]], columns=auc_columns)
                    auc_df=pd.concat([auc_df, temp])
    return([roc_df,auc_df])


def estimate_roc(test, control, threshold, nRep=5000):
    n=int(test.shape[0])
    nTest=int(floor(n/2))
    nControl=n-nTest
    range_n=range(n)
    #TPlist=[]
    #FPlist=[]
    test.index=range_n
    control.index=range_n
    test_classify=pd.Series([ 1 if test.Value[i] < threshold else 0 for i in range_n ])
    control_classify=pd.Series([ 1 if control.Value[i] < threshold else 0 for i in range_n ])

    #for i in range(nRep):
    #    idx_inc=random.sample(range_n, nTest)
    #    idx_exc = [x for x in range_n if x not in idx_inc  ]
    #    X=test_classify[idx_inc] #With perfect classification, should all be 1
    #    Y=control_classify[idx_exc] #With perfect classification, should all be 0
    #    TP=sum(X) #True positives
    #    FP=sum(Y) #False positives
    #    TPlist.append(TP)
    #    FPlist.append(FP)
    #TPrate=np.mean(TP)/nTest
    #FPrate=np.mean(FP)/nControl
    t=sum(test_classify)
    tn=float(test.shape[0])
    f=sum(control_classify)
    fn=float(control.shape[0])
    TPrate=t/tn
    FPrate=f/fn

    return([TPrate, FPrate])
    
def calc_distance_metrics(df, subject, condition, misaligned, pet_images,t1_images, brain_masks, pet_brain_masks, distance_metrics):
    sub_df=pd.DataFrame(columns=df.columns)

    for pet_img, pet_mask in zip(misaligned, pet_brain_masks):
        #sub_misaligned=[ i for i in misaligned if subject in i and condition in i  ]
        #sub_misaligned_masks=[ i for i in pet_brain_masks if subject in i and condition in i ]
        path, ext = os.path.splitext(pet_img)
        base=basename(path)
        param=base.split('_')[-1]
        param_type=base.split('_')[-2]
        mis_metric=qc.distance(pet_img, t1_images, brain_masks, pet_mask, distance_metrics.values())
        for m,metric_name,metric_func in zip(mis_metric, distance_metrics.keys(), distance_metrics.values()):
            temp=pd.DataFrame([[subject,condition,param_type,param,metric_name,m]],columns=df.columns  ) 
            sub_df = pd.concat([sub_df, temp])
    df = pd.concat([df, sub_df])
    df.index=range(df.shape[0])
    return(df)
    

def calc_outlier_measures(df, outlier_measures, distance_metrics, normal_param):
    outlier_measure_names=outlier_measures.keys() #List of names of outlier measures
    outlier_measures_list=outlier_measures.values() #List of names of outlier measures
    metric_names=distance_metrics.keys() #List of names for distance metrics
    subjects=np.unique(df.Subject) #List of subjects
    unique_error_types=np.unique(df.ErrorType) #List of errors types in PET mis-alignmenta
    out_columns=['Subject','Condition','ErrorType','Error','Measure','Metric', 'Value'] 
    df_out = pd.DataFrame(columns=out_columns)
    for error_type, error_type_df in df.groupby(['ErrorType']):
        normal_df=error_type_df[  error_type_df.Error == normal_param  ]  #Get list of normal subjects for this error type
        #if error_type != 'offset': continue
        for error, error_df in error_type_df.groupby(['Error']):
            #if not error in ['0 0 0']: continue
            for sub, sub_df in error_df.groupby(['Subject']):
                #Remove the current subject from the data frame containing normal subjects
                temp_df=normal_df[ ~ (normal_df.Subject == sub) ]
                #if sub != 'P28': continue

                for cond, mis_df in sub_df.groupby(['Condition']):
                    #Create data frame of a single row for this subject, error type and error parameter
                    #Combine the data frame with normal PET images with that of the mis-aligned PET image
                    test_df=pd.concat([temp_df, mis_df])
                    for measure, measure_name in zip(outlier_measures_list, outlier_measure_names):
                        combined = test_df.pivot_table(rows=["Subject","Condition","ErrorType","Error"],cols=['Metric'],values="Value")
                        combined.reset_index(inplace=True)
                        r=measure(combined.loc[:,metric_names])
                        idx = combined[ combined.Subject == sub  ].index[0]
                        s= r[idx][0]
                        row_args = [sub,cond,error_type,error,measure_name,'All',s]
                        row=pd.DataFrame([row_args], columns=out_columns  )
                        df_out = pd.concat([df_out, row],axis=0)

                        for metric_name, metric_df in test_df.groupby(['Metric']):
                            #if metric_name != 'MI': continue
                            #Get column number of the current outlier measure
                            #Reindex the test_df from 0 to the number of rows it has
                            #Get the series with the calculate the distance measure for the current measurae
                            #print metric_df[ metric_df.Subject == "P28"  ]
                            metric_df.index = range(metric_df.shape[0])
                            r=measure(metric_df.Value.values)
                            idx = metric_df[ metric_df.Subject == sub  ].index[0]
                            s= r[idx][0]
                            #metric_df['KDE'] = r
                            #print metric_df.sort('Value')
                            #exit(0)
                            #print error,':', s
                            #plt.clf()
                            #plt.scatter(metric_df.Value.values, r)
                            #plt.savefig(metric_name+'_'+error+'.png')
                            row_args = [sub,cond,error_type,error,measure_name,metric_name,s]
                            row=pd.DataFrame([row_args], columns=out_columns  )
                            df_out = pd.concat([df_out, row],axis=0)
    return(df_out)


from matplotlib.lines import Line2D
def plot_outlier_measures(dfi, outlier_measures, out_fn, color=cm.spectral):
    file_list = []
    df = dfi.copy()
    f=lambda x: float(str(x).split(' ')[-1])#FIXME: Will only print last error term

    nMeasure=len(df.Measure.unique())
    df.Error = df.Error.apply(f)

    sub_cond=np.array([ str(a)+'_'+str(b) for a,b in  zip(df.Subject, df.Condition) ])
    sub_cond_unique = np.unique(sub_cond)
    nUnique=float(len(sub_cond_unique))
    #d = { key : color(value/float(nMetric)) for (value, key) in enumerate(distance_metrics.keys()) }
    ax_list=[]
    measures=outlier_measures.keys()
    nErrorType=len(np.unique(df.ErrorType))
    for metric, group in df.groupby(['Metric']): 
        plt.clf()
        fig=plt.figure(1)
        fig.suptitle('Outlier detection of misaligned PET images')
        n=1

        for key, group1 in group.groupby(['ErrorType']):
            for measure, group2 in group1.groupby(['Measure']): 
                ax=plt.subplot(nErrorType, nMeasure, n)
                #ax.set_title('Outlier detection based on '+measure)
                ax.set_ylabel(measure)
                ax.set_xlabel('Error in '+key)

                y=group2.groupby(['Error']).Value.mean()
                #ax.plot(y.index, y, c=d[metric], label=metric)
                ax.plot(y.index, y)


            ax.legend(loc="best", fontsize=7)
            n+=1

        temp_fn = os.path.splitext(out_fn)
        temp_out_fn = temp_fn[0] + '_' + metric + temp_fn[1]
        print 'saving outlier plot to', out_fn
        file_list += temp_out_fn
        plt.savefig(temp_out_fn,width=1000*nMeasure, dpi=1000)
    return(file_list)

def plot_distance_metrics(dfi,distance_metrics, out_fn, color=cm.spectral):
    df=dfi.copy()
    f=lambda x: float(str(x).split(' ')[-1]) #FIXME: Will only print last error term
    nMetric=len(df.Metric.unique())
    df.Error = df.Error.apply(f)
    files_list = []
    sub_cond=np.array([ str(a)+'_'+str(b) for a,b in  zip(df.Subject, df.Condition) ])
    sub_cond_unique = np.unique(sub_cond)
    nUnique=float(len(sub_cond_unique))


    d = { key : color(value/float(len(sub_cond_unique))) for (value, key) in enumerate(sub_cond_unique) }

    ax_list=[]
    nErrorType=len(np.unique(df.ErrorType))
    nn = int(ceil(sqrt( nMetric  )))
    for key, group in df.groupby(['ErrorType']):
        for metric, group2 in group.groupby(['Metric']): 
            plt.clf()
            fig=plt.figure(1)
            n=1
            plt.ylabel(metric)
            plt.xlabel('Error in '+key)
            for sub_cond_key, group3 in group2.groupby(['Subject','Condition']): 
                sub_cond = str(sub_cond_key[0]) + '_' + str(sub_cond_key[1])
                plt.plot(group3.Error, group3.Value, c=d[sub_cond], label=sub_cond)
                #ax.legend(loc="best", fontsize=7)
            n+=1
            #plt.show()
            out2_fn=sub('.png','_'+key+'_'+metric+'.png', out_fn)
            print 'saving outlier plot to', out2_fn
            #plt.tight_layout()
            print out2_fn
            files_list += out2_fn
            plt.savefig(out2_fn,width=1000, dpi=500)
    return(files_list)



class myIdentOutput(TraitedSpec):
    out_file = traits.Str(desc="Output file")

class myIdentInput(BaseInterfaceInputSpec):
    param = traits.Str( mandatory=True, desc="Input list of translated PET images")
    param_type = traits.Str(mandatory=True, desc="Type of misalignment parameter (e.g., angle, offset)")
    in_file = traits.File(mandatory=True, exists=True, desc="Input file")
    out_file = traits.File(desc="Output image")

class myIdent(BaseInterface):
    input_spec = myIdentInput 
    output_spec =myIdentOutput 
   
    def _run_interface(self, runtime):
        ###############################################################
        # Need to create lists of misaligned PET images to pass to QC #
        ###############################################################
        in_file = self.inputs.in_file
        param = self.inputs.param
        param_type=self.inputs.param_type

        path, ext = os.path.splitext(in_file)
        base=basename(path)
        self.inputs.out_file = os.getcwd() + os.sep + base + '_'+ param_type + '_' + param +  ext
        shutil.copy(in_file, self.inputs.out_file) 

        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


class joinListOutput(TraitedSpec):
    out_list = traits.List(desc="Output file")

class joinListInput(BaseInterfaceInputSpec):
    in_list = traits.List(mandatory=True, exists=True, desc="Input list")
    out_list = traits.List(desc="Output list")

class joinList(BaseInterface):
    input_spec = myIdentInput 
    output_spec =myIdentOutput 
   
    def _run_interface(self, runtime):
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_list"] = self.inputs.in_list
        return outputs

class concat_dfOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class concat_dfInput(BaseInterfaceInputSpec):
    in_list = traits.List(mandatory=True, exists=True, desc="Input list")
    out_file = traits.File(mandatory=True, desc="Output file")

class concat_df(BaseInterface):
    input_spec =  concat_dfInput 
    output_spec = concat_dfOutput 
   
    def _run_interface(self, runtime):
        df=pd.DataFrame([])
        for f in self.inputs.in_list:
            dft = pd.read_csv(f)
            df = pd.concat([df, dft], axis=0)
        df.to_csv(self.inputs.out_file, index=False)
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.getcwd() + os.sep + self.inputs.out_file
        return outputs
      


