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
#from nipype.interfaces.base import Info
from nipype.interfaces.utility import Rename
from os.path import splitext
import nipype.interfaces.minc as minc
from nipype.interfaces.minc import Calc as CalcCommand
from nipype.interfaces.minc import Blur as SmoothCommand
from nipype.interfaces.minc import Resample as ResampleCommand
from Extra.xfmOp import InvertCommand
from Extra.morphomat import MorphCommand
from Extra.info import StatsCommand
from Extra.resample import param2xfmCommand
from Extra.obj import *
import Registration.registration as reg
import pyminc.volumes.factory as pyminc

class LabelsInput(BaseInterfaceInputSpec):
    mniT1 = File(exists=True, desc="T1 image normalized into MNI space")
    petT1 = File(exists=True, desc="PET image transformed into PET space")
    LinXfm= File(exists=True, mandatory=True, desc="Transformation matrix to register PET image to T1 space")
    nLinAtlasMNIXfm = traits.Str(default='', desc="Non-linear transformation matrix to register atlas template image into MNI space")
    label_type = traits.Str(mandatory=True, desc="Type for label")
    labels = traits.List(desc="label value(s) for label image.")
    #_spaces = ['native', 'stereo', 'other']
    #space = traits.Enum(*_spaces, mandatory=True, desc="Coordinate space of the label")
    space = traits.Str(desc="Coordinate space of the label")
    analysis_space = traits.Str(mandatory=True, desc="Analysis space")
    label_img  = File(mandatory=True, desc="Mask on the template")
    erode_times = traits.Int(desc="Number of times to erode image", usedefault=True, default=0)
    mni2target = File(desc="Transformation from stereotaxic to analysis space")
    like_file = File(desc="Target img") 
    label_template=traits.Str(usedefault=True,default_value='NA',desc="Template for stereotaxic atlas")
    brainmask = traits.Str(usedefault=True,default_value='NA',desc="Brain mask in T1 native space")
    brain_only = traits.Bool(usedefault=True, default=False, desc="Flag to signal to use brainmask")
    ones_only = traits.Bool(usedefault=True, default=False, desc="Flag to signal threshold so that label image is only 1s and 0s")
    surf = File(desc="Obj surface")
    out_file  = File(desc="Labels in analysis space")

