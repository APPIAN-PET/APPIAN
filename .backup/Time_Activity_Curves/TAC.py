import os
import numpy as np
import tempfile
import shutil

from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile




class idwcInput(BaseInterfaceInputSpec):

	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class idwcOutput(TraitedSpec):

class idwcRunning(BaseInterface):
    input_spec = idwcInput
    output_spec = idwcOutput


    def _run_interface(self, runtime):


		return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()






class idwcRpmInput(BaseInterfaceInputSpec):

	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class idwcRpmOutput(TraitedSpec):

class idwcRpmRunning(BaseInterface):
    input_spec = idwcRpmInput
    output_spec = idwcRpmOutput


    def _run_interface(self, runtime):


		return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()



class dftRegionalInput(BaseInterfaceInputSpec):

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class dftRegionalOutput(TraitedSpec):

class dftRegionalRunning(BaseInterface):
    input_spec = dftRegionalInput
    output_spec = dftRegionalOutput


    def _run_interface(self, runtime):


        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()



