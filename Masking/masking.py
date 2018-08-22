import os
import numpy as np
import tempfile
import shutil
import pickle
import ntpath 

from pyminc.volumes.factory import *
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
#from nipype.interfaces.base import Info
from nipype.interfaces.utility import Rename

import nipype.interfaces.minc as minc
from nipype.interfaces.minc import Calc as CalcCommand
from nipype.interfaces.minc import Blur as SmoothCommand
from nipype.interfaces.minc import Resample as ResampleCommand
from Extra.xfmOp import InvertCommand
from Extra.morphomat import MorphCommand
from Extra.info import StatsCommand
import Registration.registration as reg

class LabelsInput(BaseInterfaceInputSpec):
    nativeT1 = File(exists=True, mandatory=True, desc="Native T1 image")
    mniT1 = File(exists=True, mandatory=True, desc="T1 image normalized into MNI space")
    LinMNIT1Xfm = File(exists=True, mandatory=True, desc="Inverted transformation matrix to register T1 image into MNI space")
    LinT1MNIXfm = File(exists=True, mandatory=True, desc="Transformation matrix to register T1 image into MNI space")
    nLinAtlasMNIXfm = traits.Str(default='', desc="Non-linear transformation matrix to register atlas template image into MNI space")
    labels = traits.List(desc="label value(s) for label image.")
    #_spaces = ['native', 'icbm152', 'other']
    #space = traits.Enum(*_spaces, mandatory=True, desc="Coordinate space of the label")
    space = traits.Str(desc="Coordinate space of the label")
    label_img  = File( desc="Mask on the template")
    erode_times = traits.Int(desc="Number of times to erode image", usedefault=True, default=0)
    LabelsMNI = File(desc="Reference mask in MNI space")
    LabelsT1  = File(desc="Reference mask in the T1 native space")
    
    label_template=traits.Str(usedefault=True,default_value='NA',desc="Template for stereotaxic atlas")
    brainmask_t1 = traits.Str(usedefault=True,default_value='NA',desc="Brain mask in T1 native space")
    brainmask_mni = traits.Str(usedefault=True,default_value='NA',desc="Brain mask in MNI space")
    brain_only = traits.Bool(usedefault=True, default=False, desc="Flag to signal to use brainmask")
    ones_only = traits.Bool(usedefault=True, default=False, desc="Flag to signal threshold so that label image is only 1s and 0s")

class LabelsOutput(TraitedSpec):
    LabelsMNI  = File(desc="Reference mask in MNI space")
    LabelsT1  = File( desc="Reference mask in the T1 native space")
    nLinAtlasMNIXfm = traits.Str(desc="Non-linear transformation matrix to register atlas template image into MNI space")

