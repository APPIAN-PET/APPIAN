import os
import numpy as np
import json
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)


class ModifyHeaderOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class ModifyHeaderInput(CommandLineInputSpec):
    in_file = File(position=-1, argstr="%s", mandatory=True, desc="Image")
    out_file = File(desc="Image after centering")

    sinsert = traits.Bool(argstr="-sinsert", position=-3, default_value=False, desc="Insert a string attribute")
    dinsert = traits.Bool(argstr="-dinsert", position=-3, default_value=False, desc="Insert a double precision attribute")
    sappend = traits.Bool(argstr="-sappend", position=-3, default_value=False, desc="Append a string attribute")
    dappend = traits.Bool(argstr="-dappend", position=-3, default_value=False, desc="Append a double precision attribute")
    delete = traits.Bool(argstr="-delete", position=-3, default_value=False, desc="Delete an attribute")
    opt_string = traits.Str(argstr="%s", position=-2, desc="Option defining the infos to print out")
    header = traits.File(argstr="MINC header for PET image, stored as dictionary")

class ModifyHeaderCommand(CommandLine):
    _cmd = "minc_modify_header"
    input_spec = ModifyHeaderInput
    output_spec = ModifyHeaderOutput

    def _parse_inputs(self, skip=None):
        self.inputs.out_file = self.inputs.in_file
        return super( ModifyHeaderCommand, self)._parse_inputs(skip=skip)
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs


class FixHeaderOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

#class FixHeaderInput(ModifyHeaderInput):
class FixHeaderInput(CommandLineInputSpec):
    zstart = traits.Float(argstr="-dinsert zspace:start=%f",  desc="Replace start value for zspace")
    ystart = traits.Float(argstr="-dinsert yspace:start=%f",  desc="Replace start value for yspace")
    xstart = traits.Float(argstr="-dinsert xspace:start=%f",  desc="Replace start value for xspace")
    zstep = traits.Float(argstr="-dinsert zspace:step=%f",  desc="Replace start value for zstep")
    ystep = traits.Float(argstr="-dinsert yspace:step=%f",  desc="Replace start value for ystep")
    xstep = traits.Float(argstr="-dinsert xspace:step=%f",  desc="Replace start value for xstep")
    header = traits.File(desc="MINC header for PET image stored in dictionary.")
    out_file = File(desc="Image after centering")
    in_file = File(argstr="%s", position=1, desc="Image after centering")

#class FixHeaderCommand(ModifyHeaderCommand):
class FixHeaderCommand(CommandLine):
    input_spec = FixHeaderInput
    output_spec = FixHeaderOutput
    _cmd = "minc_modify_header"
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs

    def _parse_inputs(self, skip=None):
        self.inputs.out_file = self.inputs.in_file
        header=self.inputs.header
        if skip is None:
            skip = []
        data = json.load(open( header ,"rb"))

		try : 
			data["time"]["start"][0]
			self.inputs.tstart = data["time"]["start"[0]
		except KeyError : pass

		try : 
			data["time"]["start"][0]
			self.inputs.tstart = data["time"]["step"][0]
		except KeyError : pass

        self.inputs.zstart = data["zspace"]["start"][0]
        self.inputs.ystart = data["yspace"]["start"][0]
        self.inputs.xstart = data["xspace"]["start"][0]
        self.inputs.zstep  = data["zspace"]["step"][0]
        self.inputs.ystep  = data["yspace"]["step"][0]
        self.inputs.xstep  = data["xspace"]["step"][0]

        return super(FixHeaderCommand, self)._parse_inputs(skip=skip)

	


