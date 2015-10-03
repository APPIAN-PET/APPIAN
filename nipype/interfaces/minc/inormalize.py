import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)






class InormalizeOutput(TraitedSpec):
    out_file = File(exists=True, desc="Normalized image")

class InormalizeInput(MINCCommandInputSpec):
    input_file = File(position=0, argstr="%s", mandatory=True, desc="image to normalize")
    out_file = File(position=1, argstr="%s", mandatory=True, desc="Normalized image")
    model_file = File(position=2, argstr="-model %s", mandatory=True, desc="model image")
    
    clobber = traits.Bool(position=-2, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(position=-1, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class InormalizeCommand(MINCCommand):
    _cmd = "inormalize"
    _suffix = "_inorm"
    input_spec = InormalizeInput
    output_spec = InormalizeOutput

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        if not isdefined(self.inputs.out_file):
            outputs["out_file"] = self._gen_fname(self.inputs.input_file, suffix=self._suffix)
        outputs["out_file"] = os.path.abspath(outputs["out_file"])
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


