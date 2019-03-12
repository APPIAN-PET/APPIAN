import os
import numpy as np
import tempfile
import shutil
import pickle
import ntpath

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)

from nipype.interfaces.utility import Rename
from os.path import splitext
import nipype.interfaces.minc as minc
from Extra.xfmOp import InvertCommand
from Extra.morphomat import MorphCommand
from Extra.info import StatsCommand
from Extra.resample import param2xfmCommand
from Extra.obj import *
from Extra.xfmOp import ConcatCommand, ConcatNLCommand
from scipy.ndimage.morphology import binary_erosion
import Registration.registration as reg
import pyminc.volumes.factory as pyminc
import nibabel as nib

class LabelsInput(BaseInterfaceInputSpec):
    mniT1 = File(exists=True, desc="T1 image normalized into MNI space")
    tfm= File(exists=True, mandatory=True, desc="Transformation matrix to register PET image to T1 space")
    template  = File(desc="Mask on the template")
    warp = File(desc="Warp/deformation volume for NL transform")
    label_type = traits.Str(mandatory=True, desc="Type for label")
    labels = traits.List(desc="label value(s) for label image.")
    label_img  = File(mandatory=True, desc="Mask on the template")
    erode_times = traits.Int(desc="Number of times to erode image", usedefault=True, default=0)
    like_file = File(desc="Target img")
    label_template=traits.Str(usedefault=True,default_value='NA',desc="Template for stereotaxic atlas")
    analysis_space=traits.Str()
    brain_mask = traits.Str(usedefault=True,default_value='NA',desc="Brain mask in T1 native space")
    brain_only = traits.Bool(usedefault=True, default=False, desc="Flag to signal to use brain_mask")
    ones_only = traits.Bool(usedefault=True, default=False, desc="Flag to signal threshold so that label image is only 1s and 0s")
    out_file  = File(desc="Labels in analysis space")

class LabelsOutput(TraitedSpec):
    out_file  = File(desc="Labels in analysis space")

class Labels(BaseInterface):
    input_spec = LabelsInput
    output_spec = LabelsOutput
    _suffix = "_space-"

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _run_interface(self, runtime):
        #1. load label image
        label_img = nib.load(self.inputs.label_img).get_data()
        
        #2. Remove labels not specified by user, if any have been provided
        if self.inputs.labels != [] :
            labels_to_remove =[ i for i in np.unique(label_img) if i not in self.input.labels ]
            for i in labels_to_remove :
                label_img[ label_img == i ] = 0
        
        #3. concatenate all labels to 1
        if self.inputs.ones_only :
            label_img[label_img != 0 ] = 1


        #4. erode all labels
        label_img_eroded=np.zeros(label_img.shape)
        if self.inputs.erode_times != 0 :
            for i in np.unique(label_img) :
                if i != 0 :
                    temp=np.zeros(label_img.shape)
                    temp[ label_img == i ] = 1
                    temp = binary_erosion(temp, iterations=self.inputs.erode_times)
                    label_img_eroded += temp
            label_img=label_img_eroded

        #5.
        if self.inputs.brain_only :
            brain_mask = nib.load(self.inputs.brain_mask).get_data()
            label_img *= brain_mask

        #6. Apply transformation
        transformLabels = ApplyTransforms()
        transformLabels.inputs.input_image = self.inputs.label_img
        transformLabels.inputs.reference_image = self.inputs.like_file
        transformLabels.inputs.transformations = self.inputs.tfm
        transformLabels.inputs.interpolation = 'Nearest'

        #7. Copy to output
        shutil.copy(transformLabels.inputs.warped_image, self.inputs.out_file)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.label_img, self._suffix+self.inputs.analysis_space)
        outputs["out_file"] = self.inputs.out_file #Masks in stereotaxic space
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.label_img, self._suffix+self.inputs.analysis_space)
        return super(Labels, self)._parse_inputs(skip=skip)

"""
.. module:: masking
    :platform: Unix
    :synopsis: Module to create labeled images.
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""

def get_transforms_for_stage(inputnode, label_space, analysis_space, identity):
    if label_space == "stereo" :
        if analysis_space == "t1":
            tfm_node=inputnode
            transform_file="tfm_stx_mri"
            target_file="nativeT1"
        elif analysis_space == "pet":
            tfm_node=inputnode
            transform_file='tfm_stx_pet'
            target_file="pet_volume"
        else :
            tfm_node=identity
            transform_file="out_file"
            target_file="mniT1"
    elif label_space == "t1":
        if analysis_space == "stereo":
            tfm_node=inputnode
            transform_file="tfm_mri_stx"
            target_file="mniT1"
        elif analysis_space == "pet":
            tfm_node=inputnode
            transform_file="tfm_mri_pet"
            target_file="pet_volume"
        else :
            tfm_node=identity
            transform_file="out_file"
            target_file="t1"
    elif label_space == "pet":
        if analysis_space == "stereo":
            tfm_node=inputnode
            transform_file="tfm_pet_stx"
            target_file="mniT1"
        elif analysis_space == "t1":
            tfm_node=inputnode
            transform_file="tfm_pet_mri"
            target_file="nativeT1"
        else :
            tfm_node=identity
            transform_file="out_file"
            target_file="pet"

    return([tfm_node, transform_file, target_file])



def get_workflow(name, infosource, opts):
    '''
        Create workflow to produce labeled images.

        1. Invert T1 Native to MNI 152 transformation
        2. Transform
        4. Transform brain_mask from MNI 152 to T1 native
        5. Create PVC labeled image
        6. Create quantification labeled image
        7. Create results labeled image

        :param name: Name for workflow
        :param infosource: Infosource for basic variables like subject id (sid) and condition id (cid)
        :param datasink: Node in which output data is sent
        :param opts: User options

        :returns: workflow
    '''
    workflow = pe.Workflow(name=name)
    out_list=["pet_brain_mask", "brain_mask",  "results_label_img_t1", "results_label_img_mni" ]
    in_list=["nativeT1","mniT1","brain_mask_stx", "brain_mask_space_mri", "pet_header_json", "pet_volume", "results_labels", "results_label_template","results_label_img", 'tfm_mri_stx','tfm_stx_mri',  "tfm_pet_stx", "tfm_stx_pet",'tfm_mri_stx', "tfm_mri_pet", "tfm_pet_mri", "surf_left", 'surf_right']
    if not opts.pvc_method == None :
        out_list += ["pvc_label_img_t1", "pvc_label_img_mni"]
        in_list += ["pvc_labels", "pvc_label_space", "pvc_label_img","pvc_label_template"]
    if not opts.tka_method == None:
        out_list += ["tka_label_img_t1", "tka_label_img_mni"]
        in_list +=  ["tka_labels", "tka_label_space","tka_label_template","tka_label_img"]
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=in_list), name='inputnode')
    outputnode = pe.Node(niu.IdentityInterface(fields=out_list), name='outputnode')
    #Define empty node for output

    if not opts.pvc_method == None and not opts.pvc_method == None:
        pvc_tfm_node, pvc_tfm_file, pvc_target_file = get_transforms_for_stage( inputnode, opts.pvc_label_space, opts.analysis_space, identity_transform)

    if not opts.tka_method == None:
       tka_tfm_node, tka_tfm_file, tka_target_file = get_transforms_for_stage(  inputnode, opts.tka_label_space, opts.analysis_space, identity_transform)

    results_tfm_node, results_tfm_file, results_target_file = get_transforms_for_stage(  inputnode, opts.results_label_space, opts.analysis_space, identity_transform)

    ###################
    # Brain Mask Node #
    ###################
    if opts.analysis_space == "stereo"  :
        brain_mask_node = pe.Node(niu.IdentityInterface(fields=["output_file"]), "brain_mask")
        workflow.connect(inputnode, "brain_mask_stx", brain_mask_node, "output_file")
        like_file="mniT1"
    elif opts.analysis_space == "t1" :
        brain_mask_node = pe.Node(niu.IdentityInterface(fields=["output_file"]), "brain_mask")
        workflow.connect(inputnode, "brain_mask_t1", brain_mask_node, "output_file")
        like_file="nativeT1"
    elif opts.analysis_space == "pet" :
        brain_mask_node = pe.Node(minc.Resample(), "brain_mask")
        brain_mask_node.inputs.nearest_neighbour_interpolation = True
        workflow.connect(inputnode, "brain_mask_stx", brain_mask_node, "input_file")
        workflow.connect(inputnode, "tfm_stx_pet", brain_mask_node, "transformation")
        workflow.connect(inputnode, "pet_volume", brain_mask_node, "like")
        like_file="pet_volume"
    else :
        print("Error: Analysis space must be one of pet,stereo,t1 but is",opts.analysis_space)
        exit(1)

    #################
    # Surface masks #
    #################
    if opts.use_surfaces:
        if opts.analysis_space != "stereo" :
            surface_left_node = pe.Node(transform_objectCommand(), name="surface_left_node")
            surface_right_node = pe.Node(transform_objectCommand(), name="surface_right_node")
            workflow.connect(inputnode, 'surf_left', surface_left_node, 'in_file')
            workflow.connect(inputnode, 'surf_right', surface_right_node, 'in_file')
            if opts.analysis_space == "t1" :
                workflow.connect(inputnode, "tfm_stx_mri", surface_left_node, 'tfm_file')
                workflow.connect(inputnode, "tfm_stx_mri", surface_right_node, 'tfm_file')
            elif opts.analysis_space == "pet" :
                workflow.connect(inputnode, 'tfm_stx_pet', surface_left_node, 'tfm_file')
                workflow.connect(inputnode, 'tfm_stx_pet', surface_right_node, 'tfm_file')
        else :
            surface_left_node = pe.Node(niu.IdentityInterface(fields=["output_file"]), "surf_left_node")
            surface_right_node = pe.Node(niu.IdentityInterface(fields=["output_file"]), "surf_right_node")
            workflow.connect(inputnode, "surf_left", surface_left_node, "output_file")
            workflow.connect(inputnode, "surf_right", surface_right_node, "output_file")

    resultsLabels = pe.Node(interface=Labels(), name="resultsLabels")
    resultsLabels.inputs.analysis_space = opts.analysis_space
    resultsLabels.inputs.label_type = opts.results_label_type
    resultsLabels.inputs.space = opts.results_label_space
    resultsLabels.inputs.erode_times = opts.results_erode_times
    resultsLabels.inputs.brain_only = opts.results_labels_brain_only
    resultsLabels.inputs.ones_only = opts.results_labels_ones_only
    workflow.connect(inputnode, 'results_labels', resultsLabels, 'labels')
    workflow.connect(inputnode, 'results_label_img', resultsLabels, 'label_img')
    workflow.connect(inputnode, 'results_label_template', resultsLabels, 'label_template')
    workflow.connect(inputnode, like_file, resultsLabels, 'like_file')
    workflow.connect(brain_mask_node,"output_file", resultsLabels, 'brain_mask')
    workflow.connect(results_tfm_node, results_tfm_file, resultsLabels, "")
    
    #Setup node for nonlinear alignment of results template to default (icbm152) template
    if opts.results_label_template != None :
        results_template_norm = pe.Node(interface=reg.nRegRunning(), name="results_template_normalization")
        results_template_norm.inputs.in_target_file = opts.template
        results_template_norm.inputs.in_source_file = opts.results_label_template
        
        results_template_analysis_space = pe.Node(ConcatNLCommand(), name="results_template_analysis_space")
        workflow.connect(results_template_norm, 'out_file_tfm', results_template_analysis_space, 'in_file' )
        workflow.connect(results_template_norm, 'out_file_warp', results_template_analysis_space, 'in_warp' )
        workflow.connect(results_tfm_node, results_tfm_file, results_template_analysis_space, 'in_file_2' )
                
        workflow.connect(results_template_analysis_space, 'out_file', resultsLabels, 'nAtlasMNI')
        workflow.connect(results_template_analysis_space, 'out_warp', resultsLabels, 'warp')
        workflow.connect(results_template_norm, 'out_file_img', resultsLabels, 'template')

    if not opts.pvc_method == None and not opts.pvc_method == None:
        pvcLabels = pe.Node(interface=Labels(), name="pvcLabels")
        pvcLabels.inputs.analysis_space = opts.analysis_space
        pvcLabels.inputs.label_type = opts.pvc_label_type
        pvcLabels.inputs.space = opts.pvc_label_space
        pvcLabels.inputs.erode_times = opts.pvc_erode_times
        pvcLabels.inputs.brain_only = opts.pvc_labels_brain_only
        pvcLabels.inputs.ones_only = opts.pvc_labels_ones_only
        workflow.connect(inputnode, 'pvc_labels', pvcLabels, 'labels')
        workflow.connect(inputnode, 'pvc_label_img', pvcLabels, 'label_img')
        workflow.connect(inputnode, like_file, pvcLabels, 'like_file')
        workflow.connect(brain_mask_node, "output_file", pvcLabels, 'brain_mask')
        workflow.connect(pvc_tfm_node, pvc_tfm_file, pvcLabels, "")


        if opts.pvc_label_template != None :
            pvc_template_norm = pe.Node(interface=reg.nRegRunning(), name="pvc_template_normalization")
            pvc_template_norm.inputs.in_target_file = opts.template
            pvc_template_norm.inputs.in_source_file = opts.pvc_label_template
            
            pvc_template_analysis_space = pe.Node(ConcatNLCommand(), name="pvc_template_analysis_space")
            workflow.connect(pvc_template_norm, 'out_file_tfm', pvc_template_analysis_space, 'in_file' )
            workflow.connect(pvc_template_norm, 'out_file_warp', pvc_template_analysis_space, 'in_warp' )
            workflow.connect(pvc_tfm_node, pvc_tfm_file, pvc_template_analysis_space, 'in_file_2' )
                    
            workflow.connect(pvc_template_analysis_space, 'out_file', pvcLabels, 'nAtlasMNI')
            workflow.connect(pvc_template_analysis_space, 'out_warp', pvcLabels, 'warp')
            workflow.connect(pvc_template_norm, 'out_file_img', pvcLabels, 'template')


    if not opts.tka_method == None :
        tkaLabels = pe.Node(interface=Labels(), name="tkaLabels")
        tkaLabels.inputs.analysis_space = opts.analysis_space
        tkaLabels.inputs.label_type = opts.tka_label_type
        tkaLabels.inputs.space = opts.tka_label_space
        tkaLabels.inputs.erode_times = opts.tka_erode_times
        tkaLabels.inputs.brain_only = opts.tka_labels_brain_only
        tkaLabels.inputs.ones_only = opts.tka_labels_ones_only
        workflow.connect(inputnode, 'tka_labels', tkaLabels, 'labels')
        workflow.connect(inputnode, 'tka_label_img', tkaLabels, 'label_img')
        workflow.connect(inputnode, like_file, tkaLabels, 'like_file')
        workflow.connect(brain_mask_node, "output_file", tkaLabels, 'brain_mask')
        workflow.connect(tka_tfm_node, tka_tfm_file, tkaLabels, "")


        if opts.tka_label_template != None :
            tka_template_norm = pe.Node(interface=reg.nRegRunning(), name="tka_template_normalization")
            tka_template_norm.inputs.in_source_file = opts.template
            tka_template_norm.inputs.in_target_file = opts.tka_label_template
            
            tka_template_analysis_space = pe.Node(ConcatNLCommand(), name="tka_template_analysis_space")
            workflow.connect(tka_template_norm, 'out_file_tfm', tka_template_analysis_space, 'in_file' )
            workflow.connect(tka_template_norm, 'out_file_warp', tka_template_analysis_space, 'in_warp' )
            workflow.connect(tka_tfm_node, tka_tfm_file, tka_template_analysis_space, 'in_file_2' )
                    
            workflow.connect(tka_template_analysis_space, 'out_file', tkaLabels, 'nAtlasMNI')
            workflow.connect(tka_template_analysis_space, 'out_warp', tkaLabels, 'warp')
            workflow.connect(tka_template_norm, 'out_file_img', tkaLabels, 'template')

    return(workflow)
