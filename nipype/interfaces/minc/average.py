import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)






class AverageOutput(TraitedSpec):
    out_file = File(exists=True, desc="3D output image")

class AverageInput(MINCCommandInputSpec):
    input_file = File(position=0, argstr="%s", mandatory=True, desc="4D input image")
    out_file = File(position=-1, argstr="%s", mandatory=True, desc="3D output image")

    avgdim = traits.Str(argstr="-avgdim %s", mandatory=True, desc="Specify a dimension along which we wish to average")
    width_weighted = traits.Bool(argstr="-width_weighted", usedefault=True, default_value=True, desc="Weight by dimension widths.")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class AverageCommand(MINCCommand):
    _cmd = "mincaverage"
    _suffix = "_sum"
    input_spec = AverageInput
    output_spec = AverageOutput

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


