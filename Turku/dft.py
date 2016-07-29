import os
import ntpath
import nipype.pipeline.engine as pe


import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec

class img2dftOutput(TraitedSpec):
    out_file = File(argstr=" %s", position=-1,  desc="Patlak plot ki parametric image.")

class img2dftInput(MINCCommandInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")


class img2dftCommand(MINCCommand):
    input_spec =  img2dftInput
    output_spec = img2dftOutput

    _cmd = "img2dft" 
    _file_type = ".dft" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) 
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + self._file_type

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(img2dftCommand, self)._parse_inputs(skip=skip)