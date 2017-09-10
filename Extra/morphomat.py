import os
import numpy as np

from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)






class MorphOutput(TraitedSpec):
    out_file = File(exists=True, desc="mincmorphed image")

class MorphInput(CommandLineInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="image to mincmorph")
    out_file = File(position=1, argstr="%s", mandatory=True, desc="mincmorphed image")

    successive = traits.Str(position=2, argstr="-successive %s", mandatory=True, desc="Successive operations")
    
    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class MorphCommand(CommandLine):
    _cmd = "mincmorph"
    _suffix = "_mincmorph"
    input_spec = MorphInput
    output_spec = MorphOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix)

        return super(MorphCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


