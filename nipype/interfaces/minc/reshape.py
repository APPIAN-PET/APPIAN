import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)




class ReshapeOutput(TraitedSpec):
    output_file = File(exists=True, desc="output image")

class ReshapeInput(MINCCommandInputSpec):
    input_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="input image")
    output_file = File(position=1, argstr="%s", mandatory=True, desc="output image")
    
    dimrange = traits.Str(position=2, argstr="-dimrange '%s'", desc="Specify range of dimension subscripts")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ReshapeCommand(MINCCommand):
    _cmd = "mincreshape"
    _suffix = "_mincreshape"
    input_spec = ReshapeInput
    output_spec = ReshapeOutput

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


