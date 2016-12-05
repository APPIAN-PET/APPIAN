import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
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
    join_rotationsNode = pe.JoinNode(interface=niu.IdentityInterface(fields=['rotations']), joinsource="angle_splitNode", joinfield=["rotations"], name="join_rotationsNode")
    workflow.connect(rrotate_resampleNode, 'out_file', join_rotationsNode, 'rotations')

    ### B. Translate
    ###Send rotated pet images to output node 
    workflow.connect(join_rotationsNode, 'rotations', outputnode, 'rotated_pet')
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
    join_translateNode = pe.JoinNode(interface=niu.IdentityInterface(fields=["translations"]), joinsource="offset_splitNode", joinfield=["translations"], name="join_translateNode")
    workflow.connect(rtranslate_resampleNode, 'out_file', join_translateNode, 'translations')
    ###Send translated pet images to output node 
    workflow.connect(join_translateNode, 'translations', outputnode, 'translated_pet')

    return(workflow)




class test_group_coreg_qcOutput(TraitedSpec):
    out_list = traits.List(desc="Output list")

class test_group_coreg_qcInput(BaseInterfaceInputSpec):
    rotated_pet = traits.List( mandatory=True, desc="Input list of translated PET images")
    translated_pet = traits.List( mandatory=True, desc="Input list of rotated PET images")
    t1_images = traits.List( mandatory=True, desc="Input list of T1 images")
    pet_images = traits.List( mandatory=True, desc="Input list of PET images")
    brain_masks = traits.List( mandatory=True, desc="Input list of brain masks images")
    subjects= traits.List( mandatory=True, desc="Input list of subjects")
    conditions= traits.List( mandatory=True, desc="List of conditions")
    study_prefix= traits.List( mandatory=True, desc="Prefix of study")
    out_list = traits.List(desc="Output list")

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

        metric_names=["Mutual.Information", "XCorr"]
        outlier_measure_list=[qc.kolmogorov_smirnov, qc.img_mad]
        outlier_measure_names=['KSD', 'MAD']
        colnames= ["Subject", "Condition", "Error.Type", "Error" ] + metric_names + outlier_measure_names
        df=pd.DataFrame(columns=colnames)
        metrics=[ qc.mi, qc.xcorr ] #stochastic sign change
        outlier_measure_list=[]
        flatten = lambda  l: [ j for i in l for j in i]
        rotated_pet = flatten(rotated_pet)
        translated_pet=flatten(translated_pet)
        misaligned=rotated_pet + translated_pet 
        for sub, cond in zip(subjects, conditions):
            sub_misaligned=[ i for i in misaligned if sub in i  ]
            pet_normal = [ i for i in pet_images if sub in i and cond in i ][0]
            t1=[ i for i in t1_images if sub in i and cond in i ][0]
            brain_mask=[ i for i in brain_masks if sub in i and cond in i ][0]
            print pet_normal
            print t1
            print brain_mask
            #Get the distance metrics for each subject for their normal PET image 

            #Put distance metric values into a data frame
            sub_df=pd.DataFrame(columns=colnames  )

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
                for m in metrics:
                    mis_metric.append( m(pet_img, t1, brain_mask) )
                #Append misaligned distance metrics to the subject data frame
                temp=pd.DataFrame([[sub,cond,param_type,param]+mis_metric + [0,0]],columns=colnames ) 
                sub_df = pd.concat([sub_df, temp])
            df = pd.concat([df, sub_df])
            df.to_csv('/data1/projects/scott/test_group_qc.csv', index=False )
        print df


        '''normal_df=pd["Error.Type"=="Normal"]
        #Calculate the outlier measures based on group values of each distance metric
        for param_type in unique_param_types: #rotate and translate
            for param in unique_params:
                for sub in subjects:
                    
                    test_df=pd.concat(normal_df, mis_df)
                    for outlier_measure in outlier_measure_list:
                        outlier_measure(test_df)

        print "\n\n\nOkay whatever\n\n\n" 
        '''
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_list"] = self.inputs.out_list
        return outputs
 
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
      


