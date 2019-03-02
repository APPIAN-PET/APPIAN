# vim: set tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
# vim: filetype plugin indent on
import os
import re
import numpy as np

import tempfile
import shutil
import Extra.resample as rsl
from Test.test_group_qc import myIdent
from os.path import basename

from pyminc.volumes.factory import *
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile
from nipype.interfaces.utility import Rename


from Extra.tracc import TraccCommand

import nipype.interfaces.minc as minc
from Extra.xfmOp import ConcatCommand


"""
.. module:: registration
    :platform: Unix
    :synopsis: Module to perform image registration.
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""


#def misalign_pet(workflow, inputnode, pet2mri ) :
#    ###Create rotation xfm files based on transform error
#    transformNode = pe.Node(interface=rsl.param2xfmInterfaceCommand(), name='transformNode')
#    workflow.connect(inputnode, 'error', transformNode, 'transformation')
#
#    ### Concatenate pet2mri and misalignment xfm
#    pet2misalign_xfm=pe.Node(interface=ConcatCommand(), name="pet2misalign_xfm")
#    workflow.connect(pet2mri,'out_file_xfm', pet2misalign_xfm, 'in_file')
#    workflow.connect(transformNode,'out_file', pet2misalign_xfm, 'in_file_2')
#
#    ###Apply transformation to PET file
#    transform_resampleNode=pe.Node(interface=rsl.ResampleCommand(),name="transform_resampleNode")
#    transform_resampleNode.inputs.use_input_sampling=True;
#    workflow.connect(transformNode, 'out_file', transform_resampleNode, 'transformation')
#    workflow.connect(pet2mri, 'out_file_img', transform_resampleNode, 'in_file')
#
#    ###Rotate brain mask
#    transform_brainmaskNode=pe.Node(interface=rsl.ResampleCommand(), name="transform_brainmaskNode" )
#    transform_brainmaskNode.inputs.interpolation='nearest_neighbour'
#    workflow.connect(pet2misalign_xfm, 'out_file', transform_brainmaskNode, 'transformation')
#    workflow.connect(transform_resampleNode, 'out_file', transform_brainmaskNode, 'model_file')
#
#    invert_concat_pet2misalign_xfm=pe.Node(interface=minc.XfmInvert(),name="invert_concat_pet2misalign_xfm")
#    workflow.connect(pet2misalign_xfm,'out_file',invert_concat_pet2misalign_xfm,'input_file')
#    pet2mri = final_pet2mri = pe.Node(interface=niu.IdentityInterface(fields=["out_file_img", "out_file_xfm", "out_file_xfm_invert"]), name="pet2mri_misaligned")
#    workflow.connect(transform_resampleNode, "out_file", final_pet2mri, "out_file_img")
#    workflow.connect(pet2misalign_xfm, "out_file", final_pet2mri, "out_file_xfm")
#    workflow.connect(invert_concat_pet2misalign_xfm, "output_file", final_pet2mri, "out_file_xfm_invert")
#    t1_brain_mask_img = 'out_file'

def get_workflow(name, infosource, opts):
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
    workflow = pe.Workflow(name=name)
    #bnDefine input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_volume","pet_volume_4d","t1_native_space","t1_headMask","tka_label_img_t1","results_label_img_t1","pvc_label_img_t1", "pet_brain_mask", "t1_brain_mask", "xfmT1MNI", "T1Tal", "error", "header" ]), name='inputnode')
    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["petmri_img", "pet_img_4d","petmri_xfm","mripet_xfm",'petmni_xfm', 'mnipet_xfm' ]), name='outputnode')

    node_name="pet2mri"
    pet2mri = pe.Node(interface=Registration(args='--float',
            verbose=1,
            collapse_output_transforms=True,
            initial_moving_transform_com=True,
            num_threads=1,
            output_inverse_warped_image=True,
            output_warped_image=True,
            sigma_units=['vox']*3,
            transforms=['Rigid'],
            terminal_output='file',
            winsorize_lower_quantile=0.005,
            winsorize_upper_quantile=0.995,
            convergence_threshold=[1e-08],
            convergence_window_size=[20],
            metric=['Mattes'],
            metric_weight=[1.0],
            #number_of_iterations=[[10000, 11110, 11110],
            #    [10000, 11110, 11110],
            #    [100, 30, 20]],
            number_of_iterations=[[1, 1, 1]],
            radius_or_number_of_bins=[32],
            sampling_percentage=[0.3 ],
            sampling_strategy=['Regular'],
            shrink_factors=[[3, 2, 1]],
            smoothing_sigmas=[[4.0, 2.0, 1.0]],
            transform_parameters=[(0.1)],
            use_estimate_learning_rate_once=[True],
            use_histogram_matching=[False],
            write_composite_transform=True),
            name="pet2mri")
    pet2mri.inputs.clobber = True
    pet2mri.inputs.verbose = opts.verbose
    pet2mri.inputs.lsq="lsq6"
    pet2mri.inputs.metric="mi"

    workflow.connect(inputnode,'pet_volume', pet2mri, 'in_source_file')
    workflow.connect(inputnode,'t1_native_space', pet2mri, 'in_target_file')#,
    

    #if opts.test_group_qc : misalign_pet(workflow, inputnode, pet2mri )


    PETMNIXfm_node = pe.Node( interface=ConcatCommand(), name="PETMNIXfm_node")
    workflow.connect(pet2mri, "out_file_xfm", PETMNIXfm_node, "in_file")
    workflow.connect(inputnode, "xfmT1MNI", PETMNIXfm_node, "in_file_2")

    MNIPETXfm_node = pe.Node(interface=minc.XfmInvert(), name="MNIPETXfm_node")
    workflow.connect( PETMNIXfm_node, "out_file", MNIPETXfm_node, 'input_file'  )

    workflow.connect(PETMNIXfm_node, 'out_file', outputnode, 'petmni_xfm' )
    workflow.connect(MNIPETXfm_node, 'output_file', outputnode, 'mnipet_xfm' )

    #Resample 4d PET image to T1 space
    if opts.analysis_space == 't1':
        pettot1_4d = pe.Node(interface=minc.Resample(), name='pet_t1_4d')
        pettot1_4d.inputs.keep_real_range=True
        workflow.connect(inputnode, 'pet_volume_4d', pettot1_4d, 'input_file')
        workflow.connect(pet2mri, 'out_file_xfm', pettot1_4d, 'transformation')
        workflow.connect(inputnode, 't1_native_space', pettot1_4d, 'like')
        workflow.connect(pettot1_4d,'output_file', outputnode, 'pet_img_4d')

        workflow.connect(inputnode, 't1_native_space', outputnode, 't1_analysis_space')
    elif opts.analysis_space == "stereo" :
        #Resample 4d PET image to MNI space
        pettomni_4d = pe.Node(interface=minc.Resample(), name='pet_mni_4d')
        pettomni_4d.inputs.keep_real_range=True
        workflow.connect(inputnode, 'pet_volume_4d', pettomni_4d, 'input_file')
        workflow.connect(PETMNIXfm_node, "out_file", pettomni_4d, 'transformation')
        workflow.connect(inputnode, 'T1Tal',pettomni_4d, 'like')
        workflow.connect(pettomni_4d,'output_file', outputnode, 'pet_img_4d')
    
    workflow.connect(pet2mri, 'out_file_xfm', outputnode, 'petmri_xfm')
    workflow.connect(pet2mri, 'out_file_xfm_invert', outputnode, 'mripet_xfm')
    workflow.connect(pet2mri, 'out_file_img', outputnode, 'petmri_img')
    return workflow
