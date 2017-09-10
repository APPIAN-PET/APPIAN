import os
import numpy as np

from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)




class CalcOutput(TraitedSpec):
    out_file = File(exists=True, desc="output image")

class CalcInput(CommandLineInputSpec):
    in_file = InputMultiPath(File(exits=True, mandatory=True), position=0, desc='list of inputs', argstr='%s')
    out_file = File(position=1, argstr="%s", desc="output image")

    expression = traits.Str(position=2, argstr="-expression '%s'", desc="algorithm")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class CalcCommand(CommandLine):
    _cmd = "minccalc"
    _suffix = "_calc"
    input_spec = CalcInput
    output_spec = CalcOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file[0], suffix=self._suffix)
        return super(CalcCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


