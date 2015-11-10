import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from ...utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)



 
class SmoothInput(MINCCommandInputSpec):
    # input_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="image to blur")
    input_file = File(position=0, argstr="%s", mandatory=True, desc="image to blur")
    output_file = File(position=1, argstr="%s", desc="smoothed image")
    # output_file = File(position=1, argstr="%s", name_source=["input_file"], name_template='%s', output_name='output_file', desc="smoothed image")

    fwhm = traits.Int(position=2, argstr="-fwhm %d", mandatory=True, desc="fwhm value")  
    no_apodize = traits.Bool(position=-3, argstr="-no_apodize", usedefault=True, default_value=True, desc="Do not apodize the data before blurring")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class SmoothOutput(TraitedSpec):
    output_file = File(exists=True, desc="smoothed image")

class SmoothCommand(MINCCommand, Info):
    _cmd = "mincblur"
    _suffix = "_blur"
    input_spec = SmoothInput
    output_spec = SmoothOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        if not isdefined(self.inputs.output_file):
            fname, ext = os.path.splitext(self.inputs.input_file)
            self.inputs.output_file = fname + '_fwhm' + str(self.inputs.fwhm)

        return super(SmoothCommand, self)._parse_inputs(skip=skip)


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_file"] = self.inputs.output_file + self._suffix + '.mnc'
        return outputs


    def _gen_filename(self, name):
        if name == "output_file":
            return self._list_outputs()["output_file"]
        return None
