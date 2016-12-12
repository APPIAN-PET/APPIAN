import nipype
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,  BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import pyminc.volumes.factory as pyminc
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import fnmatch
import os
import shutil
from math import sqrt
from os import getcwd
from os.path import basename
from sys import argv, exit
from re import sub
import nipype.interfaces.minc.resample as rsl
import Quality_Control as qc




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




class test_group_coreg_qcOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class test_group_coreg_qcInput(BaseInterfaceInputSpec):
    rotated_pet = traits.List( mandatory=True, desc="Input list of translated PET images")
    translated_pet = traits.List( mandatory=True, desc="Input list of rotated PET images")
    t1_images = traits.List( mandatory=True, desc="Input list of T1 images")
    pet_images = traits.List( mandatory=True, desc="Input list of PET images")
    brain_masks = traits.List( mandatory=True, desc="Input list of brain masks images")
    subjects= traits.List( mandatory=True, desc="Input list of subjects")
    conditions= traits.List( mandatory=True, desc="List of conditions")
    study_prefix= traits.List( mandatory=True, desc="Prefix of study")
    out_file = traits.File(desc="Output file")

pd.set_option('display.width', 1000)

class test_group_coreg_qcCommand(BaseInterface):
    input_spec = test_group_coreg_qcInput 
    output_spec = test_group_coreg_qcOutput
   
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

        outlier_measures={'KSD':qc.kolmogorov_smirnov, 'MAD':qc.img_mad}
        distance_metrics={'NMI':qc.mi, 'XCorr':qc.xcorr }

        metric_names=["NMI", "XCorr"]
        outlier_measure_list=[qc.kolmogorov_smirnov, qc.img_mad]
        outlier_measure_names=['KSD', 'MAD']
        colnames= ["Subject", "Condition", "ErrorType", "Error" ] + metric_names + outlier_measure_names
        df=pd.DataFrame(columns=colnames)
        metrics=[ qc.mi, qc.xcorr ] #stochastic sign change
        outlier_measure_list=[]
        flatten = lambda  l: [ j for i in l for j in i]
        rotated_pet = flatten(rotated_pet)
        translated_pet=flatten(translated_pet)
        misaligned=rotated_pet + translated_pet 

        test_group_qc_csv="/data1/projects/scott/test_group_qc.csv"

        test_group_qc_full_csv="/data1/projects/scott/test_group_qc_full.csv"
        self.inputs.out_file=test_group_qc_csv

        if os.path.exists(test_group_qc_csv) == False:
            df=calc_distance_metrics(subjects, conditions, misaligned, pet_images, t1_images, brain_masks, distance_metrics)
            df.to_csv(test_group_qc_csv, index=False )
        else:
            df=pd.read_csv(test_group_qc_csv)


        #Calculate the outlier measures based on group values of each distance metric
        df=calc_outlier_measures(df, outlier_measures, distance_metrics)
        df.to_csv(test_group_qc_full_csv, index=False )
        print "\n\n\nOkay whatever\n\n\n" 
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_list"] = self.inputs.out_list
        return outputs

def calc_distance_metrics(subjects, conditions, misaligned, pet_images, t1_images, brain_masks, distance_metrics):
    for sub, cond in zip(subjects, conditions):
        if cond != 'C': continue
        sub_misaligned=[ i for i in misaligned if sub in i  ]
        pet_normal = [ i for i in pet_images if sub in i and cond in i ][0]
        t1=[ i for i in t1_images if sub in i and cond in i ][0]
        brain_mask=[ i for i in brain_masks if sub in i and cond in i ][0]
        print pet_normal
        print t1
        print brain_mask
        #Get the distance metrics for each subject for their normal PET image 

        #Put distance metric values into a data frame
        sub_df=pd.DataFrame(columns=colnames)

        #Get outlier metric for normal PET image
        print sub_df
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
            for m in distance_metrics.values():
                mis_metric.append( m(pet_img, t1, brain_mask) )
            #Append misaligned distance metrics to the subject data frame
            temp=pd.DataFrame([[sub,cond,param_type,param]+mis_metric + [0,0]],columns=colnames ) 
            sub_df = pd.concat([sub_df, temp])
        df = pd.concat([df, sub_df])
    return(df)

def calc_outlier_measures(df, outlier_measures, distance_metrics):
    normal_param='0,0,0'
    outlier_measure_list=outlier_measures.values()#List of functions calculating outlier measure  
    outlier_measure_names=outlier_measures.keys() #List of names of outlier measures
    metric_names=distance_metrics.keys() #List of names for distance metrics

    subjects=np.unique(df.Subject) #List of subjects

    unique_error_types=np.unique(df.ErrorType) #List of errors types in PET mis-alignment

    for error_type in unique_error_types: 
        unique_errors = np.unique( df.Error[df.ErrorType == error_type ] )#Get list of error parameters for error type 
        normal_df=df[ ( df.Error == normal_param ) & (df.ErrorType == error_type) ] #Get list of normal subjects for this error type
        for error in unique_errors: 
            for sub in subjects:
                #Create data frame of a single row for this subject, error type and error parameter
                mis_df = df[(df.Subject==sub) & (df.ErrorType == error_type) & (df.Error == error) ]
                #Remove the current subject from the data frame containing normal subjects
                temp_df=normal_df[ ~ (normal_df.Subject == sub) ]
                #Combine the data frame with normal PET images with that of the mis-aligned PET image
                test_df=pd.concat([temp_df, mis_df])
                #Get the index number of the last, misaligned PET image
                n=test_df.shape[0]-1
                for metric_name in metric_names:
                    #Get column number for the current distance metric
                    metric_index=df.columns.get_loc(metric_name)
                    for measure, measure_name in zip(outlier_measure_list, outlier_measure_names):
                        #Get column number of the current outlier measure
                        measure_index=df.columns.get_loc(measure_name)
                        #Reindex the test_df from 0 to the number of rows it has
                        test_df.index=range(test_df.shape[0]) 
                        #Get the series with the 
                        x=pd.Series(test_df.iloc[:,metric_index])
                        #Calculate the distance measure for the current measure
                        r=measure(x,n)
                        #Identify the target row where the outlier measure, r, needs to be inserted
                        target_row=(df.Subject == sub) & (df.ErrorType == error_type) & (df.Error == error)
                        #Insert r into the data frame
                        df.loc[ target_row,  df.columns[measure_index]] =r


    #FIXME Need a better way to deal with multiple metrics and measures, Maybe each measure should have it's own table
    #FIXME need to graph by average for each condition, then done! 
    #NOTE: Mutual information seems to work well, but not XCorr. Also Kolmogorov-Smirnov seems not to work. 
    #Sunday: Produce initial graphs for mutual info, fix multiple metric/ measure problem
    #Monday: Add metrics / measures
    #Tuesday: Write up for OHBM
    g=lambda x: df.columns.get_loc(x)
    imin=min(map(g, metric_names))
    
    list(df.columns[0:imin])
    print 'Okay!'              
    return(df)
                    
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
      


