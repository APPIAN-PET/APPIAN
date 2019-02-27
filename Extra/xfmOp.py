import shutil
import os
import re
import numpy as np
from os.path import splitext, basename
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)

class ConcatInput(CommandLineInputSpec):
    in_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="main input xfm file")
    in_file_2 = File(position=1, argstr="%s", exists=True, mandatory=True, desc="input xfm files to concat")
    out_file = File(position=2, argstr="%s", desc="output concatenated xfm file")
    in_warp = File( desc="output concatenated xfm file")
    in_warp_2 = File( desc="output concatenated xfm file")
    out_warp = File(desc="transformation image")
    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ConcatOutput(TraitedSpec):
    out_file = File(exists=True, desc="transformation matrix")
    out_warp = File(desc="transformation image")

class ConcatCommand(CommandLine):
    _cmd = "xfmconcat"
    _suffix = "_concat"
    input_spec = ConcatInput
    output_spec = ConcatOutput


    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_filename(self.inputs.in_file, self.inputs.in_file_2, self._suffix)

        return super(ConcatCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_filename(self.inputs.in_file, self.inputs.in_file_2, self._suffix)
        self.inputs.out_warp = re.sub('.xfm', 'grid_0.mnc', self.inputs.out_file)
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        outputs["out_warp"] = self.inputs.out_warp
        return outputs


    def _gen_filename(self, name, name2, suffix):
        split_name = splitext(name)
        fn = os.getcwd() + os.sep + basename(split_name[0])+"_concat" + split_name[1]
        return fn


class ConcatNLCommand(BaseInterface):
    _suffix = "_concat"
    input_spec = ConcatInput
    output_spec = ConcatOutput

    def _run_interface(self, runtime):
        
        concat=ConcatCommand()
        concat.inputs.in_file = self.inputs.in_file
        concat.inputs.in_file_2 = self.inputs.in_file_2
        concat.run()
        print(concat.inputs.out_warp)
        #exit(1)
        #if os.path.exists(self.inputs.in_warp) or os.path.exists(self.inputs.in_warp_2) :
        #    if not os.path.exists(concat.inputs.out_warp) :
        #        if os.path.exists(self.inputs.in_warp) :
        #            shutil.copy(self.inputs.in_warp, concat.inputs.out_warp)
        #        else :
        #            shutil.copy(self.inputs.in_warp_2, concat.inputs.out_warp)

        #exit(1)
        
        return runtime
    
    def _gen_filename(self, name, name2, suffix):
        split_name = splitext(name)
        fn = os.getcwd() + os.sep + basename(split_name[0])+"_concat" + split_name[1]
        return fn
    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_filename(self.inputs.in_file, self.inputs.in_file_2, self._suffix)
        if not isdefined(self.inputs.out_warp):
            self.inputs.out_warp = re.sub('.xfm', '_grid_0.mnc', self.inputs.out_file)
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        outputs["out_warp"] = self.inputs.out_warp
        return outputs
class InvertInput(CommandLineInputSpec):
    in_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="main input xfm file")
    out_file = File(position=2, argstr="%s", desc="output inverted xfm file")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class InvertOutput(TraitedSpec):
    out_file = File(desc="transformation matrix")

class InvertCommand(CommandLine):
    _cmd = "xfminvert"
    _suffix = "_inv"
    input_spec = InvertInput
    output_spec = InvertOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix, ext='.xfm')

        return super(InvertCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None
