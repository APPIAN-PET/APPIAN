import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)



 


class ConcatInput(MINCCommandInputSpec):
    in_file_xfm = File(position=0, argstr="%s", exists=True, mandatory=True, desc="main input xfm file")
    in_files_xfm2 = File(position=1, argstr="%s", exists=True, mandatory=True, desc="input xfm files to concat")
    out_file_xfm = File(position=2, argstr="%s", desc="output concatenated xfm file")

    clobber = traits.Bool(position=-2, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(position=-1, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ConcatOutput(TraitedSpec):
    output_file = File(exists=True, desc="transformation matrix")

class ConcatCommand(MINCCommand, Info):
    _cmd = "xfmconcat"
    _suffix = "_concat"
    input_spec = ConcatInput
    output_spec = ConcatOutput


    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        if not isdefined(self.inputs.out_file_xfm):
            fname, ext = os.path.splitext(self.inputs.in_file_xfm)
            # self.inputs.out_file_xfm = self._gen_fname(fname, suffix=self._suffix)
            self.inputs.out_file_xfm = fname + self._suffix + '.xfm'

        return super(ConcatCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_file"] = self.inputs.out_file_xfm
        return outputs

    def _run_interface(self, runtime):
        runtime = super(ConcatCommand, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime

    def _gen_filename(self, name):
        if name == "output_file":
            return self._list_outputs()["output_file"]
        return None







class InvertInput(MINCCommandInputSpec):
    in_file_xfm = File(position=0, argstr="%s", exists=True, mandatory=True, desc="main input xfm file")
    out_file_xfm = File(position=2, argstr="%s", desc="output inverted xfm file")

    clobber = traits.Bool(position=-2, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(position=-1, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class InvertOutput(TraitedSpec):
    output_file = File(desc="transformation matrix")

class InvertCommand(MINCCommand, Info):
    _cmd = "xfminvert"
    _suffix = "_inv"
    input_spec = InvertInput
    output_spec = InvertOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        if not isdefined(self.inputs.out_file_xfm):
            fname, ext = os.path.splitext(self.inputs.in_file_xfm)
            # self.inputs.out_file_xfm = self._gen_fname(fname, suffix=self._suffix)
            self.inputs.out_file_xfm = fname + self._suffix + '.xfm'

        return super(InvertCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_file"] = self.inputs.out_file_xfm
        return outputs


    def _run_interface(self, runtime):
        runtime = super(InvertCommand, self)._run_interface(runtime)
        if runtime.stderr:
            self.raise_exception(runtime)
        return runtime

    def _gen_filename(self, name):
        if name == "output_file":
            return self._list_outputs()["output_file"]
        return None