class Labels(BaseInterface):
    input_spec = LabelsInput
    output_spec = LabelsOutput
    _suffix = "_label"

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.LabelsT1): 
            self.inputs.LabelsT1 = self._gen_output(self.inputs.nativeT1, self._suffix+'T1') 
        if not isdefined(self.inputs.LabelsMNI): 
            self.inputs.LabelsMNI = self._gen_output(self.inputs.nativeT1, self._suffix+'MNI')
        tmpDir = os.getcwd() + os.sep + 'tmp_label'  #tempfile.mkdtemp()
        os.mkdir(tmpDir)

        out_file_1 =temp_mask = tmpDir+"/mask.mnc"
        temp_mask_clean = tmpDir+"/mask_clean.mnc"

        # 1) Select Labels
        run_calc = minc.Calc() #Extract the desired label from the atlas using minccalc.
        run_calc.inputs.input_files = self.inputs.label_img #The ANIMAL or CIVET classified atlas
        run_calc.inputs.output_file = temp_mask  #Output mask with desired label
        run_calc.inputs.expression = " || ".join([ '(A[0] > ' + str(label) + '-0.1 && A[0] < '+str(label)+'+ 0.1 )' for label in self.inputs.labels ]) + ' ? A[0] : 0'  
        run_calc.run()
        print("Select Labels:\n", run_calc.cmdline)

        #shutil.copy(self.inputs.label_img, '/data1/projects/scott/' + os.path.basename(self.inputs.label_img) )
        #shutil.copy(temp_mask, '/data1/projects/scott/morph_' + os.path.basename(self.inputs.label_img) )
        # 2) Erode
        if int(self.inputs.erode_times) > 0:
            run_mincmorph = MorphCommand()
            run_mincmorph.inputs.in_file = temp_mask
            run_mincmorph.inputs.out_file = temp_mask_clean
            run_mincmorph.inputs.successive='E' * self.inputs.erode_times 
            run_mincmorph.run()
            out_file_1 = temp_mask_clean

        #Copy temp_mask[_clean] to first output
        if self.inputs.space == 'native': 
            shutil.copy(out_file_1, self.inputs.LabelsT1)
            out_file_1 = self.inputs.LabelsT1
        elif self.inputs.space == 'icbm152': 
            shutil.copy(out_file_1, self.inputs.LabelsMNI)
            out_file_1 = self.inputs.LabelsMNI
        
        # 3) Co-registration
        if self.inputs.space == "other":
            if self.inputs.nLinAtlasMNIXfm == '':
                sourceToModel_xfm = os.getcwd() + os.sep + 'template2mni.xfm'
                run_nlinreg = reg.nLinRegRunning()
                run_nlinreg.inputs.in_source_file = self.inputs.label_template
                run_nlinreg.inputs.in_target_file = self.inputs.mniT1  #self.inputs.model
                run_nlinreg.inputs.out_file_xfm = sourceToModel_xfm # xfm file for the transformation from template to subject stereotaxic
                run_nlinreg.run()
                self.inputs.nLinAtlasMNIXfm=sourceToModel_xfm
            else :
                sourceToModel_xfm=self.inputs.nLinAtlasMNIXfm

        # 4) Apply transformation 
        if self.inputs.space == "icbm152":  
            xfm = self.inputs.LinMNIT1Xfm
            like_file = self.inputs.nativeT1
            out_file_2 = self.inputs.LabelsT1
        elif self.inputs.space == "other":  
            #xfm = run_nlinreg.inputs.out_file_xfm
            xfm = sourceToModel_xfm 
            like_file = self.inputs.mniT1
            out_file_2 = self.inputs.LabelsMNI
        elif self.inputs.space == "native": 
            xfm = self.inputs.LinMNIT1Xfm
            like_file = self.inputs.mniT1
            out_file_2 = self.inputs.LabelsMNI

        run_resample = minc.Resample() 
        run_resample.inputs.input_file = out_file_1
        run_resample.inputs.output_file = out_file_2
        run_resample.inputs.like = like_file
        run_resample.inputs.transformation = xfm
        run_resample.inputs.nearest_neighbour_interpolation = True
        run_resample.run()


        if self.inputs.space == "other": 
            # 5) Resample 'other' atlas into T1 native space 
            run_resample = minc.Resample() 
            run_resample.inputs.input_file = out_file_2
            run_resample.inputs.output_file = self.inputs.LabelsT1
            run_resample.inputs.like = self.inputs.nativeT1
            run_resample.inputs.transformation = self.inputs.LinMNIT1Xfm
            run_resample.inputs.nearest_neighbour_interpolation = True
            print run_resample.cmdline
            run_resample.run()


        # 6) Mask brain for T1 and MNI labels
        for label, mask in zip([self.inputs.LabelsT1, self.inputs.LabelsMNI], [self.inputs.brainmask_t1, self.inputs.brainmask_mni ]):
            if mask != 'NA':
                if self.inputs.brain_only :
                    temp_mask = tmpDir+"/mask.mnc"
                    run_calc = minc.Calc() #Extract the desired label from the atlas using minccalc.
                    run_calc.inputs.input_files = [ label, mask] #The ANIMAL or CIVET classified atlas
                    run_calc.inputs.output_file = temp_mask  #Output mask with desired label
                    run_calc.inputs.expression = " A[1] == 1 ? A[0] : 0 " 
                    run_calc.clobber = True
                    run_calc.run()
                    shutil.copy(temp_mask, label)
                    print "Warning: masking labeled image with brain mask."
                    print "Label: ", label
                    print "Mask: ", mask
		if self.inputs.ones_only :
		    temp_mask = tmpDir+"/mask.mnc"
		    run_calc = minc.Calc() #Extract the desired label from the atlas using minccalc.
		    run_calc.inputs.input_files = [ label ] #The ANIMAL or CIVET classified atlas
		    run_calc.inputs.output_file = temp_mask  #Output mask with desired label
		    run_calc.inputs.expression = " A[0] > 0.1 ? 1 : 0 " 
		    run_calc.clobber = True
		    run_calc.run()
		    shutil.copy(temp_mask, label)
	
        if not os.path.exists( self.inputs.LabelsT1): 
            print 'Does not exist -- Labels T1:', self.inputs.LabelsT1
            exit(0)
        if not os.path.exists( self.inputs.LabelsMNI): 
            print 'Does not exist -- Labels MNI:', self.inputs.LabelsMNI
            exit(0)

        #print '\n',self.inputs.LabelsT1, os.path.exists(self.inputs.LabelsT1) ,'\n'
        #print '\n',self.inputs.LabelsMNI, os.path.exists(self.inputs.LabelsMNI) ,'\n'
        #shutil.rmtree(tmpDir)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.LabelsT1): 
            self.inputs.LabelsT1 = self._gen_output(self.inputs.nativeT1, self._suffix+'T1') 
        if not isdefined(self.inputs.LabelsMNI): 
            self.inputs.LabelsMNI = self._gen_output(self.inputs.nativeT1, self._suffix+'MNI')

        outputs["LabelsMNI"] = self.inputs.LabelsMNI #Masks in stereotaxic space
        outputs["LabelsT1"] = self.inputs.LabelsT1 #Masks in native space
        outputs["nLinAtlasMNIXfm"] = self.inputs.nLinAtlasMNIXfm 
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        return super(Labels, self)._parse_inputs(skip=skip)