class LabelsOutput(TraitedSpec):
    out_file  = File(desc="Labels in analysis space")
    nLinAtlasMNIXfm = traits.Str(desc="Non-linear transformation matrix to register atlas template image into MNI space")

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
        print(self.inputs) 
        self.inputs.out_file = self._gen_output(self.inputs.label_img, self._suffix+self.inputs.analysis_space) 

        tmpDir = os.getcwd() + os.sep + 'tmp_label'  #tempfile.mkdtemp()
        os.mkdir(tmpDir)

        out_file_1 =temp_mask = tmpDir+"/mask.mnc"
        temp_mask_clean = tmpDir+"/mask_clean.mnc"
        if self.inputs.labels == [] : 
            mask= pyminc.volumeFromFile(self.inputs.label_img)
            mask_flat=mask.data.flatten()
            labels=[ str(int(round(i))) for i in np.unique(mask_flat) ]
            if '0' in labels :  labels.remove('0')
            print("Labels: ", labels)
        else : 
            labels = self.inputs.labels
        # 1) Select Labels
        run_calc = minc.Calc() #Extract the desired label from the atlas using minccalc.
        run_calc.inputs.input_files = self.inputs.label_img #The ANIMAL or CIVET classified atlas
        run_calc.inputs.output_file = temp_mask  #Output mask with desired label
        run_calc.inputs.expression = " || ".join([ '(A[0] > ' + str(label) + '-0.1 && A[0] < '+str(label)+'+ 0.1 )' for label in  labels ]) + ' ? A[0] : 0'  
        run_calc.run()
        print("Select Labels:\n", run_calc.cmdline)

        # 2) Erode
        if int(self.inputs.erode_times) > 0:
            run_mincmorph = MorphCommand()
            run_mincmorph.inputs.in_file = temp_mask
            run_mincmorph.inputs.out_file = temp_mask_clean
            run_mincmorph.inputs.successive='E' * self.inputs.erode_times 
            run_mincmorph.run()
            out_file_1 = temp_mask_clean

        out_file_1 = self.inputs.out_file
       
        # 3) Co-registration
        if self.inputs.space == "stereo" and self.inputs.label_type == "atlas-template"    :
            if self.inputs.nLinAtlasMNIXfm == '':
                sourceToModel_xfm = os.getcwd() + os.sep + 'template2mni.xfm'
                run_nlinreg = reg.nLinRegRunning()
                run_nlinreg.inputs.in_source_file = self.inputs.label_template
                run_nlinreg.inputs.in_target_file = self.inputs.mniT1  
                run_nlinreg.inputs.out_file_xfm = sourceToModel_xfm # xfm file for the transformation from template to subject stereotaxic
                run_nlinreg.run()

                mni2target = minc.XfmConcat()
                mni2target.inputs.input_file_1 = sourceToModel_xfm
                mni2target.inputs.input_file_2 = self.inputs.mni2target 
                mni2target.run()
                xfm = mni2target.inputs.out_file
                self.inputs.nLinAtlasMNIXfm=mni2target.inputs.output_file
            else :
                #sourceToModel_xfm=self.inputs.nLinAtlasMNIXfm
                xfm=self.inputs.nLinAtlasMNIXfm
        else :
            xfm = self.inputs.LinXfm
        
        # 4) Apply transformation 
        like_file = self.inputs.like_file
        base=splitext(out_file_1)
        out_file_2=base[0]+self.inputs.analysis_space+base[1]

        run_resample = minc.Resample() 
        run_resample.inputs.input_file = self.inputs.label_img
        run_resample.inputs.output_file = out_file_2
        run_resample.inputs.like = like_file
        run_resample.inputs.transformation = xfm
        run_resample.inputs.nearest_neighbour_interpolation = True
        run_resample.run()

        label = run_resample.inputs.output_file

        #Copy to output
        shutil.copy(label, self.inputs.out_file)
        
        print(self.inputs.brainmask)
        # 6) Mask brain for T1 and MNI labels
        if self.inputs.brain_only :
            temp_mask = tmpDir+"/mask.mnc"
            run_calc = minc.Calc() #Extract the desired label from the atlas using minccalc.
            run_calc.inputs.input_files = [ label, self.inputs.brainmask] 
            run_calc.inputs.output_file = temp_mask  #Output mask with desired label
            run_calc.inputs.expression = " A[1] == 1 ? A[0] : 0 " 
            run_calc.clobber = True
            run_calc.run()
            #shutil.copy(temp_mask, label)
            shutil.copy(temp_mask,  self.inputs.out_file)
            label = self.inputs.out_file
            print "Warning: masking labeled image with brain mask."
            print "Label: ", label
        if self.inputs.ones_only :
            temp_mask = tmpDir+"/mask.mnc"
            run_calc = minc.Calc() #Extract the desired label from the atlas using minccalc.
            run_calc.inputs.input_files = [ label ] #The ANIMAL or CIVET classified atlas
            run_calc.inputs.output_file = temp_mask  #Output mask with desired label
            run_calc.inputs.expression = " A[0] > 0.1 ? 1 : 0 " 
            run_calc.clobber = True
            run_calc.run()
            shutil.copy(temp_mask, self.inputs.out_file)
	
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file): 
            self.inputs.out_file = self._gen_output(self.inputs.label_img, self._suffix+self.inputs.analysis_space) 
        outputs["out_file"] = self.inputs.out_file #Masks in stereotaxic space
        outputs["nLinAtlasMNIXfm"] = self.inputs.nLinAtlasMNIXfm 
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        return super(Labels, self)._parse_inputs(skip=skip)

