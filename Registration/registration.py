# vim: set tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
# vim: filetype plugin indent on
import os
import re
import numpy as np
import tempfile
import shutil
import Extra.resample as rsl
import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from Registration.ants_mri_normalize import APPIANRegistration, APPIANConcatenateTransforms, APPIANApplyTransforms

from os.path import basename
from nipype.interfaces.base import TraitedSpec, File, traits, InputMultiPath
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile
from nipype.interfaces.utility import Rename
from Extra.tracc import TraccCommand
from Extra.xfmOp import ConcatCommand

"""
.. module:: registration
    :platform: Unix
    :synopsis: Module to perform image registration.
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""


#def misalign_pet(workflow, inputnode, pet2mri ) :
#    ###Create rotation tfm files based on transform error
#    transformNode = pe.Node(interface=rsl.param2tfmInterfaceCommand(), name='transformNode')
#    workflow.connect(inputnode, 'error', transformNode, 'transformation')
#
#    ### Concatenate pet2mri and misalignment tfm
#    pet2misalign_tfm=pe.Node(interface=ConcatCommand(), name="pet2misalign_tfm")
#    workflow.connect(pet2mri,'composite_transform', pet2misalign_tfm, 'in_file')
#    workflow.connect(transformNode,'out_file', pet2misalign_tfm, 'in_file_2')
#
#    ###Apply transformation to PET file
#    transform_resampleNode=pe.Node(interface=rsl.ResampleCommand(),name="transform_resampleNode")
#    transform_resampleNode.inputs.use_input_sampling=True;
#    workflow.connect(transformNode, 'out_file', transform_resampleNode, 'transformation')
#    workflow.connect(pet2mri, 'warped_image', transform_resampleNode, 'in_file')
#
#    ###Rotate brain mask
#    transform_brainmaskNode=pe.Node(interface=rsl.ResampleCommand(), name="transform_brainmaskNode" )
#    transform_brainmaskNode.inputs.interpolation='nearest_neighbour'
#    workflow.connect(pet2misalign_tfm, 'out_file', transform_brainmaskNode, 'transformation')
#    workflow.connect(transform_resampleNode, 'out_file', transform_brainmaskNode, 'model_file')
#
#    invert_concat_pet2misalign_tfm=pe.Node(interface=minc.Invert(),name="invert_concat_pet2misalign_tfm")
#    workflow.connect(pet2misalign_tfm,'out_file',invert_concat_pet2misalign_tfm,'input_file')
#    pet2mri = final_pet2mri = pe.Node(interface=niu.IdentityInterface(fields=["warped_image", "composite_transform", "composite_transform_invert"]), name="pet2mri_misaligned")
#    workflow.connect(transform_resampleNode, "out_file", final_pet2mri, "warped_image")
#    workflow.connect(pet2misalign_tfm, "out_file", final_pet2mri, "composite_transform")
#    workflow.connect(invert_concat_pet2misalign_tfm, "output_file", final_pet2mri, "composite_transform_invert")
#    t1_brain_mask_img = 'out_file'

def get_workflow(workflow, infosource, opts):
    '''
        Create workflow to perform PET to T1 co-registration.

        1. PET to T1 coregistration with brain masks
        2. Transform T1 MRI brainmask and headmask from MNI 152 to T1 native

        :param name: Name for workflow
        :param infosource: Infosource for basic variables like subject id (sid) and condition id (cid)
        :param datasink: Node in which output data is sent
        :param opts: User options

        :returns: workflow
    '''
    #workflow = pe.Workflow(name=name)
    #bnDefine input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_volume","pet_volume_4d","mri_space_nat","mri_space_stx","t1_headMask", "pet_brain_mask", "t1_brain_mask", "tfm_mri_stx", "tfm_stx_mri", "mri_space_stx", "error", "header" ]), name='inputnode')
    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["petmri_img", "pet_img_4d","tfm_pet_mri","tfm_mri_pet",'tfm_pet_stx', 'tfm_stx_pet' ]), name='outputnode')

    node_name="pet2mri"
    pet2mri = pe.Node(interface=APPIANRegistration(), name="pet2mri")
    pet2mri.inputs.normalization_type='rigid'
    if opts.pet_brain_mask :
        workflow.connect(inputnode, 'pet_brain_mask', pet2mri, 'moving_image_mask')
    workflow.connect(inputnode, 't1_brain_mask', pet2mri, 'fixed_image_mask')
    workflow.connect(inputnode, 'pet_volume', pet2mri, 'moving_image')
    workflow.connect(inputnode, 'mri_space_nat', pet2mri, 'fixed_image')

    #if opts.test_group_qc : misalign_pet(workflow, inputnode, pet2mri )

    #pet_stx_node = pe.Node( interface=APPIANConcatenateTransforms(), name="pet_stx_node")
    #workflow.connect(pet2mri, "out_matrix", pet_stx_node, "transform_1")
    #workflow.connect(inputnode, "tfm_mri_stx", pet_stx_node, "transform_2")

    #stx_pet_node = pe.Node(interface=APPIANConcatenateTransforms(), name="stx_pet_node")
    #workflow.connect( inputnode, "tfm_stx_mri", stx_pet_node, 'transform_2' )
    #workflow.connect( pet2mri, "out_matrix_inverse", stx_pet_node, 'transform_1' )


    #Resample 4d PET image to T1 space
    if opts.analysis_space == 't1':
        pettot1_4d = pe.Node(interface=APPIANApplyTransforms(), name='pet_space_mri')
        workflow.connect(inputnode, 'pet_volume_4d', pettot1_4d, 'input_image')
        workflow.connect(pet2mri, 'composite_transform', pettot1_4d, 'transform_2')
        workflow.connect(inputnode, 'mri_space_nat', pettot1_4d, 'reference_image')
        workflow.connect(pettot1_4d,'output_file', outputnode, 'pet_img_4d')

        workflow.connect(inputnode, 'mri_space_nat', outputnode, 't1_analysis_space')
    elif opts.analysis_space == "stereo" :
        #Resample 4d PET image to MNI space
        pettomni_4d = pe.Node(interface=APPIANApplyTransforms(), name='pet_space_stx')
        workflow.connect(inputnode, 'pet_volume_4d', pettomni_4d, 'input_image')
        workflow.connect(pet2mri, "out_matrix", pettomni_4d, 'transform_1')
        workflow.connect(inputnode, "out_mri_stx", pettomni_4d, 'transform_2')
        workflow.connect(inputnode, 't1_space_stx',pettomni_4d, 'reference_image')
        workflow.connect(pettomni_4d,'output_file', outputnode, 'pet_img_4d')
    if opts.normalization_type == 'nl' : 
        workflow.connect(pet2mri, 'composite_transform', outputnode, 'tfm_pet_mri')
        workflow.connect(pet2mri, 'inverse_composite_transform', outputnode, 'tfm_mri_pet')
    else :
        workflow.connect(pet2mri, 'out_matrix', outputnode, 'tfm_pet_mri')
        workflow.connect(pet2mri, 'out_matrix_inverse', outputnode, 'tfm_mri_pet')
    workflow.connect(pet2mri, 'warped_image', outputnode, 'petmri_img')
    return workflow
