import nipype
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,  BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import pyminc.volumes.factory as pyminc
import matplotlib as mpl
from scipy.integrate import simps
mpl.use('Agg')
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
import numpy as np
import pandas as pd
import fnmatch
import os
import shutil
from scipy import stats
from math import sqrt, floor, ceil
from os import getcwd
from os.path import basename
from sys import argv, exit
from re import sub
from Quality_Control.outlier import lof, kde, MAD, lcf
from Quality_Control.qc import outlier_measures, distance_metrics, metric_columns
import Quality_Control as qc
import Extra.resample as rsl
import random
import seaborn as sns
import nipype.interfaces.io as nio
from Extra.concat import concat_df


# Name: group_coreg_qc_test
# Purpose: Test the ability of group_coreg_qc to detect misregistration of T1 and PET images. This is done by
#          creating misregistered PET images for each subject by applying translations and rotations to the PET
#          image. For each misregistered PET image, we run group_coreg_qc to see how much the misregistration 
#          affects group qc metrics.


global normal_param
global angles
global offsets
global errors
angles=[ [('angle', '0 0 0')], [('angle', '0 0 2')],[('angle', '0 0 4')],[('angle', '0 0 6')],[('angle', '0 0 12')],[('angle', '0 0 18') ]] #X,Y,Z angle of rotation
offsets=[[("offset",'0 0 0')], [("offset",'2 0 0')], [("offset",'4 0 0')], [("offset",'6 0 0')], [("offset",'12 0 0')], [("offset",'18 0 0')] ] #X,Y,Z offset of translation (in mm)
errors = angles + offsets
#errors = [ [('angle', '0 0 0')] ]
misalignment_parameters={"angles":angles, "offsets":offsets}

normal_param ='000'
def get_misalign_pet_workflow(name, opts):
    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    #FIXME: Should have angles and offsets defined by user. Use ';' to seperate elements
    #angles=['0 0 0', '0 0 2', '0 0 4', '0 0 8', '0 0 12', '0 0 16', '0 0 20'] #X,Y,Z angle of rotation
    #offsets=['0 0 0', '0 0 2', '0 0 4', '0 0 8', '0 0 12', '0 0 14' ] #X,Y,Z offset of translation (in mm)
    
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
        misaligned=rotated_pet + translated_pet 
        
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
        df=calc_outlier_measures(df, outlier_measures, normal_param)
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
        normal_param = self.inputs.normal_param
        df=pd.read_csv(self.inputs.in_file)
        self.inputs.out_file = self._gen_output()
        self.inputs.auc_file = self._gen_output("test_group_qc_auc.csv")
        [ roc_df, auc_df ]=outlier_measure_roc(df, normal_param)
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
class plot_metricsOutput(TraitedSpec):
    out_files = traits.List(desc="Output file")

class plot_metricsInput(BaseInterfaceInputSpec):
    out_files = traits.List(desc="Output file")
    in_file = traits.File(exists=True, mandatory=True,desc="Input file")

