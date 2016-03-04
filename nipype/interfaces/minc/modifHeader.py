import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)







class ModifyHeaderOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class ModifyHeaderInput(BaseInterfaceInputSpec):
    in_file = File(position=-1, argstr="%s", mandatory=True, desc="Image")

    opt_string = traits.Str(argstr="%s", mandatory=True, desc="Option defining the infos to print out")
    sinsert = traits.Bool(argstr="-sinsert", usedefault=True, default_value=True, desc="Insert a string attribute")
    dinsert = traits.Bool(argstr="-dinsert", usedefault=True, default_value=True, desc="Insert a double precision attribute")
    sappend = traits.Bool(argstr="-sappend", usedefault=True, default_value=True, desc="Append a string attribute")
    dappend = traits.Bool(argstr="-dappend", usedefault=True, default_value=True, desc="Insert a double precision attribute")
    delete = traits.Bool(argstr="-delete", usedefault=True, default_value=True, desc="Delete an attribute")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ModifyHeaderRunning(BaseInterface):
    input_spec = ModifyHeaderInput
    output_spec = ModifyHeaderOutput


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs



