import os
import numpy as np
import tempfile
import shutil
import pickle
import ntpath
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
import nipype.interfaces.minc as minc
import Registration.registration as reg
import pyminc.volumes.factory as pyminc
import nibabel as nib
import SimpleITK as sitk
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from arg_parser import file_dir
from nipype.interfaces.utility import Rename
from Extra.utils import splitext, gz
from Extra.xfmOp import InvertCommand
from Extra.morphomat import MorphCommand
from Extra.info import StatsCommand
from Extra.resample import param2xfmCommand
from Extra.obj import *
from scipy.ndimage.morphology import binary_erosion
from Registration.ants_mri_normalize import APPIANRegistration, APPIANApplyTransforms,APPIANConcatenateTransforms


icbm_default_brain=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_t1_tal_nlin_asym_09c_mask.nii"

class IdentityTransformInput(BaseInterfaceInputSpec):
    out_file  = File(desc="Labels in analysis space")

class IdentityTransformOutput(TraitedSpec):
    out_file  = File(desc="Labels in analysis space")

class IdentityTransform(BaseInterface):
    input_spec = IdentityTransformInput
    output_spec = IdentityTransformOutput

    def _gen_output(self):
        dname = os.getcwd()
        return dname+ os.sep+'identity_transform.txt'

    def _run_interface(self, runtime):
        self.inputs.out_file = self._gen_output() 
        identity = sitk.Transform(3, sitk.sitkIdentity)
        sitk.WriteTransform(identity, str(self.inputs.out_file))
        return runtime

    def _list_outputs(self):
	outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file


class LabelsInput(BaseInterfaceInputSpec):
    #tfm= traits.File(desc="Transformation matrix to register PET image to T1 space") #
    transform_3 = traits.File( desc="Transformation matrix to register PET image to T1 space") #
    transform_2 = traits.File( desc="Transformation matrix to register PET image to T1 space") #
    transform_1 = traits.File( desc="Transformation matrix to register PET image to T1 space") #
    warp = traits.File(desc="Warp/deformation volume for NL transform")
    labels = traits.List(desc="label value(s) for label image.")
    label_img  = traits.File(mandatory=True, desc="Mask on the template")
    erode_times = traits.Int(desc="Number of times to erode image", usedefault=True, default=0)
    like_file = traits.File(desc="Target img")
    analysis_space=traits.Str()
    brain_mask = traits.Str(usedefault=True,default_value='NA',desc="Brain mask in T1 native space")
    brain_only = traits.Bool(usedefault=True, default=False, desc="Flag to signal to use brain_mask")
    ones_only = traits.Bool(usedefault=True, default=False, desc="Flag to signal threshold so that label image is only 1s and 0s")
    out_file  = traits.File(desc="Labels in analysis space")

class LabelsOutput(TraitedSpec):
    out_file  = traits.File(desc="Labels in analysis space")

class Labels(BaseInterface):
    input_spec = LabelsInput
    output_spec = LabelsOutput
    _suffix = "_space-"

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _run_interface(self, runtime):
        #1. load label image
        img = nib.load(self.inputs.label_img)
        label_img = img.get_data()
        
        print("1", np.sum(label_img)) 
        print(self.inputs.labels)
        _labels =[ int(i) for i in self.inputs.labels ]
        #2. Remove labels not specified by user, if any have been provided
        if self.inputs.labels != [] :
            labels_to_remove =[ i for i in np.unique(label_img) if int(i) not in _labels ]
            for i in labels_to_remove :
                label_img[ label_img == i ] = 0
        print(np.unique(label_img))
        print("2", np.sum(label_img)) 
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

        tmp_label_img  = nib.Nifti1Image(label_img, img.get_affine())
        tmp_label_img.to_filename("tmp_label_img.nii")

        #6. Apply transformation
        transformLabels = APPIANApplyTransforms()
        transformLabels.inputs.input_image ="tmp_label_img.nii"
        transformLabels.inputs.reference_image = self.inputs.like_file
        transformLabels.inputs.transform_1 = self.inputs.transform_1
        transformLabels.inputs.transform_2 = self.inputs.transform_2
        transformLabels.inputs.transform_3 = self.inputs.transform_3
        transformLabels.inputs.interpolation = 'NearestNeighbor'
        transformLabels.run()
        output_image = transformLabels._list_outputs()['output_image']
        print(transformLabels._list_outputs() ) 
        #7. Copy to output

        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.label_img, self._suffix+self.inputs.analysis_space)
        print(output_image, self.inputs.out_file)
        if '.gz' in splitext(self.inputs.out_file)[1] : 
            print('Gzip')
            gz(output_image, self.inputs.out_file)
            nib.load(output_image)
            nib.load(self.inputs.out_file)
        else : 
            print('Copy')
            shutil.copy(output_image, self.inputs.out_file)

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
    if label_space == analysis_space :
        tfm_node=[identity]
        transform_file=["out_file"]
    else : 
        if label_space == "stereo" :
            if analysis_space == "t1":
                transform_file=["tfm_stx_mri"]
            elif analysis_space == "pet":
                transform_file=['tfm_mri_pet', 'tfm_stx_mri']
        elif label_space == "t1":
            if analysis_space == "stereo":
                transform_file=["tfm_mri_stx"]
            elif analysis_space == "pet":
                transform_file=["tfm_mri_pet"]
        elif label_space == "pet":
            if analysis_space == "stereo":
                transform_file=["tfm_mri_stx", "tfm_pet_mri"]
            elif analysis_space == "t1":
                transform_file=["tfm_pet_mri"]

        tfm_node=[inputnode]*len(transform_file)

    return([tfm_node, transform_file])

def set_label_node(analysis_space, label_space,  erode_times, brain_only, ones_only, tfm_node_list, tfm_file_list,label_template, default_template, normalization_type, like_file, brain_mask_node, workflow,inputnode, kind):
    LabelNode = pe.Node(interface=Labels(), name=kind+"Labels")
    LabelNode.inputs.analysis_space = analysis_space
    LabelNode.inputs.erode_times = erode_times
    LabelNode.inputs.brain_only = brain_only
    LabelNode.inputs.ones_only = ones_only
    workflow.connect(inputnode, kind+'_labels', LabelNode, 'labels')
    workflow.connect(inputnode, kind+'_label_img', LabelNode, 'label_img')
    workflow.connect(inputnode, like_file, LabelNode, 'like_file')

    if label_space == 'pet':
        label_brain_mask_node = brain_mask_node
        label_brain_mask_file = 'output_image'
    elif label_space == 'stereo' :
        label_brain_mask_node = inputnode
        label_brain_mask_file = 'brain_mask_space_stx'
    elif label_space == 'mri' :
        label_brain_mask_node = inputnode
        label_brain_mask_file = 'brain_mask_space_mri'

    workflow.connect(label_brain_mask_node, label_brain_mask_file, LabelNode, 'brain_mask')
  
    #Setup node for nonlinear alignment of results template to default (icbm152) template
    if label_template != None :
        template_norm = pe.Node(interface=APPIANRegistration(), name="template_normalization")
        template_norm.inputs.interpolation='NearestNeighbor'
        template_norm.inputs.normalization_type = normalization_type
        workflow.connect(inputnode, kind+'_label_template', template_norm, 'moving_image')
        template_norm.inputs.fixed_image = default_template
        template_norm.inputs.fixed_image_mask = icbm_default_brain
        tfm_node_list.append(template_norm)
        if normalization_type == 'nl' :
            template_tfm = 'composite_transform'
        else : 
            template_tfm = 'out_matrix'
        tfm_file_list.append(template_tfm)
    
    tfm_index=1
    print(tfm_node_list)
    print(tfm_file_list)
    for node, tfm in zip(tfm_node_list, tfm_file_list) :
        print(node, tfm)
        workflow.connect(node, tfm, LabelNode,'transform_'+str(tfm_index))
        tfm_index += 1
    return LabelNode