class plot_metricsCommand(BaseInterface):
    input_spec = plot_metricsInput 
    output_spec= plot_metricsOutput
  
    def _gen_output(self, fname = 'metrics.png'):
        dname = os.getcwd() 
        return dname+ os.sep+fname

    def _run_interface(self, runtime):
        df=pd.read_csv(self.inputs.in_file)
        out_file  = self._gen_output()
        self.inputs.out_files =  plot_metrics(df,  out_file, color=cm.spectral)
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
    error_type_unit=traits.Dict(desc="error units")
    error_type_name=traits.Dict(desc="error type")
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
### FUNCTIONS
def plot_roc(dfi, df_auc, error_type_unit, error_type_name, color=cm.spectral, DPI=500):
    
    df = dfi.copy()
    figs=[]
    fn_list=[]
    nmeasure=len(np.unique(df.measure))
    f=lambda x: float( str(x).split('.')[-1] )
    df.error = df.error.apply(f)
    nerrortype = len(np.unique(df.errortype) )
    for names, df0 in df.groupby(['errortype','roi']):
        label_name=names[0]
        roi_name=names[1]
        g = sns.FacetGrid(df0, col="measure", row="metric", despine=True, legend_out=True, hue="error")
        g = g.map(plt.plot, "FalsePositive", "TruePositive", alpha=0.75).add_legend()
        fn=os.getcwd()+os.sep + label_name+'_'+ str(roi_name) +'_roc.png'
        #print "Saving ROC plot to", fn
        plt.savefig(fn, width=2000*len(df0.measure.unique()) , dpi=DPI)
        fn_list += fn
    
    for names, df0 in df_auc.groupby(['errortype','roi']):
        label_name=names[0]
        roi_name=names[1]
        df0.sort_values(by=["errortype", "measure", "metric", "error"], inplace=True)
        plt.clf()
        fig=plt.figure()       
        g = sns.FacetGrid(df0, sharex=False, legend_out=True,  despine=True, margin_titles=True, col="measure", row="errortype", hue="metric")
        g = g.map(plt.plot, "error", "AUC", alpha=0.75).add_legend()
        fn=os.getcwd()+os.sep +'auc_'+str(roi_name)+'.png'
        plt.savefig(fn, width=1000*len(df0.measure.unique()), dpi=DPI)
        fn_list += fn
        #print "Saving AUC plot to", fn
    return(fn_list)


def outlier_measure_roc(df, normal_error):
    subjects=np.unique(df['sub'])
    roc_columns=['errortype', 'measure','metric', 'roi', 'error' ]
    auc_columns=['errortype', 'measure','metric', 'roi', 'error', 'AUC' ]
    roc_df=pd.DataFrame(columns=roc_columns )
    auc_df=pd.DataFrame(columns=auc_columns )

    for metric_name, metric in df.groupby(['metric']):
        for error_type_key, error_type in metric.groupby(['errortype']):
            for measure_type_key, measure_type in error_type.groupby(['measure']):
                for region_type_key, region_type in measure_type.groupby(['roi']):
                    normal=region_type[region_type.error.astype(float) == float(normal_error)]
                    misaligned=region_type[ ~(region_type.error.astype(type(normal_error)) == normal_error) ]
                    for error, test in misaligned.groupby(['error']):
                        y_true = np.concatenate([np.repeat(1,normal.shape[0]), np.repeat(0,test.shape[0])])
                        y_score = np.concatenate([normal.value, test.value])
                        fp, tp, thr = roc_curve(y_true, y_score)
                        n=fp.shape[0]
                        temp=pd.DataFrame([ [error_type_key]*n, [measure_type_key]*n,[metric_name]*n, [region_type_key]*n, [error]*n]).T
                        temp.columns=roc_columns
                        temp["FalsePositive"] = fp
                        temp["TruePositive"] = tp
                        roc_df=pd.concat([roc_df, temp])
                        roc_auc = auc(fp, tp)
                        temp = pd.DataFrame( [[error_type_key, measure_type_key,metric_name, region_type_key, error, roc_auc]], columns=auc_columns)
                        auc_df=pd.concat([auc_df, temp])
    return([roc_df,auc_df])


    
def calc_distance_metrics(df, subject, condition, misaligned, pet_images,t1_images, brain_masks, pet_brain_masks, distance_metrics):
    sub_df=pd.DataFrame(columns=df.columns)

    for pet_img, pet_mask in zip(misaligned, pet_brain_masks):
        path, ext = os.path.splitext(pet_img)
        base=basename(path)
        param=base.split('.')[-1]
        param_type=base.split('.')[-2]

        mis_metric=qc.distance(pet_img, t1_images, brain_masks, pet_mask, distance_metrics.values())
        for m,metric_name,metric_func in zip(mis_metric, distance_metrics.keys(), distance_metrics.values()):
            temp=pd.DataFrame([[subject,condition,param_type,param,metric_name,m]],columns=df.columns) 
            sub_df = pd.concat([sub_df, temp])
    df = pd.concat([df, sub_df])
    df.index=range(df.shape[0])
    return(df)
    

