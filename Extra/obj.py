import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
import os

class objOutput(TraitedSpec):
	out_file=traits.File(argstr="%s", desc="Out file")

class objInput(CommandLineInputSpec):
	in_file=traits.File(argstr="%s",position=1, desc="In obj file")
	tfm_file=traits.File(argstr="%s",position=2, desc="Transform file")
	out_file=traits.File(argstr="%s",position=3, desc="Out file")

class transform_objectCommand(CommandLine ):
    input_spec = objInput  
    output_spec = objOutput
    _cmd = "transform_objects"
    _suffix="_tfm"

    def _gen_outputs(self, fn) :
        fn_split = os.path.splitext(fn)
        return os.getcwd() + os.sep +  os.path.basename( fn_split[0] ) + self._suffix + fn_split[1]

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_outputs(self.inputs.in_file)

        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_outputs(self.inputs.in_file)
        return super(transform_objectCommand, self)._parse_inputs(skip=skip)


class volume_object_evaluateOutput(TraitedSpec):
	out_file=traits.File(argstr="%s", desc="Out file")

class volume_object_evaluateInput(CommandLineInputSpec):
        vol_file=traits.File(argstr="%s",position=1, desc="In obj file")
	obj_file=traits.File(argstr="%s",position=2, desc="Transform file")
	out_file=traits.File(argstr="%s",position=3, desc="Out file")

class volume_object_evaluateCommand( CommandLine ):
    input_spec = volume_object_evaluateInput  
    output_spec = volume_object_evaluateOutput
    _cmd = "volume_object_evaluate"
    _suffix="_surf-intersect"
    _ext=".txt"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_outputs(self.inputs.vol_file)
        return super(volume_object_evaluateCommand, self)._parse_inputs(skip=skip)
    
    def _gen_outputs(self, fn) :
        fn_split = os.path.splitext(fn)
        return os.getcwd() + os.sep +  os.path.basename( fn_split[0] ) + self._suffix + self._ext

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_outputs(self.inputs.vol_file)

        outputs["out_file"] = self.inputs.out_file
        return outputs


