# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a
import nipype.pipeline.engine as pe
import os
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)

import numpy as np
import ntpath
from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)

class PVCInput(MINCCommandInputSpec):
    out_file = File(position=3, argstr="%s",desc="image to operate on")
    mask = File( position=2, argstr="-mask %s", desc="Integer mask file")
    input_file = File(exists=True, position=1, argstr="%s", desc="PET file")
    z_fwhm = traits.Float( argstr="-z %f", desc="FWHM of PSF along z-axis")
    y_fwhm = traits.Float( argstr="-y %f", desc="FWHM of PSF along y-axis")
    x_fwhm = traits.Float( argstr="-x %f", desc="FWHM of PSF along x-axis")
     
    max_iterations = traits.Int(argstr="-max-iterations %d", desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-tolerance %f", desc="Tolerance")
    denoise_fwhm = traits.Float( argstr="-denoise_fwhm %f", desc="FWHM for denoising image")
    lambda_var = traits.Float( argstr="-lambda %f", desc="Lambda for controlling smoothing across regions")
    nvoxel_to_average = traits.Int( argstr="-nvoxel-to-average %f", desc="Number of voxels to average over.")
    pvc_method = traits.Str(argstr="--pvc %s",mandatory=True, desc="PVC type")

  
class PVCOutput(TraitedSpec):
    out_file = File(argstr="-o %s", exists=True, desc="Output PET image")

class PVCCommand(MINCCommand):
    input_spec =  PVCInput
    output_spec = PVCOutput
    
    def __init__(self, pvc_method):
        self._cmd = pvc_method 
        self._suffix = "_" + _cmd 

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


def get_workflow(name, infosource, datasink, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_center", "pet_mask"]), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputnode')
    node_name=opts.pvc_method
    PVCNode = pe.Node(interface=PVCCommand(opts.pvc_method), name=node_name)
    PVCNode.inputs.z_fwhm = opts.scanner_fwhm[0]
    PVCNode.inputs.y_fwhm = opts.scanner_fwhm[1]
    PVCNode.inputs.x_fwhm = opts.scanner_fwhm[2]
    PVCNode.inputs.pvc_method = opts.pvc_method
    if opts.pvc_method == "idSURF":
        PVCNode.inputs.max_iterations = opts.max_iterations
        PVCNode.inputs.tolerance = opts.tolerance
        PVCNode.inputs.denoise_fwhm = opts.denoise_fwhm
        PVCNode.inputs.lambda_var = opts.lambda_var
        PVCNode.inputs.nvoxel_to_average=opts.nvoxel_to_average
    workflow.connect([
                    (inputnode, PVCNode, [('pet_center','input_file')]),
                    (inputnode, PVCNode, [('pet_mask','mask')])
                    ])
    workflow.connect(PVCNode, 'out_file', datasink, PVCNode.name)
    workflow.connect(PVCNode, 'out_file', outputnode, "out_file")

    return(workflow)

    '''node_name="GTM"
    gtmNode = pe.Node(interface=GTMCommand(), name=node_name)
    gtmNode.inputs.fwhm = opts.scanner_fwhm

    workflow.connect([(inputnode, gtmNode, [('pet_center','input_file')]),
                    (inputnode, gtmNode, [('pet_mask','mask')])
                    ])
    if opts.pvc_method == "GTM":
        workflow.connect(gtmNode, 'out_file', datasink, gtmNode.name)
        workflow.connect(gtmNode, 'out_file', outputnode, "out_file")

    if opts.pvc_method == "idSURF":
 	node_name="idSURF"
    	idSURFNode = pe.Node(interface=idSURFCommand(), name=node_name)
    	idSURFNode.inputs.fwhm = opts.scanner_fwhm
    	idSURFNode.inputs.max_iterations = opts.max_iterations
    	idSURFNode.inputs.tolerance = opts.tolerance
    	idSURFNode.inputs.denoise_fwhm = opts.denoise_fwhm
    	idSURFNode.inputs.lambda_var = opts.lambda_var
    	idSURFNode.inputs.nvoxel_to_average=opts.nvoxel_to_average
        workflow.connect([(gtmNode, idSURFNode, [('out_file','first_guess')]),
                        (inputnode, idSURFNode, [('pet_center','input_file')]),
                        (inputnode, idSURFNode, [('pet_mask','mask')])
                        ])
        workflow.connect(idSURFNode, 'out_file', datasink, idSURFNode.name)
        workflow.connect(idSURFNode, 'out_file', outputnode, "out_file")'''

'''class idSURFOutput(TraitedSpec):
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
'''