def calc_outlier_measures(df, outlier_measures, normal_param):
    df.reset_index(drop=True)
    outlier_measure_names=outlier_measures.keys() #List of names of outlier measures
    outlier_measures_list=outlier_measures.values() #List of names of outlier measures
    metric_names=df.metric.unique() #distance_metrics.keys() #List of names for distance metrics
    subjects=np.unique(df['sub']) #List of subjects
    unique_error_types=np.unique(df.errortype) #List of errors types in PET mis-alignmenta
    out_columns=['sub','task','ses','errortype','error','roi','measure','metric', 'value'] 
    df_out = pd.DataFrame(columns=out_columns)
    error_data_type = df.error.dtype
    cast_normal = np.cast[error_data_type](normal_param)
    for error_type, error_type_df in df.groupby(['errortype']):
        idx = [ True if f == cast_normal else False for f in error_type_df.error]
        normal_df=error_type_df[ idx  ]  #Get list of normal subjects for this error type
        for error, error_df in error_type_df.groupby(['error']):
            for roi, roi_df in error_df.groupby(['roi']):
                for sub, sub_df in roi_df.groupby(['sub']):
                    #Remove the current subject from the data frame containing normal subjects
                    temp_df=normal_df[ normal_df['sub'] != sub  ]
                    for cond, mis_df in sub_df.groupby(['task','ses']):
                        #Create data frame of a single row for this subject, error type and error parameter
                        #Combine the data frame with normal PET images with that of the mis-aligned PET image
                        test_df=pd.concat([temp_df, mis_df])
                        for measure, measure_name in zip(outlier_measures_list, outlier_measure_names):
                            combined = test_df.pivot_table(index=["sub","task","ses","errortype","error"],columns=['metric'],values="value")
                            combined.reset_index(inplace=True)
                            if len(metric_names) > 1 : #if more than one metric, calculate outlier measure for all metrics combined
                                #Distance measure is calculated using all metrics
                                metricvalues=combined.loc[:,metric_names]
                                if len(metricvalues.shape) == 1 : metricvalues = metricvalues.reshape(-1,1)
                                r=measure(metricvalues)
                                if len(r.shape) > 1 : r = r.flatten()
                                idx = combined.loc[ combined["sub"].values == sub ].index[0]
                                s= r[idx] #[0] #Outerlier measure for subject "idx"
                                row_args = [sub]+list(cond)+[error_type,error,roi,measure_name,'All',s]
                                #Add row for outlier measure calculated with all metrics
                                row=pd.DataFrame([row_args], columns=out_columns  )
                                df_out = pd.concat([df_out, row],axis=0)
                            for metric_name, metric_df in test_df.groupby(['metric']):
                                #Get column number of the current outlier measure
                                #Reindex the test_df from 0 to the number of rows it has
                                #Get the series with the calculate the distance measure for the current measure
                                metric_df.index = range(metric_df.shape[0])
                                metricvalues=metric_df.value.values
                                if len(metricvalues.shape) == 1 : metricvalues = metricvalues.reshape(-1,1)
                                cdf=False
                                if 'coreg' or 'pvc' in metric_df.analysis: cdf=True
                                r=measure(metricvalues, cdf)
                                if len(r.shape) > 1 : r = r.flatten()
                                idx = metric_df[ metric_df['sub'].values == sub  ].index[0]
                                s= r[idx]
                                row_args = [sub]+list(cond)+[error_type,error,roi,measure_name,metric_name,s]
                                row=pd.DataFrame([row_args], columns=out_columns  )
                                df_out = pd.concat([df_out, row],axis=0)
    #print(df_out)
    return(df_out)


