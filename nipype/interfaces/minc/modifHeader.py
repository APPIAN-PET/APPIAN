import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)


class ModifyHeaderOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class ModifyHeaderInput(MINCCommandInputSpec):
    in_file = File(position=-3, argstr="%s", mandatory=True, desc="Image")

    sinsert = traits.Bool(argstr="-sinsert", default_value=False, desc="Insert a string attribute")
    dinsert = traits.Bool(argstr="-dinsert", default_value=False, desc="Insert a double precision attribute")
    sappend = traits.Bool(argstr="-sappend", default_value=False, desc="Append a string attribute")
    dappend = traits.Bool(argstr="-dappend", default_value=False, desc="Append a double precision attribute")
    delete = traits.Bool(argstr="-delete", default_value=False, desc="Delete an attribute")
    opt_string = traits.Str(argstr="%s", desc="Option defining the infos to print out")

class ModifyHeaderCommand(MINCCommand):
    _cmd = "minc_modify_header"
    input_spec = ModifyHeaderInput
    output_spec = ModifyHeaderOutput


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs

