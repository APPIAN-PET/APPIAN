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
    header = traits.Dict(argstr="MINC header for PET image, stored as dictionary")

class ModifyHeaderCommand(MINCCommand):
    _cmd = "minc_modify_header"
    input_spec = ModifyHeaderInput
    output_spec = ModifyHeaderOutput


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs



class FixHeaderInput(ModifyHeaderInput):
    zstart = traits.Float(argstr="-dinsert zspace:start=%f",  desc="Replace start value for zspace")
    ystart = traits.Float(argstr="-dinsert yspace:start=%f",  desc="Replace start value for yspace")
    xstart = traits.Float(argstr="-dinsert xspace:start=%f",  desc="Replace start value for xspace")
    zstep = traits.Float(argstr="-dinsert zspace:step=%f",  desc="Replace start value for zstep")
    ystep = traits.Float(argstr="-dinsert yspace:step=%f",  desc="Replace start value for ystep")
    xstep = traits.Float(argstr="-dinsert xspace:step=%f",  desc="Replace start value for xstep")
    header = traits.Dict(desc="MINC header for PET image stored in dictionary.")

class FixHeaderCommand(ModifyHeaderCommand):
    input_spec = FixHeaderInput

    def _parse_inputs(self, skip=None):
        header=self.inputs.header
        if skip is None:
            skip = []
        self.inputs.zstart = header["zspace"]["start"][0]
        self.inputs.ystart = header["yspace"]["start"][0]
        self.inputs.xstart = header["xspace"]["start"][0]
        self.inputs.zstep = header["zspace"]["step"][0]
        self.inputs.ystep = header["yspace"]["step"][0]
        self.inputs.xstep = header["xspace"]["step"][0]

        return super(FixHeaderCommand, self)._parse_inputs(skip=skip)