from matplotlib.lines import Line2D
def plot_outlier_measures(dfi, outlier_measures, out_fn, color=cm.spectral):
    dfi["sub"]=dfi["sub"].map(str)+"-"+dfi["task"].map(str)+"-"+dfi["ses"].map(str) 
    file_list = []
    df = dfi.copy()
    #f = lambda x: float(str(x).split('.')[-1]) 
	#FIXME: Will only print last error term
    #f=lambda x: float(''.join([ i for i in x if i.isdigit() ]))
    f=lambda x : float(x) / 100 
    nmeasure=len(df.measure.unique())
    nmetric=len(df.measure.unique())
    df.error = df.error.apply(f)
    ndim = int(ceil(np.sqrt(nmeasure)))
    sub_cond=np.array([ str(a)+'_'+str(b)+'_'+str(c) for a,b,c in  zip(df['sub'], df.task, df.ses) ])
    sub_cond_unique = np.unique(sub_cond)
    nUnique=float(len(sub_cond_unique))
    measures=outlier_measures.keys()
    
    for key, group1 in df.groupby(['errortype','roi']):
        errortype=key[0]
        roi=key[1]
        plt.clf()
        fig=plt.figure(1)
        fig.suptitle('Outlier detection of misaligned PET images')
        n=1
        for metric, group2 in group1.groupby(['metric']): 
            for measure, group3 in group2.groupby(['measure']) :
                x=group3.value
                den=1
                if np.min(x) != np.max(x) : den = np.max(x) - np.min(x)
                x_norm = (x-np.min(x))/den
                group1.value.loc[(group1.measure == measure) & (group1.metric == metric)]= x_norm
        ax=plt.subplot(ndim, ndim, n)
        g = sns.FacetGrid(group1, sharex=False, sharey=False, legend_out=True,  despine=True, margin_titles=True, col="metric", row="errortype", hue="sub")
        xmax=group1["error"].max()
        sns.set(font_scale=1)
        g = g.map(plt.plot, "error", "value", alpha=0.5)#.add_legend()
        g = g.map(plt.scatter, "error", "value", alpha=0.5).add_legend()
        plt.ylabel('')
        plt.xlabel('')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.ylim([-0.001,1.001])
        plt.xlim([-0.001,xmax])
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper right", ncol=1, prop={'size': 6})

        ax.legend(loc="best", fontsize=7)
        n+=1
        temp_fn = os.path.splitext(out_fn)
        temp_out_fn = temp_fn[0] + '_' + errortype +'_'+ str(roi) + temp_fn[1]
        print 'saving outlier plot to', temp_out_fn
        file_list += temp_out_fn
        plt.savefig(temp_out_fn,width=2000*ndim, dpi=500)
    return(file_list)

def plot_metrics(dfi, out_fn, color=cm.spectral):
    #f=lambda x: float(''.join([ i for i in x if i.isdigit() ]))
    
    dfi["sub"]=dfi["sub"].map(str)+"-"+dfi["task"].map(str)+"-"+dfi["ses"].map(str) 
    f=lambda x: float( str(x).split('.')[-1] )
    dfi.error = dfi.error.apply(f)
    dfi = dfi.sort_values(by=["errortype", "error"])
    
    for roi, df0 in dfi.groupby(["roi"]):
        plt.clf()
        plt.figure()
        g = sns.FacetGrid(dfi, sharex=False, sharey=False, legend_out=True,  despine=True, margin_titles=True, col="metric", row="errortype", hue="sub")
        sns.set(font_scale=1)
        g = g.map(plt.plot, "error", "value", alpha=0.5)#.add_legend()
        g = g.map(plt.scatter, "error", "value", alpha=0.5).add_legend()
        out_split = os.path.splitext(out_fn)
        out_fn = out_split[0] + '_'+str(roi)+out_split[1]
        plt.savefig(out_fn, width=1000*len(dfi.metric.unique()), dpi=500)
    return([out_fn])


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

def runningIntegrate(tac, times):
    mean_int=[]
    for i in range(1,1+len(times)) :
        mean_int.append(simps(tac[0:i], times[0:i]))
    return mean_int

def logan(ref_tac, ref_int, roi_tac, roi_int):
    y = np.array(roi_int) / np.array(roi_tac )
    x = np.array(ref_int) / np.array(roi_tac)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x,y)
    return slope - 1
