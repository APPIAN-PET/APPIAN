import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, CommandLine,  CommandLineInputSpec , File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.interfaces.base import CommandLine, CommandLineInputSpec

class imgunitInput(CommandLineInputSpec): #CommandLineInputSpec):
    in_file = File(argstr="%s", position=-1, desc="Input image.")
    out_file = File(desc="Output image.")
    u = traits.Str(argstr="-u=%s", position=1, desc="-u=<New unit; e.g. Bq/cc or kBq/ml>. Set the unit, but does NOT change the pixel values.")
    us = traits.Str(argstr="-us=%s", position=1, desc="-us=<New unit; e.g. Bq/cc or kBq/ml>. Set the unit only if unit is not originally defined in the image. This does NOT change the pixel values.")
    uc = traits.Str(argstr="-uc=%s", position=1, desc="-uc=<New unit; e.g. Bq/cc or kBq/ml>. Converts pixel values to the specified unit.")


class imgunitOutput(TraitedSpec):
    out_file = File(desc="Output image.")


class imgunitCommand(CommandLine): #CommandLine): 
    input_spec =  imgunitInput
    output_spec = imgunitOutput

    _cmd = "imgunit" 

    def _parse_inputs(self, skip=None):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self.inputs.in_file
        return super(imgunitCommand, self)._parse_inputs(skip=skip)
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs
    
