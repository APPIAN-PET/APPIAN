import os
import numpy as np

#from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec
from mincbase import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    isdefined)


class MathsInput(MINCCommandInputSpec):
    in_file = File(position=2, argstr="%s", exists=True, mandatory=True,
                   desc="image to operate on")

class MathsOutput(TraitedSpec):
#    out_file = File(exists=True, desc="image written after calculations")
    out_file = File(genfile=True, position=3, argstr="%s",
                    desc="image to write after calculations", hash_files=False)

class MathsCommand(MINCCommand):
    _cmd = "mincmath"
    _suffix = "_maths"
    input_spec = MathsInput
    output_spec = MathsOutput

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        if not isdefined(self.inputs.out_file):
            outputs["out_file"] = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
        outputs["out_file"] = os.path.abspath(outputs["out_file"])
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None






class OperationsMathsInput(MathsInput):
    _opmaths = ["add", "sub", "mult", "div", "pd", "eq", "ne", "ge", "gt", "and", "or", "not", "isnan", 'nisnan']
    operation = traits.Enum(*_opmaths, mandatory=True, argstr="-%s",
                            position=4,desc="math operations to perform")
    operand_file = File(exists=True, argstr="%s", mandatory=True,
                        position=5, xor=["operand_value"],
                        desc="second image to perform operation with")

class OperationsMaths(MathsCommand):
    input_spec = OperationsMathsInput



class ConstantMathsInput(MathsInput):
    constant = traits.Enum("constant", mandatory=True, argstr="-%s", position=4,
                           desc="constant to apply")
    operand_value = traits.Float(exists=True, argstr="%.8f", mandatory=True, position=5, xor=["operand_value"],
                                 desc="value to perform operation with")

class ConstantMaths(MathsCommand):
    input_spec = ConstantMathsInput

class Constant2MathsInput(MathsInput):
    constant2 = traits.Enum("constant2", mandatory=True, argstr="-%s", position=4,
                           desc="constants to apply")
    operand_value = traits.Float(exists=True, argstr="%.8f", mandatory=True, position=5, xor=["operand_value"],
                                 desc="value to perform operation with")
    operand_value2 = traits.Float(exists=True, argstr="%.8f", mandatory=True, position=6, xor=["operand_value2"],
                                 desc="2nde value to perform operation with")

class Constant2Maths(MathsCommand):
    input_spec = Constant2MathsInput