from math import isnan
def tkametric(ref_tac, ref_int, roi_tac, roi_int, times):
    x=np.array(ref_int)
    y=np.array(roi_int)
    den = np.sum(x**2)
    num = np.sum(x*y)
    m2=num/den
    #m1=1/np.exp(np.sum(x-y)**2)
    #if isnan(m1) or isnan(m2) : print m1, m2

    return m2 #, m2

def write_dft(header, tac, name, fn):
    try : 
        #end_times = [ float(h) for h in  header['time']["frames-time"] ]
        end_times = [ float(e) for s,e in  header['Time']["FrameTimes"]["Values"] ]
    except ValueError :
        end_times = [1.]
    start_times = [0] + end_times 
    start_times.remove(start_times[-1])

    with open(fn, 'w+') as f:
        f.write("DFT\t\t"+name+"\n")
        f.write("TAC\tstudy\n")
        f.write("kBq/mL\tp118\n")
        f.write("Times (min)\t1\n")
        for s,e,t in zip(start_times, end_times, tac):
            f.write("%3.1f\t%3.1f\t%3.3f\n" % (s,e,t))
    return start_times, end_times

class tka_refContaminateOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class tka_refContaminateInput(BaseInterfaceInputSpec):
    pet_4d = traits.File(mandatory=True, exists=True, desc="Input 4D PET")
    reference_vol = traits.File(mandatory=True, exists=True, desc="Reference region volume")
    results_vol = traits.File(mandatory=True, exists=True, desc="Results volume")
    header = traits.Dict(mandatory=True, desc="Dictionary of header info")
    sid= traits.Str(mandatory=True, desc="sub ID")
    cid= traits.Str(mandatory=True, desc="task,ses ID")
    out_file = traits.File(desc="Output file")

class tka_refContaminate(BaseInterface):
    input_spec = tka_refContaminateInput 
    output_spec = tka_refContaminateOutput 
  
    def _gen_output(self):
        return os.getcwd() + os.sep + "sid-"+self.inputs.sid +"_cid-"+self.inputs.cid+"_referenceContamination.csv"

    def _run_interface(self, runtime):
        out_columns=['sub','task','ses','errortype','error','metric', 'value'] 
        df_out = pd.DataFrame([],columns=out_columns)
        sid=self.inputs.sid
        cid=self.inputs.cid
        pet = pyminc.volumeFromFile(self.inputs.pet_4d)
        ref = pyminc.volumeFromFile(self.inputs.reference_vol)
        roi = pyminc.volumeFromFile(self.inputs.results_vol)
        roi_vol = roi.data
        idx= (roi.data > 1.9) & (roi.data <2.1)
        roi.data[idx]=1
        roi.data[~idx]=0
        ref_tac=[]
        roi_tac=[]

        nref=np.sum(ref.data)
        nroi=np.sum(roi.data)
        for i in range(pet.data.shape[0]): 
            ref_tac.append(np.sum(np.array(pet.data[i,:]) * np.array(ref.data)) / nref )
        for i in range(pet.data.shape[0]): 
            roi_tac.append(np.sum(np.array(pet.data[i]) * np.array(roi_vol)) / nroi )

        roi_fn=os.getcwd()+os.sep+"roi_temp.dft"
        start_times, end_times = write_dft(self.inputs.header, roi_tac, "roi", roi_fn)
        roi_int = runningIntegrate(roi_tac, end_times)
        
        contamination_error_levels = [0., 0.25, 0.5, 0.75, 1]
        for i in contamination_error_levels : 
            fake_tac = i*np.array(roi_tac) + (1.-i) * np.array(ref_tac)
            fake_fn=os.getcwd()+os.sep+"fake_temp"+str(i)+".dft"
            ref_int = runningIntegrate(fake_tac, end_times)
            bp = logan(fake_tac, ref_int, roi_tac, roi_int)
            m2  = tkametric(fake_tac,ref_int, roi_tac, roi_int, end_times)
            temp0=pd.DataFrame([ [sid, cid,'RefMixture',i,'bp', bp ],[sid, cid,'RefMixture',i,'m2', m2 ]   ], columns=out_columns)
            df_out = pd.concat([df_out, temp0])

        if not isdefined(self.inputs.out_file) : 
            self.inputs.out_file=self._gen_output() 
        print "TKA Contamination:",self.inputs.out_file
        df_out.to_csv(self.inputs.out_file)
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

