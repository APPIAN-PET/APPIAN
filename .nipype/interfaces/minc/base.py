from glob import glob
import os
import warnings

from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile
from nipype.interfaces.base import (CommandLine, traits, File, CommandLineInputSpec, isdefined)
from ..base import (traits, isdefined, CommandLine, CommandLineInputSpec, TraitedSpec, File, Directory, InputMultiPath, OutputMultiPath)

class Info(object):

    ftypes = {'MINC': '.mnc',
              'MINC_GZ': '.mnc.gz'}

    dtprecision = {'float_single'   : 'float',
                   'float_double'   : 'double',
                   'short_int'      : 'short',
                   'int'            : 'int',
                   'byte'           : 'byte',
                   }

    dtsign = {'signed'     : 'signed',
              'unsigned'   : 'unsigned'}


    @classmethod
    def output_type(cls):
        return 'MINC_GZ'

class MINCCommandInputSpec(CommandLineInputSpec):
    # input_file = File(desc='input File', exists = True, mandatory = True, argstr="%s")
    output_type = traits.Enum('MINC', Info.ftypes.keys(), desc='MINC output type')

# class MINCCommandOutputSpec(CommandLineInputSpec):
#     # output_type = traits.Enum('MINC', Info.ftypes.keys(), desc='MINC output type')
#     output_file = File(desc='output File', exists = True)


class MINCCommand(CommandLine):
    input_spec = MINCCommandInputSpec
    _output_type = None

    def __init__(self, **inputs):
        super(MINCCommand, self).__init__(**inputs)
        self.inputs.on_trait_change(self._output_update, 'output_type')

        if self._output_type is None:
            self._output_type = Info.output_type()
        
        if not isdefined(self.inputs.output_type):
            self.inputs.output_type = self._output_type
        else:
            self._output_update()

    def _output_update(self):
        self._output_type = self.inputs.output_type
        self.inputs.environ.update({'MINCOUTPUTTYPE': self.inputs.output_type})

    def _gen_fname(self, basename, cwd=None, suffix=None, change_ext=True,
                   ext=None):

        if basename == '':
            msg = 'Unable to generate filename for command %s. ' % self.cmd
            msg += 'basename is not set!'
            raise ValueError(msg)
        if cwd is None:
            cwd = os.getcwd()
        if ext is None:
            # ext = Info.output_type_to_ext(self.inputs.output_type)ftypes
            ext = Info.ftypes['MINC']
        if change_ext:
            if suffix:
                suffix = ''.join((suffix, ext))
            else:
                suffix = ext
        if suffix is None:
            suffix = ''
        fname = fname_presuffix(basename, suffix=suffix,
                                use_ext=False, newpath=cwd)
        return fname
