import os
import numpy as np

from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)



class PVCOutput(TraitedSpec):
    out_file = File(argstr="-o %s", exists=True, desc="PVC PET image")


class PVCInput(MINCCommandInputSpec):
    out_file = File(  mandatory=True,  argstr="-o %s",desc="image to operate on")
    input_file = File( mandatory=True,exists=True, argstr="-pet %s", desc="PET file")
    mask = File(exists=True, mandatory=True,  argstr="-mask %s", desc="Integer mask file")
    fwhm = traits.Float(exists=True, mandatory=True, argstr="-fwhm %f", desc="FWHM of Gaussian filter")

class idsurfInput(PVCInput):
    first_guess = File(exists=True, argstr="-first_guess %s", desc="First guess of PVC")
    max_iterations = traits.Int(mandatory=True, argstr="-max-iterations %d", desc="Maximum number of iterations")
    tolerance = traits.Float(mandatory=True, argstr="-tolerance %f", desc="Tolerance")
    denoise_fwhm = traits.Float(mandatory=True, argstr="-denoise_fwhm %f", desc="FWHM for denoising image")
    lambda_var = traits.Float(mandatory=True, argstr="-lambda %f", desc="Lambda for controlling smoothing across regions")
    smooth_only = traits.boolean(argstr="-smooth_only", desc="No PVC, only smooth")
    


class idsurfCommand(MINCCommand):
    _cmd = "idSURF"
    _suffix = "_idsurf"
    input_spec =  idsurfInput
    output_spec = PVCOutput

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        if not isdefined(self.inputs.out_file):
            outputs["out_file"] = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
        outputs["out_file"] = os.path.abspath(outputs["out_file"])
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

#class gtmCommand(MINCCommand):
#    _cmd = "gtm"
#    _suffix = "_gtm"
#    input_spec = PVCInput
#    output_spec = PVCOutput
#
#    def _list_outputs(self):
#        outputs = self.output_spec().get()
#        outputs["out_file"] = self.inputs.out_file
#        if not isdefined(self.inputs.out_file):
#            outputs["out_file"] = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
#        outputs["out_file"] = os.path.abspath(outputs["out_file"])
#        return outputs
#
#    def _gen_filename(self, name):
#        if name == "out_file":
#            return self._list_outputs()["out_file"]
#        return None



