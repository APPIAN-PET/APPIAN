import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)






class ConcatOutput(TraitedSpec):
    output_file = File(exists=True, desc="resampled image")

class ConcatInput(MINCCommandInputSpec):
    # input_file = File(position=0, argstr="%s", mandatory=True, desc="Input image.")
    input_file = InputMultiPath(File(mandatory=True), position=0, argstr='%s', desc='List of input images.')
    output_file = File(position=1, argstr="%s", mandatory=True, desc="Output image.")
    
    dimension = traits.Str(argstr="-concat_dimension %s", desc="Concatenate along a given dimension.")
    start = traits.Float(argstr="-start %s", desc="Starting coordinate for new dimension.")
    step = traits.Float(argstr="-step %s", desc="Step size for new dimension.")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ConcatCommand(MINCCommand):
    _cmd = "mincconcat"
    _suffix = "_concat"
    input_spec = ConcatInput
    output_spec = ConcatOutput

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_file"] = self.inputs.output_file
        if not isdefined(self.inputs.output_file):
            outputs["output_file"] = self._gen_fname(self.inputs.input_file, suffix=self._suffix)
        outputs["output_file"] = os.path.abspath(outputs["output_file"])
        return outputs

    def _gen_filename(self, name):
        if name == "output_file":
            return self._list_outputs()["output_file"]
        return None


