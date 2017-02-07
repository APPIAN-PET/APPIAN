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
from math import sqrt, floor
from os import getcwd
from os.path import basename
from sys import argv, exit
from re import sub
import nipype.interfaces.minc.resample as rsl
import Quality_Control as qc
import random



# Name: group_coreg_qc_test
# Purpose: Test the ability of group_coreg_qc to detect misregistration of T1 and PET images. This is done by
#          creating misregistered PET images for each subject by applying translations and rotations to the PET
#          image. For each misregistered PET image, we run group_coreg_qc to see how much the misregistration 
#          affects group qc metrics.


def get_misalign_pet_workflow(name, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow

    #FIXME: Should have angles and offsets defined by user. Use ';' to seperate elements
    angles=['0,0,0', '0,0,2', '0,0,4', '0,0,8', '0,0,16', '0,0,32', '0,0,64'] #X,Y,Z angle of rotation
    offsets=['0,0,0', '0,0,2', '0,0,4', '0,0,8', '0,0,10', '0,0,12', '0,0,14' ] #X,Y,Z offset of translation (in mm)
    inputnode=pe.Node(interface=niu.IdentityInterface(fields=['pet', 'sid', 'cid', 'study_prefix']), name='inputnode')
    outputnode=pe.Node(interface=niu.IdentityInterface(fields=['translated_pet', 'rotated_pet']), name='outputnode')
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
    ###Join the rotation nodes back together
    join_rotationsNode = pe.JoinNode(interface=niu.IdentityInterface(fields=["angle"]), joinsource="angle_splitNode", joinfield=["angle"], name="join_rotationsNode")
    join_rotationsNode.inputs.angle=[]
    workflow.connect(rrotate_resampleNode, 'out_file', join_rotationsNode, 'angle')
    ###Send rotated pet images to output node 
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
    #workflow.connect(offset_concatNode, 'param', rtranslate_resampleNode, 'offset')
    ###Join the translations nodes back together
    join_translateNode = pe.JoinNode(interface=niu.IdentityInterface(fields=["offset"]), joinsource="offset_splitNode", joinfield=["offset"], name="join_translateNode")
    join_translateNode.inputs.offset=[]
    workflow.connect(rtranslate_resampleNode, 'out_file', join_translateNode, 'offset')
    ###Send translated pet images to output node 
    workflow.connect(join_translateNode, 'offset', outputnode, 'translated_pet')

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
    rotated_pet = traits.List( mandatory=True, desc="Input list of translated PET images")
    translated_pet = traits.List( mandatory=True, desc="Input list of rotated PET images")
    t1_images = traits.List( mandatory=True, desc="Input list of T1 images")
    pet_images = traits.List( mandatory=True, desc="Input list of PET images")
    brain_masks = traits.List( mandatory=True, desc="Input list of brain masks images")
    subjects= traits.List( mandatory=True, desc="Input list of subjects")
    conditions= traits.List( mandatory=True, desc="List of conditions")
    study_prefix= traits.List( mandatory=True, desc="Prefix of study")
    distance_metrics = traits.Dict(mandatory=True,desc="Dictionary with distance metrics")
    colnames = traits.List(mandatory=True,desc="Column names for Pandas DataFrame")
    out_file = traits.File(desc="Output file")

class distance_metricCommand(BaseInterface):
    input_spec = distance_metricInput 
    output_spec = distance_metricOutput
   
    def _run_interface(self, runtime):
        #######################################################
        # Create lists of misaligned PET images to pass to QC #
        #######################################################
        subjects=self.inputs.subjects
        conditions=self.inputs.conditions
        pet_images=self.inputs.pet_images
        t1_images=self.inputs.t1_images
        brain_masks=self.inputs.brain_masks
        rotated_pet=self.inputs.rotated_pet
        study_prefix=self.inputs.study_prefix
        translated_pet=self.inputs.translated_pet
        distance_metrics = self.inputs.distance_metrics
        colnames = list(self.inputs.colnames)

        df=pd.DataFrame(columns=colnames)

        outlier_measure_list=[]
        flatten = lambda  l: [ j for i in l for j in i]
        
        rotated_pet = flatten(rotated_pet)
        translated_pet=flatten(translated_pet)
        misaligned=rotated_pet + translated_pet 
        home_dir=os.getcwd()
        self.inputs.out_file=home_dir+os.sep+"test_group_qc_metric.csv"

        df=calc_distance_metrics(df, subjects, conditions, misaligned, pet_images, t1_images, brain_masks, distance_metrics )
        df.to_csv(self.inputs.out_file, index=False)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

#
# Outlier measures 
#

class outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class outlier_measuresInput(BaseInterfaceInputSpec):
    outlier_measures = traits.Dict(mandatory=True, desc="Dictionary with outlier measures")
    distance_metrics = traits.Dict(mandatory=True, desc="Dictionary with distance metrics")
    normal_param = traits.Str(mandatory=True, desc="Normal alignment parameter (eg 0,0,0)")
    out_file = traits.File(desc="Output file")
    in_file = traits.File(exists=True,mandatory=True,desc="In file")

class outlier_measuresCommand(BaseInterface):
    input_spec = outlier_measuresInput 
    output_spec= outlier_measuresOutput
   
    def _run_interface(self, runtime):
        #######################################################
        outlier_measures= self.inputs.outlier_measures
        distance_metrics = self.inputs.distance_metrics
        normal_param = self.inputs.normal_param

        df=pd.read_csv(self.inputs.in_file)
        #Calculate the outlier measures based on group values of each distance metric
        df=calc_outlier_measures(df, outlier_measures, distance_metrics, normal_param)
        self.inputs.out_file=os.getcwd()+os.sep+"test_group_qc_outliers.csv"
        df.to_csv(self.inputs.out_file, index=False )
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs
#
# Outlier measures ROC
#

class outlier_measures_rocOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class outlier_measures_rocInput(BaseInterfaceInputSpec):
    outlier_threshold = traits.Dict(mandatory=True, desc="List of thresholds for outlier measures")
    normal_param = traits.Str(mandatory=True,desc="Normal alignment parameter (eg 0,0,0)")
    out_file = traits.File(desc="Output file")
    in_file = traits.File(exists=True,mandatory=True,desc="Input file")
class outlier_measures_rocCommand(BaseInterface):
    input_spec = outlier_measures_rocInput 
    output_spec= outlier_measures_rocOutput
   
    def _run_interface(self, runtime):
        #Calculate ROC curves based on outlier measures
        outlier_threshold = self.inputs.outlier_threshold
        normal_param = self.inputs.normal_param
        df=pd.read_csv(self.inputs.in_file)
        roc_df=outlier_measure_roc(df, outlier_threshold, normal_param)
        self.inputs.out_file = os.getcwd()+os.sep+"test_group_qc_roc.csv"
        roc_df.to_csv(self.inputs.out_file, index=False) 
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


#
# Plot outlier measures
#

class plot_outlier_measuresOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class plot_outlier_measuresInput(BaseInterfaceInputSpec):
    outlier_measures = traits.Dict(mandatory=True, desc="Dictionary with outlier measures")
    distance_metrics = traits.Dict(mandatory=True,desc="Dictionary with distance metrics")
    out_file = traits.File(desc="Output file")
    in_file = traits.File(exists=True, mandatory=True,desc="Input file")

class plot_outlier_measuresCommand(BaseInterface):
    input_spec = plot_outlier_measuresInput 
    output_spec= plot_outlier_measuresOutput
   
    def _run_interface(self, runtime):
        outlier_measures= self.inputs.outlier_measures
        distance_metrics = self.inputs.distance_metrics
        #Calculate ROC curves based on outlier measures
        df=pd.read_csv(self.inputs.in_file)

        self.inputs.out_file = os.getcwd()+os.sep+'outlier_measures.png'
        plot_outlier_measures(df, outlier_measures, distance_metrics, self.inputs.out_file, color=cm.spectral)

        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs
#
# Plot ROC curves
#

class plot_rocOutput(TraitedSpec):
    out_files = traits.List(desc="Output file")

class plot_rocInput(BaseInterfaceInputSpec):
    error_type_unit=traits.Dict(desc="Error units")
    error_type_name=traits.Dict(desc="Error type")
    out_files = traits.List(desc="Output file")
    in_file = traits.File(desc="Input file")

class plot_rocCommand(BaseInterface):
    input_spec = plot_rocInput 
    output_spec= plot_rocOutput
   
    def _run_interface(self, runtime):
        #Calculate ROC curves based on outlier measures
        df=pd.read_csv(self.inputs.in_file)
        error_type_unit=self.inputs.error_type_unit
        error_type_name=self.inputs.error_type_name
        self.inputs.out_files=plot_roc(df, error_type_unit, error_type_name)

        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_files"] = self.inputs.out_files
        return outputs


### WORKFLOW

def get_test_group_coreg_qc_workflow(name, opts):

    workflow = pe.Workflow(name=name)
    params=['subjects','study_prefix', 'conditions', 'pet_images', 't1_images','brain_masks', 'rotated_pet', 'translated_pet']
    inputnode=pe.Node(interface=niu.IdentityInterface(fields=params) , name='inputnode')
    outputnode=pe.Node(interface=niu.IdentityInterface(fields=['outlier_measures_df', 'outlier_measures_plot', 'outlier_measures_roc_plot']), name='outputnode')


    normal_param='0,0,0'
    outlier_measures={'MAD':qc.img_mad}
    outlier_threshold={ 'MAD':[-6,-5,-4,-3,-2,-1,0, 1,2,3,4,5,6]}
    distance_metrics={'NMI':qc.mi, 'CC':qc.cc, 'IV':qc.iv, 'FSE':qc.fse} 
    error_type_unit={"angle":"(degrees)",  "offset":'(mm)'} 
    error_type_name={"angle":'rotation',  "offset":'translation'} 
    colnames= ["Subject", "Condition", "ErrorType", "Error", "Metric", "Value"] 
    
    #calculate distance metric node
    distance_metricNode=pe.Node(interface=distance_metricCommand(), name="distance_metricNode")
    workflow.connect(inputnode, 'rotated_pet', distance_metricNode, 'rotated_pet')
    workflow.connect(inputnode, 'translated_pet', distance_metricNode, 'translated_pet')
    workflow.connect(inputnode, 't1_images', distance_metricNode, 't1_images')
    workflow.connect(inputnode, 'pet_images', distance_metricNode, 'pet_images')
    workflow.connect(inputnode, 'brain_masks', distance_metricNode, 'brain_masks')
    workflow.connect(inputnode, 'conditions', distance_metricNode, 'conditions')
    workflow.connect(inputnode, 'study_prefix', distance_metricNode, 'study_prefix')
    workflow.connect(inputnode, 'subjects', distance_metricNode, 'subjects')
    distance_metricNode.inputs.distance_metrics=distance_metrics
    distance_metricNode.inputs.colnames = colnames
    
    #calculate outlier measures node
    outlier_measuresNode=pe.Node(interface=outlier_measuresCommand(), name="outlier_measuresCommand")
    workflow.connect(distance_metricNode, 'out_file', outlier_measuresNode, 'in_file')
    outlier_measuresNode.inputs.outlier_measures = outlier_measures
    outlier_measuresNode.inputs.distance_metrics = distance_metrics
    outlier_measuresNode.inputs.normal_param = normal_param
    
    #plot outlier measures node
    plot_outlier_measuresNode=pe.Node(plot_outlier_measuresCommand(), name="plot_outlier_measuresCommand")
    plot_outlier_measuresNode.inputs.distance_metrics=distance_metrics
    plot_outlier_measuresNode.inputs.outlier_measures=outlier_measures
    workflow.connect(outlier_measuresNode, 'out_file', plot_outlier_measuresNode, 'in_file')

    #calculate ROC for outlier measures
     
    rocNode=pe.Node(outlier_measures_rocCommand(), name="rocNode")
    rocNode.inputs.outlier_threshold=outlier_threshold
    rocNode.inputs.normal_param = normal_param
    workflow.connect(outlier_measuresNode, 'out_file', rocNode, 'in_file')

    #plot roc node
    plot_rocNode=pe.Node(plot_rocCommand(), name="plot_rocNode")
    plot_rocNode.inputs.error_type_unit = error_type_unit
    plot_rocNode.inputs.error_type_name = error_type_name
    workflow.connect(rocNode, 'out_file', plot_rocNode, 'in_file')

    workflow.connect(outlier_measuresNode, 'out_file', outputnode, 'outlier_measures_df')
    workflow.connect(plot_outlier_measuresNode, 'out_file', outputnode, 'outlier_measures_plot')
    workflow.connect(plot_rocNode, 'out_files', outputnode, 'outlier_measures_roc_plot')
    return workflow
    
### FUNCTIONS


def plot_roc(df, error_type_unit, error_type_name, color=cm.spectral, DPI=1000):
    figs=[]
    fn_list=[]
    n=1
    nMeasure=len(np.unique(df.Measure))
    nMetric=len(np.unique(df.Metric))
    
    f=lambda x: float( str(x).split(',')[-1] )
    color=cm.cool

    df.Error = df.Error.apply(f)

    pts=pd.Series([0,1])
    nFig=0
    for error_type_key, error_type in df.groupby(['ErrorType']):
        nUnique = float(len(error_type.Error.unique() ))
        d = {key : color(value/nUnique) for (value, key) in enumerate(error_type.Error.unique()) }
        figs.append(plt.figure())
        #figs[nFig].suptitle('Outlier detection of misaligned PET images')
        n=1
        axs=[]
        for measure_type_key, measure_type in error_type.groupby(['Measure']):
            for metric_type_key, metric_type in measure_type.groupby(['Metric']):
                ax = plt.subplot(nMeasure, nMetric, n)
                ax.set_title('ROC for outlier detection for error in ' +error_type_name[error_type_key])
                ax.set_ylabel('True positive rate')
                ax.set_xlabel('False positive rate')
                ax.plot([0,1], [0,1], 'k--', c='red')
                for key, test in metric_type.groupby(['Error']):
                    #print test
                    x=test.FalsePositive#.append(pts)
                    y=test.TruePositive#.append(pts)
                    ax.plot(x,y, c=d[key], label=key  ) 
                ax.set_xlim(0,1)
                ax.set_ylim(0,1)
                ax.set_alpha(0.25)
                ax.legend(loc="lower right", fontsize=8, title='Error '+ error_type_unit[error_type_key])
                axs.append(ax)
                n += 1
                
        error_names=error_type.Error.unique()
        fn=os.getcwd() + os.sep + error_type_key + '_roc.png'
        fn_list += fn
        print  'saving roc to ' + fn
        figs[nFig].savefig(fn, width=200*nMetric, dpi=DPI)
        nFig += 1
        return(fn_list)

def  outlier_measure_roc(df, outlier_threshold, normal_error):
    subjects=np.unique(df.Subject)
    roc_columns=['ErrorType', 'Measure', 'Metric','Error','Threshold', 'FalsePositive', 'TruePositive' ]
    roc_df=pd.DataFrame(columns=roc_columns )
    for error_type_key, error_type in df.groupby(['ErrorType']):
        for measure_type_key, measure_type in error_type.groupby(['Measure']):
            for metric_type_key, metric_type in measure_type.groupby(['Metric']):
                normal=metric_type[metric_type.Error == normal_error]
                misaligned=metric_type[ ~(metric_type.Error == normal_error) ]
                for key, test in misaligned.groupby(['Error']):
                    for threshold in outlier_threshold[measure_type_key]:
                        #Given an error type (e.g., rotation), an error parameter (e.g., degrees of rotation), a distance metric (e.g., mutual information ),
                        #that defines a set of misaligned PET images, if we take all of the normal (i.e., correctly aligned data) and pool it with the misaligned data
                        [tp, fp] = estimate_roc(test, normal, threshold)
                        temp = pd.DataFrame( [[error_type_key, measure_type_key, metric_type_key,key, threshold, fp, tp]], columns=roc_columns)
                        roc_df=pd.concat([roc_df, temp])

    return(roc_df)


def estimate_roc(test, control, threshold, nRep=5000):
    n=int(test.shape[0])
    nTest=int(floor(n/2))
    nControl=n-nTest
    range_n=range(n)
    TPlist=[]
    FPlist=[]
    test.index=range_n
    control.index=range_n
    test_classify=pd.Series([ 1 if test.Score[i] > threshold else 0 for i in range_n ])
    control_classify=pd.Series([ 1 if control.Score[i] > threshold else 0 for i in range_n ])

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
    TPrate=sum(test_classify)/float(n)
    FPrate=sum(control_classify)/float(n)

    #if sum(test.Error == "0,0,16") > 0 :
    #   print 'Threshold', threshold
    #   print pd.concat([test, test_classify, control.Score, control_classify ], axis=1)
    #   print TPrate, FPrate

    #print sum(test_classify)/float(n), sum(control_classify)/float(n)
    return([TPrate, FPrate])
        

        

def calc_distance_metrics(df, subjects, conditions, misaligned, pet_images, t1_images, brain_masks, distance_metrics):
    print subjects
    print conditions
    for sub, cond in zip(subjects, conditions):
        sub_misaligned=[ i for i in misaligned if sub in i and cond in i  ]
        pet_normal = [ i for i in pet_images if sub in i and cond in i ][0]
        t1=[ i for i in t1_images if sub in i and cond in i ][0]
        brain_mask=[ i for i in brain_masks if sub in i and cond in i ][0]
        print pet_normal
        print t1
        print brain_mask
        #Get the distance metrics for each subject for their normal PET image 

        #Put distance metric values into a data frame
        sub_df=pd.DataFrame(columns=df.columns)

        #Get outlier metric for normal PET image
        #Get distance metrics for each subject for their misaligned PET images
        for pet_img in sub_misaligned:
            print '\n', pet_img
            print t1
            print brain_mask
            path, ext = os.path.splitext(pet_img)
            base=basename(path)
            param=base.split('_')[-1]
            param_type=base.split('_')[-2]
            label='_'+sub+'_'+cond+'_'+param_type+'_'+param
            mis_metric=[]
            ###Apply distance metrics
            for  metric_name,metric_func in distance_metrics.iteritems():
                m=qc.distance(pet_img, t1, brain_mask, metric_func) 
                #Append misaligned distance metrics to the subject data frame
                temp=pd.DataFrame([[sub,cond,param_type,param, metric_name, m]],columns=df.columns  ) 
                sub_df = pd.concat([sub_df, temp])
        df = pd.concat([df, sub_df])
    df.index=range(df.shape[0])
    return(df)

def calc_outlier_measures(df, outlier_measures, distance_metrics, normal_param):
    outlier_measure_list=outlier_measures.values()#List of functions calculating outlier measure  
    outlier_measure_names=outlier_measures.keys() #List of names of outlier measures
    metric_names=distance_metrics.keys() #List of names for distance metrics

    subjects=np.unique(df.Subject) #List of subjects

    unique_error_types=np.unique(df.ErrorType) #List of errors types in PET mis-alignmenta
    n=df.shape[0]
    #empty_df = pd.DataFrame(np.zeros([n,1]), columns=['Score'] , index=[0]*n)
    #df2 = pd.DataFrame([])
    #print empty_df
    #for measure in outlier_measure_names:
    #    m=pd.DataFrame( { 'Measure':[measure] * n}, index=[0]*n  )
    #    print(m)
    #    d=pd.concat([df,m,empty_df], axis=1)
    #    print(d)
    #    df2=pd.concat([df2,d])
    #    print(df2)
    no=len(outlier_measure_names)
    n2 = n * no
    df2 = pd.concat([df]*no, ignore_index=True)
    mdf = pd.DataFrame( {'Measure': sum([ [x] * n for x in outlier_measure_names  ],[]), 'Score':np.zeros(n2)  } )
    d=pd.concat([df2,mdf], axis=1)
    df=d
    #print d
    #print d[ (d.shape[0]-20):d.shape[0] ]
    #for error_type in unique_error_types:
    for error_type, error_type_df in df.groupby(['ErrorType']):
        unique_errors = np.unique( df.Error[df.ErrorType == error_type ] )#Get list of error parameters for error type 
        normal_df=df[ ( df.Error == normal_param ) & (df.ErrorType == error_type) ] #Get list of normal subjects for this error type
        #for error in unique_errors: 
        for error, error_df in error_type_df.groupby(['Error']):
            #for sub in subjects:
            for sub, sub_df in error_df.groupby(['Subject']):
                #Remove the current subject from the data frame containing normal subjects
                temp_df=normal_df[ ~ (normal_df.Subject == sub) ]
                for cond, mis_df in sub_df.groupby(['Condition']):
                    #Create data frame of a single row for this subject, error type and error parameter
                    #mis_df = df[(df.Subject==sub) & (df.ErrorType == error_type) & (df.Error == error) ]
                    #print 'Misaligned DF'
                    #print mis_df
                    #Combine the data frame with normal PET images with that of the mis-aligned PET image
                    temp2_df=pd.concat([temp_df, mis_df])
                    for metric_name in metric_names:
                        #Create a test data frame, test_df, with only the values for the current metric in the 'Value' column
                        test_df=temp2_df[ temp2_df.Metric == metric_name ]
                        #Get the index number of the last, misaligned PET image
                        n=test_df.shape[0]-1
                        #Get column number for the current distance metric
                        #metric_index=df.columns.get_loc(metric_name)
                        for measure, measure_name in zip(outlier_measure_list, outlier_measure_names):
                            #Get column number of the current outlier measure
                            #measure_index=df.columns.get_loc(measure_name)
                            #Reindex the test_df from 0 to the number of rows it has
                            test_df.index=range(test_df.shape[0]) 
                            #Get the series with the 
                            x=pd.Series(test_df.Value)
                            #Calculate the distance measure for the current measure
                            print "test_df"
                            print test_df
                            r=measure(x,n)
                            #Identify the target row where the outlier measure, r, needs to be inserted
                            target_row=(df.Subject == sub) & (df.ErrorType == error_type) & (df.Error == error) & (df.Metric == metric_name ) & (df.Measure == measure_name ) 
                            #Insert r into the data frame
                            df.loc[ target_row, 'Score' ] =r


    
    #g=lambda x: df.columns.get_loc(x)
    #imin=min(map(g, metric_names))
    #list(df.columns[0:imin])
    print 'Okay!'              
    return(df)


from matplotlib.lines import Line2D
def plot_outlier_measures(df, outlier_measures, distance_metrics, out_fn, color=cm.spectral):
    f=lambda x: float(str(x).split(',')[-1])
    nMetric=len(df.Metric.unique())
    nMeasure=len(df.Measure.unique())
    df.Error = df.Error.apply(f)

    color=cm.spectral
  
    #linestyles = ['_', '-', '--', ':']
    #markers = []
    #for m in Line2D.markers:
    #    try:
    #        if len(m) == 1 and m != ' ': markers.append(m)
    #    except TypeError: pass
            

    sub_cond=np.array([ str(a)+'_'+str(b) for a,b in  zip(df.Subject, df.Condition) ])
    sub_cond_unique = np.unique(sub_cond)
    print sub_cond_unique
    nUnique=float(len(sub_cond_unique))
    #d = {key : color(value/nUnique) for (value, key) in enumerate(sub_cond_unique) }
    #print d

    #styles = markers + [r'$\lambda$', r'$\bowtie$', r'$\circlearrowleft$', r'$\clubsuit$', r'$\checkmark$']
    #nStyles=len(styles)
    #if nStyles < len(distance_metrics):
    #    print "Warning: too many distance metrics!\nMore distance metrics than unique marker styles for plot."
    #marker_style = { distance_metrics.keys()[i] : styles[i % nStyles] for i in range(len(distance_metrics)) }
    #print marker_style 

    d = { key : color(value/float(nMetric)) for (value, key) in enumerate(distance_metrics.keys()) }


    ax_list=[]
    measures=outlier_measures.keys()
    nErrorType=len(np.unique(df.ErrorType))
    plt.clf()
    fig=plt.figure(1)
    fig.suptitle('Outlier detection of misaligned PET images')
    n=1
    for key, group in df.groupby(['ErrorType']):
        for measure, group2 in group.groupby(['Measure']): 
            ax=plt.subplot(nErrorType, nMeasure, n)
            ax.set_title('Outlier detection based on '+measure)
            ax.set_ylabel(measure)
            ax.set_xlabel('Error in '+key)

            for metric, group3 in group2.groupby(['Metric']):
                #for key4, group4 in group3.groupby(['Subject']):
                    #for key5, group5 in group3.groupby(['Subject', 'Condition']):
                    #    
                    #    sub_cond_key = key5[0] + '_' + key5[1]
                    #    print marker_style[metric]
                    #    
                    #    ax.plot(group5.Error, group5.Score, linestyle='-', marker=marker_style[metric], c=d[sub_cond_key], label=sub_cond_key)
                y=group3.groupby(['Error']).Score.mean()
                ax.plot(y.index, y, c=d[metric], label=metric)


        ax.legend(loc="best", fontsize=7)
        n+=1
    #plt.show()
    print 'saving outlier plot to', out_fn
    plt.savefig(out_fn,width=1000*nMeasure, dpi=1000)


                    
                #for outlier_measure in outlier_measure_list:
                #    outlier_measure(test_df)

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
        print '\n', self.inputs.out_file, '\n'
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
      