class PETheadMaskingOutput(TraitedSpec):
    out_file  = File(desc="Headmask from PET volume")

class PETheadMaskingInput(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="PET volume")
    in_json = File(exists=True, mandatory=True, desc="PET json file")
    out_file = File(desc="Head mask")
    slice_factor = traits.Float(usedefault=True, default_value=0.25, desc="Value (between 0. to 1.) that is multiplied by the maximum of the slices of the PET image. Used to threshold slices. Lower value means larger mask")
    total_factor = traits.Float(usedefault=True, default_value=0.333, desc="Value (between 0. to 1.) that is multiplied by the thresholded means of each slice. ")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETheadMasking(BaseInterface):
    input_spec = PETheadMaskingInput
    output_spec = PETheadMaskingOutput
    _suffix = "_headmask"

    # def _parse_inputs(self, skip=None):
    #     if skip is None:
    #         skip = []
    #     if not isdefined(self.inputs.out_file):
    #         self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
    #     return super(PETheadMasking, self)._parse_inputs(skip=skip)
    def _run_interface(self, runtime):

        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
            #Load PET 3D volume
        infile = volumeFromFile(self.inputs.in_file)
        zmax=infile.sizes[infile.dimnames.index("zspace")]
        #Get max slice values and multiply by pet_mask_slice_threshold (0.25 by default)
        slice_thresholds=np.amax(infile.data, axis=(1,2)) * self.inputs.slice_factor
        #Get mean for all values above slice_max
        slice_mean_f=lambda t, d, i: float(np.mean(d[i, d[i,:,:] > t[i]])) 
        slice_mean = np.array([ slice_mean_f(slice_thresholds, infile.data, i)  for i in range(zmax) ])
        #Remove nan from slice_mean
        slice_mean =slice_mean[ ~ np.isnan(slice_mean) ]
        #Calculate overall mean from mean of thresholded slices
        overall_mean = np.mean(slice_mean)
        #Calcuate threshold
        threshold = overall_mean * self.inputs.total_factor
        #Apply threshold and create and write outputfile
        run_calc = CalcCommand();
        run_calc.inputs.input_files = self.inputs.in_file 
        run_calc.inputs.output_file = self.inputs.out_file
        run_calc.inputs.expression = 'A[0] >= '+str(threshold)+' ? 1 : 0'
        if self.inputs.verbose:
            print run_calc.cmdline
        if self.inputs.run:
            run_calc.run()

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
        outputs["out_file"] = self.inputs.out_file
        return outputs

