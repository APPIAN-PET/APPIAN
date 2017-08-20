# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a
import nipype.pipeline.engine as pe
import os
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)

import numpy as np
import ntpath
from nipype.interfaces.minc.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)

class PVCInput(CommandLineInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask = File( position=2, argstr="-mask %s", desc="Integer mask file")
    input_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    z_fwhm = traits.Float( argstr="-z %f", desc="FWHM of PSF along z-axis")
    y_fwhm = traits.Float( argstr="-y %f", desc="FWHM of PSF along y-axis")
    x_fwhm = traits.Float( argstr="-x %f", desc="FWHM of PSF along x-axis")
    fwhm = traits.Float( argstr="-fwhm %f", desc="FWHM of PSF all axes")
     
    max_iterations = traits.Int(argstr="-max-iterations %d", desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-tolerance %f", desc="Tolerance")
    denoise_fwhm = traits.Float( argstr="-denoise_fwhm %f", desc="FWHM for denoising image")
    lambda_var = traits.Float( argstr="-lambda %f", desc="Lambda for controlling smoothing across regions")
    nvoxel_to_average = traits.Int( argstr="-nvoxel-to-average %f", desc="Number of voxels to average over.")
    pvc_method = traits.Str(argstr="--pvc %s",mandatory=False, desc="PVC type")
  
class PVCOutput(TraitedSpec):
    out_file = File(argstr="-o %s", exists=True, desc="Output PET image")

class PVCCommand(CommandLine):
    input_spec =  PVCInput
    output_spec = PVCOutput
    _cmd='gtm'
    _suffix='_gtm'
    #def __init__(self, pvc_method):
    #    pass
    #self._cmd = pvc_method 
    #    self._suffix = "_" + self._cmd 

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
        return super(PVCCommand, self)._parse_inputs(skip=skip)


def get_workflow(name, infosource, datasink, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_center", "pet_mask"]), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputnode')
    node_name=opts.pvc_method
    PVCNode = pe.Node(interface=PVCCommand(), name=node_name)
    if opts.pvc_method == "gtm":
        PVCNode.inputs.fwhm = opts.scanner_fwhm[0]
    elif opts.pvc_method == "idSURF":
        PVCNode.inputs.max_iterations = opts.max_iterations
        PVCNode.inputs.tolerance = opts.tolerance
        PVCNode.inputs.denoise_fwhm = opts.denoise_fwhm
        PVCNode.inputs.lambda_var = opts.lambda_var
        PVCNode.inputs.nvoxel_to_average=opts.nvoxel_to_average
    else:
        PVCNode.inputs.z_fwhm = opts.scanner_fwhm[0]
        PVCNode.inputs.y_fwhm = opts.scanner_fwhm[1]
        PVCNode.inputs.x_fwhm = opts.scanner_fwhm[2]
        PVCNode.inputs.pvc_method = opts.pvc_method
    workflow.connect([
                    (inputnode, PVCNode, [('pet_center','input_file')]),
                    (inputnode, PVCNode, [('pet_mask','mask')])
                    ])
    workflow.connect(PVCNode, 'out_file', datasink, 'pvc')
    workflow.connect(PVCNode, 'out_file', outputnode, "out_file")

    return(workflow)

