from glob import glob
import os
import warnings

from nipype.interfaces.base import (CommandLine, traits, File, CommandLineInputSpec, isdefined)

# class Info(object):
#
#     ftypes = {'MINC': '.mnc',
#               'MINC_GZ': '.mnc.gz'}
#
#     @classmethod
#     def output_type(cls):
#         return 'MINC_GZ'

class MINCCommandInputSpec(CommandLineInputSpec):
    input_file = File(desc='input File', exists = True, mandatory = True, argstr="%s")


class MINCCommandOutputSpec(CommandLineInputSpec):
    # output_type = traits.Enum('MINC', Info.ftypes.keys(), desc='MINC output type')
    output_file = File(desc='output File', exists = True)


class MINCCommand(CommandLine):
    input_spec = MINCCommandInputSpec
    output_spec = MINCCommandOutputSpec

    # def __init__(self, **inputs):
    #     super(MINCCommand, self).__init__(**inputs)
    #     self.inputs.on_trait_change(self._output_update, 'output_type')
    #
    #     if self._output_type is None:
    #         self._output_type = Info.output_type()
    