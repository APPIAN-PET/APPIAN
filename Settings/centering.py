import os
import numpy as np
import tempfile
import shutil

from os.path import basename

from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile

from nipype.interfaces.minc.info import InfoCommand
from nipype.interfaces.minc.info import StatsCommand




class VolCenteringOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class VolCenteringInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Image")
    out_file = File(argstr="%s", desc="Image after centering")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class VolCenteringRunning(BaseInterface):
    input_spec = VolCenteringInput
    output_spec = VolCenteringOutput
    _suffix = "_LinReg"


    def _run_interface(self, runtime):
        tmpdir = tempfile.mkdtemp()



        shutil.rmtree(tmpdir)

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        
        return outputs