"""
.. module:: masking
    :platform: Unix
    :synopsis: Module to create labeled images. 
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""

def get_transforms_for_stage(MNIT1, MNIPET, inputnode, label_space, analysis_space, identity):
    if label_space == "stereo" :  
        if analysis_space == "t1":
            tfm_node=MNIT1
            transform_file="output_file"
            target_file="nativeT1"
        elif analysis_space == "pet":
            tfm_node=MNIPET
            transform_file="output_file"
            target_file="pet_volume"
        else :
            tfm_node=identity
            transform_file="out_file"
            target_file="mniT1"
    elif label_space == "t1": 
        if analysis_space == "stereo":
            tfm_node=inputnode
            transform_file="LinT1MNIXfm"
            target_file="mniT1"
        elif analysis_space == "pet":
            tfm_node=inputnode
            transform_file="LinT1PETXfm"
            target_file="pet_volume"
        else :
            tfm_node=identity
            transform_file="out_file"
            target_file="t1"
    elif label_space == "pet":
        if analysis_space == "stereo":
            tfm_node=inputnode
            transform_file="LinPETMNIXfm"
            target_file="mniT1"
        elif analysis_space == "t1":
            tfm_node=inputnode
            transform_file="LinPETT1Xfm"
            target_file="nativeT1"
        else :
            tfm_node=identity
            transform_file="out_file"
            target_file="pet"

    #print label_space, "to", analysis_space
    #print "1", tfm_node, transform_file, transform_to
    #print "2", tfm_node, transform_file, transform_to
    return([tfm_node, transform_file, target_file])



def get_workflow(name, infosource, opts):
    '''
        Create workflow to produce labeled images.

        1. Invert T1 Native to MNI 152 transformation
        2. Transform
        4. Transform brainmask from MNI 152 to T1 native
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
    out_list=["pet_brainmask", "brain_mask",  "results_label_img_t1", "results_label_img_mni" ]
    in_list=["nativeT1","mniT1","brainmask", "pet_header_json", "pet_volume", "results_labels", "results_label_template","results_label_img", 'LinT1MNIXfm',  "LinPETMNIXfm", "LinMNIPETXfm", "LinT1PETXfm", "LinPETT1Xfm", "surf_left", 'surf_right']
    if not opts.nopvc: 
        out_list += ["pvc_label_img_t1", "pvc_label_img_mni"]
        in_list += ["pvc_labels", "pvc_label_space", "pvc_label_img","pvc_label_template"]
    if not opts.tka_method == None: 
        out_list += ["tka_label_img_t1", "tka_label_img_mni"]
        in_list +=  ["tka_labels", "tka_label_space","tka_label_template","tka_label_img"]
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=in_list), name='inputnode')
    outputnode = pe.Node(niu.IdentityInterface(fields=out_list), name='outputnode')
    #Define empty node for output

    #Create Identity Transform
    identity_transform = pe.Node(param2xfmCommand(), name="identity_transform")
    identity_transform.inputs.translation="0 0 0"
    identity_transform.inputs.rotation="0 0 0"
    identity_transform.inputs.scales="1 1 1"

    MNIT1 = pe.Node(interface=minc.XfmInvert(), name="MNIT1")
    workflow.connect(inputnode, 'LinT1MNIXfm',MNIT1 , 'input_file')
    MNIPET = pe.Node(interface=minc.XfmInvert(), name="MNIPET")
    workflow.connect(inputnode, 'LinPETMNIXfm',MNIPET , 'input_file')

    if not opts.nopvc and not opts.pvc_method == None:
        pvc_tfm_node, pvc_tfm_file, pvc_target_file = get_transforms_for_stage( MNIT1, MNIPET, inputnode, opts.pvc_label_space, opts.analysis_space, identity_transform)
        
    if not opts.tka_method == None:
       tka_tfm_node, tka_tfm_file, tka_target_file = get_transforms_for_stage( MNIT1, MNIPET, inputnode, opts.tka_label_space, opts.analysis_space, identity_transform)
    
    results_tfm_node, results_tfm_file, results_target_file = get_transforms_for_stage( MNIT1, MNIPET, inputnode, opts.results_label_space, opts.analysis_space, identity_transform)
    
    ###################
    # Brain Mask Node #
    ###################
    if opts.analysis_space != "stereo"  :
        brain_mask_node = pe.Node(minc.Resample(), "brain_mask")
        brain_mask_node.inputs.nearest_neighbour_interpolation = True
        #brain_mask_node.inputs.output_file="brain_mask_space-"+opts.analysis_space+".mnc" 

        workflow.connect(inputnode, "brainmask", brain_mask_node, "input_file")
        if opts.analysis_space == "t1" :
            workflow.connect(MNIT1, "output_file", brain_mask_node, "transformation")
            like_file="nativeT1"
            workflow.connect(inputnode, "nativeT1", brain_mask_node, "like")
        elif opts.analysis_space == "pet" :
            workflow.connect(MNIPET, "output_file", brain_mask_node, "transformation")
            workflow.connect(inputnode, "pet_volume", brain_mask_node, "like")
            like_file="pet_volume"
        else :
            print("Error: Analysis space must be one of pet,stereo,t1 but is",opts.analysis_space)
            exit(1)
    else :
        brain_mask_node = pe.Node(niu.IdentityInterface(fields=["output_file"]), "brain_mask")
        workflow.connect(inputnode, "brainmask", brain_mask_node, "output_file")
        like_file="mniT1"

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
                workflow.connect(MNIT1, 'output_file', surface_left_node, 'tfm_file')
                workflow.connect(MNIT1, 'output_file', surface_right_node, 'tfm_file')
            elif opts.analysis_space == "pet" :
                workflow.connect(MNIPET, 'output_file', surface_left_node, 'tfm_file')
                workflow.connect(MNIPET, 'output_file', surface_right_node, 'tfm_file')
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
    workflow.connect(brain_mask_node,"output_file", resultsLabels, 'brainmask')
    workflow.connect(results_tfm_node, results_tfm_file, resultsLabels, "LinXfm")

    if not opts.nopvc and not opts.pvc_method == None:
        pvcLabels = pe.Node(interface=Labels(), name="pvcLabels")
        pvcLabels.inputs.analysis_space = opts.analysis_space
        pvcLabels.inputs.label_type = opts.pvc_label_type
        pvcLabels.inputs.space = opts.pvc_label_space
        pvcLabels.inputs.erode_times = opts.pvc_erode_times
        pvcLabels.inputs.brain_only = opts.pvc_labels_brain_only
        pvcLabels.inputs.ones_only = opts.pvc_labels_ones_only
        workflow.connect(inputnode, 'pvc_labels', pvcLabels, 'labels')
        workflow.connect(inputnode, 'pvc_label_img', pvcLabels, 'label_img')
        workflow.connect(inputnode, 'pvc_label_template', pvcLabels, 'label_template')
        workflow.connect(inputnode, like_file, pvcLabels, 'like_file')
        workflow.connect(brain_mask_node, "output_file", pvcLabels, 'brainmask')
        workflow.connect(pvc_tfm_node, pvc_tfm_file, pvcLabels, "LinXfm")
    if not opts.tka_method == None:
        tkaLabels = pe.Node(interface=Labels(), name="tkaLabels")
        tkaLabels.inputs.analysis_space = opts.analysis_space
        tkaLabels.inputs.label_type = opts.tka_label_type
        tkaLabels.inputs.space = opts.tka_label_space
        tkaLabels.inputs.erode_times = opts.tka_erode_times
        tkaLabels.inputs.brain_only = opts.tka_labels_brain_only
        tkaLabels.inputs.ones_only = opts.tka_labels_ones_only
        workflow.connect(inputnode, 'tka_labels', tkaLabels, 'labels')
        workflow.connect(inputnode, 'tka_label_img', tkaLabels, 'label_img')
        workflow.connect(inputnode, 'tka_label_template', tkaLabels, 'label_template')
        workflow.connect(inputnode, like_file, tkaLabels, 'like_file')
        workflow.connect(brain_mask_node, "output_file", tkaLabels, 'brainmask')
        workflow.connect(tka_tfm_node, tka_tfm_file, tkaLabels, "LinXfm")
   
    return(workflow)