"""
.. module:: masking
    :platform: Unix
    :synopsis: Module to create labeled images. 
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""

def get_workflow(name, infosource, datasink, opts):
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
    out_list=["pet_brainmask", "brainmask_t1", "brainmask_mni",  "results_label_img_t1", "results_label_img_mni" ]
    in_list=["nativeT1","mniT1","brainmask", "pet_volume","pet_header_json", "results_labels", "results_label_space","results_label_template","results_label_img", 'LinT1MNIXfm', 'pvc_erode_times', 'tka_erode_times', 'results_erode_times' ]
    if not opts.nopvc: 
        out_list += ["pvc_label_img_t1", "pvc_label_img_mni"]
        in_list += ["pvc_labels", "pvc_label_space", "pvc_label_img","pvc_label_template"]
    if not opts.tka_method == None: 
        out_list += ["tka_label_img_t1", "tka_label_img_mni"]
        in_list +=  ["tka_labels", "tka_label_space","tka_label_template","tka_label_img"]
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=in_list), name='inputnode')
    #Define empty node for output

    invert_MNI2T1 = pe.Node(interface=minc.XfmInvert(), name="invert_MNI2T1")
    workflow.connect(inputnode, 'LinT1MNIXfm',invert_MNI2T1 , 'input_file')
    
    node_name="brainmask"
    brainmaskNode = pe.Node(interface=Labels(), name=node_name)
    brainmaskNode.inputs.space = "icbm152"
    brainmaskNode.inputs.labels = [1]
    workflow.connect(inputnode, 'brainmask', brainmaskNode, 'label_img')
    workflow.connect(inputnode, 'LinT1MNIXfm', brainmaskNode, 'LinT1MNIXfm')
    workflow.connect(invert_MNI2T1, 'output_file', brainmaskNode, 'LinMNIT1Xfm')
    workflow.connect(inputnode, 'nativeT1', brainmaskNode, 'nativeT1')
    workflow.connect(inputnode, 'mniT1', brainmaskNode, 'mniT1')

    node_name="pet_brainmask"
    petMasking = pe.Node(interface=PETheadMasking(), name=node_name)
    petMasking.inputs.slice_factor = opts.slice_factor
    petMasking.inputs.total_factor = opts.total_factor
    workflow.connect(inputnode, 'pet_volume', petMasking, 'in_file')
    workflow.connect(inputnode, 'pet_header_json', petMasking, 'in_json')

    if not opts.nopvc:
        node_name="pvcLabels"
        pvcLabels = pe.Node(interface=Labels(), name=node_name)
        pvcLabels.inputs.space = opts.pvc_label_space
        pvcLabels.inputs.erode_times = opts.pvc_erode_times
        pvcLabels.inputs.brain_only = opts.pvc_labels_brain_only
        pvcLabels.inputs.ones_only = opts.pvc_labels_ones_only
        workflow.connect(inputnode, 'pvc_labels', pvcLabels, 'labels')
        workflow.connect(inputnode, 'pvc_label_img', pvcLabels, 'label_img')
        workflow.connect(inputnode, 'pvc_label_template', pvcLabels, 'label_template')
        workflow.connect(inputnode, 'nativeT1', pvcLabels, 'nativeT1')
        workflow.connect(inputnode, 'mniT1', pvcLabels, 'mniT1')
        workflow.connect(inputnode, 'LinT1MNIXfm', pvcLabels, 'LinT1MNIXfm')
        workflow.connect(invert_MNI2T1, 'output_file', pvcLabels, 'LinMNIT1Xfm')
        workflow.connect(brainmaskNode, 'LabelsT1', pvcLabels , 'brainmask_t1')
        workflow.connect(brainmaskNode, 'LabelsMNI', pvcLabels, 'brainmask_mni')

    if not opts.tka_method == None:
        node_name="tkaLabels"
        tkaLabels = pe.Node(interface=Labels(), name=node_name)
        tkaLabels.inputs.space = opts.tka_label_space
        tkaLabels.inputs.erode_times = opts.tka_erode_times
        tkaLabels.inputs.brain_only = opts.tka_labels_brain_only
        tkaLabels.inputs.ones_only = opts.tka_labels_ones_only
        workflow.connect(inputnode, 'tka_labels', tkaLabels, 'labels')
        workflow.connect(inputnode, 'tka_label_img', tkaLabels, 'label_img')
        workflow.connect(inputnode, 'tka_label_template', tkaLabels, 'label_template')
        workflow.connect(inputnode, 'nativeT1', tkaLabels, 'nativeT1')
        workflow.connect(inputnode, 'mniT1', tkaLabels, 'mniT1')
        workflow.connect(inputnode, 'LinT1MNIXfm', tkaLabels, 'LinT1MNIXfm')
        workflow.connect(invert_MNI2T1, 'output_file', tkaLabels, 'LinMNIT1Xfm') 
        workflow.connect(brainmaskNode, 'LabelsT1', tkaLabels , 'brainmask_t1')
        workflow.connect(brainmaskNode, 'LabelsMNI', tkaLabels, 'brainmask_mni')

    node_name="resultsLabels"
    resultsLabels = pe.Node(interface=Labels(), name=node_name)
    resultsLabels.inputs.space = opts.results_label_space
    resultsLabels.inputs.erode_times = opts.results_erode_times
    resultsLabels.inputs.brain_only = opts.results_labels_brain_only
    resultsLabels.inputs.ones_only = opts.results_labels_ones_only
    workflow.connect(inputnode, 'results_labels', resultsLabels, 'labels')
    workflow.connect(inputnode, 'results_label_img', resultsLabels, 'label_img')
    workflow.connect(inputnode, 'results_label_template', resultsLabels, 'label_template')
    workflow.connect(inputnode, 'nativeT1', resultsLabels, 'nativeT1')
    workflow.connect(inputnode, 'mniT1', resultsLabels, 'mniT1')
    workflow.connect(inputnode, 'LinT1MNIXfm', resultsLabels, 'LinT1MNIXfm')
    workflow.connect(brainmaskNode, 'LabelsT1', resultsLabels , 'brainmask_t1')
    workflow.connect(brainmaskNode, 'LabelsMNI', resultsLabels, 'brainmask_mni')
    workflow.connect(invert_MNI2T1, 'output_file', resultsLabels, 'LinMNIT1Xfm')
    
    return(workflow)
