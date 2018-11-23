from Extra.base import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined, CommandLineInputSpec, CommandLine)
import ntpath
import os
class quantificationCommand(CommandLine):

    def _list_outputs(self):
        print("_list_outputs")
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile, _suffix):
        print("_gen_output")
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        print("_parse_inputs")
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(quantificationCommand, self)._parse_inputs(skip=skip)