#
# Workflow for testing coregistration auto-qc
#
def test_group_qc_scanLevel(name, opts):
    ###
    ### Nodes are at subject level (not joined yet)
    ###
    workflow = pe.Workflow(name=name)
    inputnode = pe.Node(niu.IdentityInterface(fields=['petmri_img', 'header', 'pet_4d', 'reference_vol', 'results_vol', 'brainmask_t1', 'cid', 'sid', 't1']), name='inputnode')
    #Define empty node for output

    wf_misalign_pet = get_misalign_pet_workflow("misalign_pet", opts)
    workflow.connect(inputnode, 'petmri_img', wf_misalign_pet, 'inputnode.pet')
    workflow.connect(inputnode, 'brainmask_t1', wf_misalign_pet, 'inputnode.brainmask')
    workflow.connect(inputnode, 'cid', wf_misalign_pet, 'inputnode.cid')
    workflow.connect(inputnode, 'sid', wf_misalign_pet, 'inputnode.sid')
    
    #calculate distance metric node
    distance_metricsNode=pe.Node(interface=distance_metricCommand(),name="test_distance_metrics")
    colnames=["sub", "task","ses", "errortype", "error", "metric", "value"] 
    distance_metricsNode.inputs.colnames = colnames
    distance_metricsNode.inputs.clobber = False 

    #TKA QC (with Logan Plot)
    tkaQCNode = pe.Node(interface=tka_refContaminate(),name="test_tka_contaminate")
    workflow.connect(inputnode, 'pet_4d', tkaQCNode, 'pet_4d')
    workflow.connect(inputnode, 'reference_vol', tkaQCNode, 'reference_vol')
    workflow.connect(inputnode, 'results_vol', tkaQCNode, 'results_vol')
    workflow.connect(inputnode, 'header', tkaQCNode, 'header')
    workflow.connect(inputnode, 'sid', tkaQCNode, 'sid')
    workflow.connect(inputnode, 'cid', tkaQCNode, 'cid')
 
    workflow.connect(wf_misalign_pet,'outputnode.rotated_pet',distance_metricsNode, 'rotated_pet')
    workflow.connect(wf_misalign_pet,'outputnode.translated_pet',distance_metricsNode, 'translated_pet')
    workflow.connect(wf_misalign_pet,'outputnode.rotated_brainmask',distance_metricsNode, 'rotated_brainmask')
    workflow.connect(wf_misalign_pet,'outputnode.translated_brainmask',distance_metricsNode, 'translated_brainmask')
    workflow.connect(inputnode, 't1', distance_metricsNode, 't1_images')
    workflow.connect(inputnode, 'petmri_img', distance_metricsNode, 'pet_images')
    workflow.connect(inputnode, 'brainmask_t1', distance_metricsNode, 'brain_masks')
    workflow.connect(inputnode, 'cid', distance_metricsNode, 'conditions')
    workflow.connect(inputnode, 'sid', distance_metricsNode, 'subjects')
    return workflow

