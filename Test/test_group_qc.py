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
    angles=['2,0,0', '4,0,0', '8,0,0', '16,0,0', '32,0,0', '64,0,0'] #X,Y,Z angle of rotation
    offsets=['2,0,0', '4,0,0', '8,0,0', '10,0,0', '12,0,0', '14,0,0' ] #X,Y,Z offset of translation (in mm)
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
    study_prefix= traits.Str( mandatory=True, desc="Prefix of study")
    out_list = traits.List(desc="Output list")

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
    
        for sub, cond in zip(subjects, conditions):
            if sub != 'sub01': continue
            print sub
            index=subjects.index(sub) #FIXME: Won't work for subjects with multiple conditions
            sub_misaligned=rotated_pet[index] + translated_pet[index]
            cond=conditions[index]
            normal = [ i for i in pet_images if not sub in i ]
            #print 'Mis-aligned'
            #print sub_misaligned
            #print 'Normal'
            #print normal
            for mis in sub_misaligned:
                path, ext = os.path.splitext(mis)
                base=basename(path)
                param=base.split('_')[-1]
                param_type=base.split('_')[-2]
                label='_'+sub+'_'+cond+'_'+param_type+'_'+param
                test_pet = [mis] + normal
                test_pet = [ pet for (t1, pet) in sorted(zip(t1_images, test_pet))]
                print mis
                #print 'Test PET'
                #print test_pet
                qc.group_coreg_qc(test_pet, t1_images, brain_masks, subjects, conditions, study_prefix, label )


            

        print "\n\n\nOkay whatever\n\n\n" 

        
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
      


