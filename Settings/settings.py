import os
import numpy as np
import tempfile
import shutil

from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile

from nipype.interfaces.minc.calc import CalcCommand



class PETinfoInput(BaseInterfaceInputSpec):

	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETinfoOutput(TraitedSpec):

class PETinfoRunning(BaseInterface):
    input_spec = PETinfoInput
    output_spec = PETinfoOutput


    def _run_interface(self, runtime):

		return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()



