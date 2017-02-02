import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, CommandLine,  CommandLineInputSpec , File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec

class imgunitInput(CommandLineInputSpec): #MINCCommandInputSpec):
    in_file = File(argstr="%s", position=-1, desc="Input image.")

    u = traits.Str(argstr="-u=%s", position=1, desc="-u=<New unit; e.g. Bq/cc or kBq/ml>. Set the unit, but does NOT change the pixel values.")
    us = traits.Str(argstr="-us=%s", position=1, desc="-us=<New unit; e.g. Bq/cc or kBq/ml>. Set the unit only if unit is not originally defined in the image. This does NOT change the pixel values.")
    uc = traits.Str(argstr="-uc=%s", position=1, desc="-uc=<New unit; e.g. Bq/cc or kBq/ml>. Converts pixel values to the specified unit.")


class imgunitOutput(TraitedSpec):
    in_file = File(argstr="%s", position=-1, desc="Input image.")


class imgunitCommand(CommandLine): #MINCCommand): 
    input_spec =  imgunitInput
    output_spec = imgunitOutput

    _cmd = "imgunit" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["in_file"] = self.inputs.in_file
        return outputs
    