def test_group_qc_groupLevel(opts, args):
    workflow = pe.Workflow(name='groupLevelQC')
    workflow.base_dir = opts.targetDir

    #Datasink
    datasink=pe.Node(interface=nio.DataSink(), name="output")
    datasink.inputs.base_directory= opts.targetDir +os.sep  +"test_qc"
    datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]
    #Datagrabber
    outfields=['coreg_metrics', 'pvc_metrics', 'tka_metrics']
    #paths={'coreg_metrics':"scanLevelQC/*/test_distance_metrics/*test_group_qc_metric.csv",
    #        'pvc_metrics':"scanLevelQC/*/test_tka_contaminate/*_referenceContamination.csv"} 
    #preproc/_args_task01.ses01.sidD02/_angle_002/
    paths={'coreg_metrics': '_args_*/*/coreg_qc_metrics/*metric.csv', 
            'tka_metrics':'_args_*/*/results_tka/*_3d.csv',
            'pvc_metrics':'_args_*/*/pvc_qc_metrics/*_metric.csv'}
    datasource = pe.Node( interface=nio.DataGrabber( outfields=outfields, raise_on_empty=True, sort_filelist=False), name="datasource")
    datasource.inputs.base_directory = opts.targetDir + os.sep +opts.preproc_dir
    datasource.inputs.template = '*'
    datasource.inputs.field_template = paths
    
    error_type_unit={"angle":"(degrees)",  "offset":'(mm)'} 
    error_type_name={"angle":'rotation',  "offset":'translation'} 

    ######################
    ### Coregistration ###
    ######################
    concat_dist_metricsNode=pe.Node(interface=concat_df(), name="concat_coreg_metrics")
    concat_dist_metricsNode.inputs.test = True
    concat_dist_metricsNode.inputs.out_file="coreg_qc_distance_metrics.csv"
    workflow.connect(datasource, 'coreg_metrics', concat_dist_metricsNode, 'in_list')

    ### Test group qc for coregistration using misaligned images 
    colnames=metric_columns  + ['error','errortype']
    
    plot_distance_metricsNode=pe.Node(plot_metricsCommand(),name="coreg_plot_metrics")
    workflow.connect(concat_dist_metricsNode,'out_file',plot_distance_metricsNode, 'in_file')
    
    #calculate outlier measures node
    outlier_measuresNode=pe.Node(interface=outlier_measuresCommand(), name="coreg_outlier_measures")
    workflow.connect(concat_dist_metricsNode, 'out_file', outlier_measuresNode, 'in_file')
    outlier_measuresNode.inputs.normal_param =  "0" #normal_param
    
    #plot outlier measures node
    plot_outlier_measuresNode=pe.Node(plot_outlier_measuresCommand(), name="coreg_plot_outlier_measures")
    workflow.connect(outlier_measuresNode, 'out_file', plot_outlier_measuresNode, 'in_file')

    #calculate ROC for outlier measures
    rocNode=pe.Node(outlier_measures_rocCommand(), name="coreg_roc")
    rocNode.inputs.normal_param = '0' #normal_param
    workflow.connect(outlier_measuresNode, 'out_file', rocNode, 'in_file')

    #plot roc node
    plot_rocNode=pe.Node(plot_rocCommand(), name="coreg_plot_roc")
    plot_rocNode.inputs.error_type_unit = error_type_unit
    plot_rocNode.inputs.error_type_name = error_type_name
    workflow.connect(rocNode, 'out_file', plot_rocNode, 'in_file')
    workflow.connect(rocNode, 'auc_file', plot_rocNode, 'auc_file')
    workflow.connect(outlier_measuresNode, 'out_file', datasink, 'outlier_measures_df')
    workflow.connect(rocNode, 'out_file', datasink, 'roc_df')
    #FIXME Following 3 nodes all have lists as outputs. These seem to cause a problem when being passed to datasink
    #workflow.connect(plot_distance_metricsNode, 'out_files', datasink, 'distance_metrics_plot')
    #workflow.connect(plot_outlier_measuresNode, 'out_files', datasink, 'outlier_measures_plot')
    #workflow.connect(plot_rocNode, 'out_files', datasink, 'outlier_measures_roc_plot')
    #################################
    ### Partial Volume Correction ###
    #################################
    if not opts.pvc_method == None: 
        concat_pvc_metricsNode=pe.Node(interface=concat_df(), name="pvc_concat_metrics")
        concat_pvc_metricsNode.inputs.test = True
        concat_pvc_metricsNode.inputs.out_file="coreg_qc_pvc.csv"
        workflow.connect(datasource, 'pvc_metrics', concat_pvc_metricsNode, 'in_list')

        plot_pvc_metricsNode=pe.Node(plot_metricsCommand(), name="pvc_plot_metrics")
        workflow.connect(concat_pvc_metricsNode, 'out_file', plot_pvc_metricsNode, 'in_file')
        
        #calculate outlier measures node
        outlier_measures_pvcNode=pe.Node(interface=outlier_measuresCommand(), name="pvc_outlier_measures")
        workflow.connect(concat_pvc_metricsNode, 'out_file', outlier_measures_pvcNode, 'in_file')
        outlier_measures_pvcNode.inputs.normal_param = '0'
        
        #plot outlier measures node
        plot_outlier_measures_pvcNode=pe.Node(plot_outlier_measuresCommand(), name="pvc_plot_outlier_measures")
        workflow.connect(outlier_measures_pvcNode, 'out_file', plot_outlier_measures_pvcNode, 'in_file')

        #calculate ROC for outlier measures
        roc_pvcNode=pe.Node(outlier_measures_rocCommand(), name="pvc_roc")
        roc_pvcNode.inputs.normal_param = '0'
        workflow.connect(outlier_measures_pvcNode, 'out_file', roc_pvcNode, 'in_file')

        #plot roc_pvc node
        plot_roc_pvcNode=pe.Node(plot_rocCommand(), name="pvc_plot_roc")
        plot_roc_pvcNode.inputs.error_type_unit = error_type_unit
        plot_roc_pvcNode.inputs.error_type_name = error_type_name
        workflow.connect(roc_pvcNode, 'out_file', plot_roc_pvcNode, 'in_file')
        workflow.connect(roc_pvcNode, 'auc_file', plot_roc_pvcNode, 'auc_file')

        workflow.connect(outlier_measures_pvcNode, 'out_file', datasink, 'outlier_measures_pvc_df')
        workflow.connect(roc_pvcNode, 'out_file', datasink, 'pvc_roc_df')
    ###############################
    ### Tracer Kinetic Analysis ###
    ###############################
    if not opts.tka_method == None: 
        concat_tka_metricsNode=pe.Node(interface=concat_df(), name="tka_concat_metrics")
        concat_tka_metricsNode.inputs.out_file="tka_qc_metrics.csv"
    
        concat_tka_metricsNode.inputs.test = True
        workflow.connect(datasource, 'tka_metrics', concat_tka_metricsNode, 'in_list')

        plot_tka_metricsNode=pe.Node(plot_metricsCommand(), name="tka_plot_metrics")
        workflow.connect(concat_tka_metricsNode, 'out_file', plot_tka_metricsNode, 'in_file')
        
        #calculate outlier measures node
        outlier_measures_tkaNode=pe.Node(interface=outlier_measuresCommand(), name="tka_outlier_measures")
        workflow.connect(concat_tka_metricsNode, 'out_file', outlier_measures_tkaNode, 'in_file')
        outlier_measures_tkaNode.inputs.normal_param = '0'
        
        #plot outlier measures node
        plot_outlier_measures_tkaNode=pe.Node(plot_outlier_measuresCommand(), name="tka_plot_outlier_measures")
        workflow.connect(outlier_measures_tkaNode, 'out_file', plot_outlier_measures_tkaNode, 'in_file')

        #calculate ROC for outlier measures
        roc_tkaNode=pe.Node(outlier_measures_rocCommand(), name="tka_roc")
        roc_tkaNode.inputs.normal_param = '0'
        workflow.connect(outlier_measures_tkaNode, 'out_file', roc_tkaNode, 'in_file')

        #plot roc_tka node
        plot_roc_tkaNode=pe.Node(plot_rocCommand(), name="tka_plot_roc")
        plot_roc_tkaNode.inputs.error_type_unit = error_type_unit
        plot_roc_tkaNode.inputs.error_type_name = error_type_name
        workflow.connect(roc_tkaNode, 'out_file', plot_roc_tkaNode, 'in_file')
        workflow.connect(roc_tkaNode, 'auc_file', plot_roc_tkaNode, 'auc_file')

        workflow.connect(outlier_measures_tkaNode, 'out_file', datasink, 'outlier_measures_tka_df')
        workflow.connect(roc_tkaNode, 'out_file', datasink, 'tka_roc_df')


    workflow.run()
    return workflow
