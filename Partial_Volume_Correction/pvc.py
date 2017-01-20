import os
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)

import numpy as np
import ntpath
from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)

class PVCInput(MINCCommandInputSpec):
    out_file = File( argstr="-o %s",desc="image to operate on")
    input_file = File(exists=True, argstr="-pet %s", desc="PET file")
    mask = File(argstr="-mask %s", desc="Integer mask file")
    fwhm = traits.Float(argstr="-fwhm %f", desc="FWHM of Gaussian filter")
    first_guess = File(argstr="-first_guess %s", desc="First guess of PVC")
    max_iterations = traits.Int(argstr="-max-iterations %d", desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-tolerance %f", desc="Tolerance")
    denoise_fwhm = traits.Float( argstr="-denoise_fwhm %f", desc="FWHM for denoising image")
    lambda_var = traits.Float( argstr="-lambda %f", desc="Lambda for controlling smoothing across regions")
    nvoxel_to_average = traits.Int( argstr="-nvoxel-to-average %f", desc="Number of voxels to average over.")

  
class GTMOutput(TraitedSpec):
    out_file = File(argstr="-o %s", exists=True, desc="GTM PVC PET image")

class GTMInput(MINCCommandInputSpec):
    out_file = File( argstr="-o %s",desc="image to operate on")
    input_file = File(exists=True, argstr="-pet %s", desc="PET file")
    mask = File(argstr="-mask %s", desc="Integer mask file")
    fwhm = traits.Float(argstr="-fwhm %f", desc="FWHM of Gaussian filter")

class GTMCommand(MINCCommand):
    input_spec =  GTMInput
    output_spec = GTMOutput

    _cmd = "gtm" #input_spec.pvc_method 
    _suffix = "_" + _cmd 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.input_file, self._suffix)
        return super(GTMCommand, self)._parse_inputs(skip=skip)



class idSURFOutput(TraitedSpec):
    out_file = File(argstr="-o %s", exists=True, desc="GTM PVC PET image")

class idSURFInput(MINCCommandInputSpec):
    out_file = File( argstr="-o %s",desc="image to operate on")
    input_file = File(exists=True, argstr="-pet %s", desc="PET file")
    mask = File(argstr="-mask %s", desc="Integer mask file")
    fwhm = traits.Float(argstr="-fwhm %f", desc="FWHM of Gaussian filter")
    first_guess = File(argstr="-first_guess %s", desc="First guess of PVC")
    max_iterations = traits.Int(argstr="-max-iterations %d", desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-tolerance %f", desc="Tolerance")
    denoise_fwhm = traits.Float( argstr="-denoise_fwhm %f", desc="FWHM for denoising image")
    lambda_var = traits.Float( argstr="-lambda %f", desc="Lambda for controlling smoothing across regions")
    nvoxel_to_average = traits.Int( argstr="-nvoxel-to-average %f", desc="Number of voxels to average over.")

class idSURFCommand(MINCCommand):
    input_spec =  idSURFInput
    output_spec = idSURFOutput

    _cmd = "idSURF" #input_spec.pvc_method 
    _suffix = "_" + _cmd 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.input_file, self._suffix)
        return super(idSURFCommand, self)._parse_inputs(skip=skip)




def get_workflow(name, infosource, datasink, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_center", "pet_mask"]), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputnode')

    node_name="GTM"
    gtmNode = pe.Node(interface=GTMCommand(), name=node_name)
    gtmNode.inputs.fwhm = opts.scanner_fwhm

    node_name="idSURF"
    idSURFNode = pe.Node(interface=idSURFCommand(), name=node_name)
    idSURFNode.inputs.fwhm = opts.scanner_fwhm
    idSURFNode.inputs.max_iterations = opts.max_iterations
    idSURFNode.inputs.tolerance = opts.tolerance
    idSURFNode.inputs.denoise_fwhm = opts.denoise_fwhm
    idSURFNode.inputs.lambda_var = opts.lambda_var
    idSURFNode.inputs.nvoxel_to_average=opts.nvoxel_to_average

    


    workflow.connect([(inputnode, gtmNode, [('pet_center','input_file')]),
                    (inputnode, gtmNode, [('pet_mask','mask')])
                    ])
    if opts.pvc_method == "GTM":
        workflow.connect(gtmNode, 'out_file', datasink, gtmNode.name)
        workflow.connect(gtmNode, 'out_file', outputnode, "out_file")

    if opts.pvc_method == "idSURF":
        workflow.connect([(gtmNode, idSURFNode, [('out_file','first_guess')]),
                        (inputnode, idSURFNode, [('pet_center','input_file')]),
                        (inputnode, idSURFNode, [('pet_PVCMask','mask')])
                        ])
        workflow.connect(idSURFNode, 'out_file', datasink, idSURFNode.name)
        workflow.connect(idSURFNode, 'out_file', outputnode, "out_file")



    return(workflow)