def get_workflow(name, infosource, opts):
    '''
        Create workflow to produce labeled images.

        :param name: Name for workflow
        :param infosource: Infosource for basic variables like subject id (sid) and condition id (cid)
        :param datasink: Node in which output data is sent
        :param opts: User options

        :returns: workflow
    '''
    workflow = pe.Workflow(name=name)
    out_list=["pet_brain_mask", "brain_mask",  "results_label_img_t1", "results_label_img_mni" ]
    in_list=["mri_space_nat","mri_space_stx","brain_mask_space_stx", "brain_mask_space_mri", "pet_header_json", "pet_volume", "results_labels", "results_label_template","results_label_img", 'tfm_mri_stx','tfm_stx_mri',  "tfm_pet_stx", "tfm_stx_pet",'tfm_mri_stx', "tfm_mri_pet", "tfm_pet_mri", "surf_left", 'surf_right']
    if not opts.pvc_method == None :
        out_list += ["pvc_label_img_t1", "pvc_label_img_mni"]
        in_list += ["pvc_labels", "pvc_label_space", "pvc_label_img","pvc_label_template"]
    if not opts.tka_method == None:
        out_list += ["tka_label_img_t1", "tka_label_img_mni"]
        in_list +=  ["tka_labels", "tka_label_space","tka_label_template","tka_label_img"]
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=in_list), name='inputnode')
    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=out_list), name='outputnode')
    
    identity_transform = pe.Node(IdentityTransform(), name="identity_transform")

    if opts.normalization_type == 'nl' :
        template_tfm='composite_transform'
    else :
        template_tfm='out_matrix'


    if not opts.pvc_method == None and not opts.pvc_method == None:
        pvc_tfm_node, pvc_tfm_file = get_transforms_for_stage(inputnode, opts.pvc_label_space, opts.analysis_space, identity_transform)

    if not opts.tka_method == None:
       tka_tfm_node, tka_tfm_file = get_transforms_for_stage(inputnode, opts.tka_label_space, opts.analysis_space, identity_transform)

    results_tfm_node, results_tfm_file = get_transforms_for_stage(inputnode, opts.results_label_space, opts.analysis_space, identity_transform)
    
    ###################
    # Brain Mask Node #
    ###################
    if opts.analysis_space == "stereo"  :
        brain_mask_node = pe.Node(niu.IdentityInterface(fields=["output_file"]), "brain_mask")
        workflow.connect(inputnode, "brain_mask_space_stx", brain_mask_node, "output_file")
        like_file="mri_space_stx"
    elif opts.analysis_space == "t1" :
        brain_mask_node = pe.Node(niu.IdentityInterface(fields=["output_file"]), "brain_mask")
        workflow.connect(inputnode, "brain_mask_space_mri", brain_mask_node, "output_file")
        like_file="mri_space_nat"
    elif opts.analysis_space == "pet" :
        brain_mask_node = pe.Node(APPIANApplyTransforms(), "brain_mask_space_pet")
        workflow.connect(inputnode, 'brain_mask_space_stx', brain_mask_node, 'input_image')
        workflow.connect(inputnode, "tfm_stx_mri", brain_mask_node, 'transform_3')
        workflow.connect(inputnode, "tfm_mri_pet", brain_mask_node, 'transform_2')
        workflow.connect(inputnode, 'pet_volume', brain_mask_node, 'reference_image')
        brain_mask_node.inputs.interpolation = 'NearestNeighbor'
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
   
    print(results_tfm_file)
    resultsLabels = set_label_node(opts.analysis_space, opts.results_label_space, opts.results_erode_times, opts.results_labels_brain_only, opts.results_labels_ones_only, results_tfm_node, results_tfm_file, opts.results_label_template, opts.template, opts.normalization_type,like_file, brain_mask_node,workflow,inputnode, "results")

    if not opts.pvc_method == None :
        pvcLabels = set_label_node(opts.analysis_space,opts.pvc_label_space, opts.pvc_erode_times, opts.pvc_labels_brain_only, opts.pvc_labels_ones_only, pvc_tfm_node, pvc_tfm_file, opts.pvc_label_template, opts.template, opts.normalization_type,like_file, brain_mask_node,workflow,inputnode, "pvc")

        
    if not opts.tka_method == None :
        tkaLabels = set_label_node(opts.analysis_space, opts.tka_label_space, opts.tka_erode_times, opts.tka_labels_brain_only, opts.tka_labels_ones_only, tka_tfm_node, tka_tfm_file, opts.tka_label_template, opts.template, opts.normalization_type, like_file, brain_mask_node,workflow,inputnode, "tka")




    return(workflow)
