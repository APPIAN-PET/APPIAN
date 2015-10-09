import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)




class CalcOutput(TraitedSpec):
    out_file = File(exists=True, desc="output image")

class CalcInput(MINCCommandInputSpec):
#    input_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="input image")
    input_file = InputMultiPath(File(exits=True, mandatory=True), position=0, desc='list of inputs', argstr='%s')
    out_file = File(position=1, argstr="%s", mandatory=True, desc="output image")

    expression = traits.Str(position=2, argstr="-expression '%s'", mandatory=True, desc="algorithm")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class CalcCommand(MINCCommand):
    _cmd = "minccalc"
    _suffix = "_minccalc"
    input_spec = CalcInput
    output_spec = CalcOutput

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


