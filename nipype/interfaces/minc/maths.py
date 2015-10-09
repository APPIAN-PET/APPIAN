import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)






class MathsOutput(TraitedSpec):
    out_file = File(exists=True, desc="image to write after calculations")


class MathsInput(MINCCommandInputSpec):

    input_file = File(position=2, argstr="%s", exists=True, mandatory=True, desc="image to operate on")
    out_file = File(position=-1, argstr="%s", mandatory=True, desc="image to operate on")

    _opmaths = ["add", "sub", "mult", "div", "pd", "eq", "ne", "ge", "gt", "and", "or", "not", "isnan", 'nisnan']
    operation = traits.Enum(*_opmaths, mandatory=True, argstr="-%s", position=3, desc="math operations to perform")
    operand_file = File(exists=True, argstr="%s", mandatory=True, position=4, desc="second image to perform operation with")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")


class MathsCommand(MINCCommand):
    _cmd = "mincmath"
    _suffix = "_maths"
    input_spec = MathsInput
    output_spec = MathsOutput
    

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







class ConstantMathsInput(MINCCommandInputSpec):
    input_file = File(position=2, argstr="%s", exists=True, mandatory=True, desc="image to operate on")
    out_file = File(position=-1, argstr="%s", mandatory=True, desc="image to operate on")


    _opmaths = ["add", "sub", "mult", "div"]
    operation = traits.Enum(*_opmaths, mandatory=True, argstr="-%s", position=3, desc="math operations to perform")
    opt_constant = traits.Str("-const", mandatory=True, argstr="%s", position=4, desc="-const")
    operand_value = traits.Float(exists=True, argstr="%.8f", mandatory=True, position=5, xor=["operand_value"], desc="value to perform operation with")

class ConstantMathsCommand(MINCCommand):
    _cmd = "mincmath"
    _suffix = "_maths"
    input_spec = ConstantMathsInput
    output_spec = MathsOutput

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










class Constant2MathsInput(MINCCommandInputSpec):
    input_file = File(position=2, argstr="%s", exists=True, mandatory=True,
                   desc="image to operate on")

    out_file = File(position=-1, argstr="%s", mandatory=True,
                   desc="image to operate on")


    _opmaths = ["add", "sub", "mult", "div"]
    operation = traits.Enum(*_opmaths, mandatory=True, argstr="-%s",
                           position=3,desc="math operations to perform")
    opt_constant = traits.Str(argstr="%s", position=4, desc="-const2")
    operand_value = traits.Float(exists=True, argstr="%.8f", mandatory=True, position=5, xor=["operand_value"],
                                 desc="value to perform operation with")
    operand_value2 = traits.Float(exists=True, argstr="%.8f", mandatory=True, position=6, xor=["operand_value2"],
                                 desc="2nde value to perform operation with")

class Constant2MathsCommand(MINCCommand):
    _cmd = "mincmath"
    _suffix = "_maths"
    input_spec = Constant2MathsInput
    output_spec = MathsOutput

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