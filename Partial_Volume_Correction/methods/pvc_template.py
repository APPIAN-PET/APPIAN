from nipype.interfaces.base import TraitedSpec, File, traits
from Extra.base import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.base import TraitedSpec, File, traits
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import ntpath
import os
class pvcCommand(MINCCommand):
    #these are temporary placeholders, to be replaced by actual <_cmd> and <_suffix> values
    _cmd="pvc"
    _suffix="pvc"
    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + self._suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
	    skip = []
        if not isdefined(self.inputs.out_file):
	    self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(pvcCommand, self)._parse_inputs(skip=skip)
