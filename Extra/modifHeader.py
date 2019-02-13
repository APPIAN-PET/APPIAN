import os
import numpy as np
import json
import shutil
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import pyminc.volumes.factory as pyminc

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

class FixCosinesOutput(TraitedSpec):
    out_file = File(desc="Image with fixed cosines")

#class FixHeaderInput(ModifyHeaderInput):
class FixCosinesInput(CommandLineInputSpec):
    out_file = File(argstr="%s", position=-1, desc="Image with fixed cosines")
    in_file = File(argstr="%s", position=-2, desc="Image")
    keep_real_range=traits.Bool(argstr="-keep_real_range",position=-4, use_default=False, default_value=True)
    two=traits.Bool(argstr="-2",position=-5, use_default=True, default_value=True)
    dircos=traits.Bool(argstr="-dircos 1 0 0 0 1 0 0 0 1",position=-3, use_default=True, default_value=True)

#class FixHeaderCommand(ModifyHeaderCommand):
class FixCosinesCommand(CommandLine):
    input_spec = FixCosinesInput
    output_spec = FixCosinesOutput
    _cmd = "mincresample"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = os.getcwd()+os.sep+os.path.splitext(os.path.basename(self.inputs.in_file))[0]+'_cosFixed.mnc'

        return super( FixCosinesCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = os.getcwd()+os.sep+os.path.splitext(os.path.basename(self.inputs.in_file))[0]+'_cosFixed.mnc'
        outputs["out_file"] = self.inputs.out_file
        return outputs



class FixHeaderOutput(TraitedSpec):
    output_file = File(desc="Image after centering")

#class FixHeaderInput(ModifyHeaderInput):
class FixHeaderInput(CommandLineInputSpec):
    tstart = traits.Float(argstr="-dinsert time:start=%f",  desc="Replace start value for time")
    zstart = traits.Float(argstr="-dinsert zspace:start=%f",  desc="Replace start value for zspace")
    ystart = traits.Float(argstr="-dinsert yspace:start=%f",  desc="Replace start value for yspace")
    xstart = traits.Float(argstr="-dinsert xspace:start=%f",  desc="Replace start value for xspace")
    tstep = traits.Float(argstr="-dinsert time:step=%f",  desc="Replace start value for time")
    zstep = traits.Float(argstr="-dinsert zspace:step=%f",  desc="Replace start value for zstep")
    ystep = traits.Float(argstr="-dinsert yspace:step=%f",  desc="Replace start value for ystep")
    xstep = traits.Float(argstr="-dinsert xspace:step=%f",  desc="Replace start value for xstep")
    header = traits.File(desc="MINC header for PET image stored in dictionary.")
    output_file = File(desc="Image after centering")
    in_file = File(argstr="%s", position=1, desc="Image after centering")
    time_only = traits.Bool(usedefault=True, default_value=False)
class FixHeaderCommand(CommandLine):
    input_spec = FixHeaderInput
    output_spec = FixHeaderOutput
    _cmd = "minc_modify_header"
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_file"] = self.inputs.in_file
        return outputs

    def _parse_inputs(self, skip=None):
        self.inputs.output_file = self.inputs.in_file #
        header=self.inputs.header
        if skip is None:
            skip = []
        data = json.load(open( header ,"rb"))


        vol=pyminc.volumeFromFile(self.inputs.in_file)
        dims = vol.getDimensionNames()
        if 'time' in dims :
            #See if there is a start time defined, else set to 0
            try :
                data["time"]["start"][0]
                self.inputs.tstart = data["time"]["start"][0]
            except KeyError:
                self.inputs.tstart = 0

            try :
                data["time"]["start"][0]
                self.inputs.tstep = data["time"]["step"][0]
            except KeyError :
                self.inputs.tstep = 1

        if not self.inputs.time_only :
            self.inputs.zstart = data["zspace"]["start"][0]
            self.inputs.ystart = data["yspace"]["start"][0]
            self.inputs.xstart = data["xspace"]["start"][0]
            self.inputs.zstep  = data["zspace"]["step"][0]
            self.inputs.ystep  = data["yspace"]["step"][0]
            self.inputs.xstep  = data["xspace"]["step"][0]

        return super(FixHeaderCommand, self)._parse_inputs(skip=skip)


class FixHeaderLinkInput(CommandLineInputSpec):
    tstart = traits.Float(argstr="-dinsert time:start=%f",  desc="Replace start value for time")
    zstart = traits.Float(argstr="-dinsert zspace:start=%f",  desc="Replace start value for zspace")
    ystart = traits.Float(argstr="-dinsert yspace:start=%f",  desc="Replace start value for yspace")
    xstart = traits.Float(argstr="-dinsert xspace:start=%f",  desc="Replace start value for xspace")
    tstep = traits.Float(argstr="-dinsert time:step=%f",  desc="Replace start value for time")
    zstep = traits.Float(argstr="-dinsert zspace:step=%f",  desc="Replace start value for zstep")
    ystep = traits.Float(argstr="-dinsert yspace:step=%f",  desc="Replace start value for ystep")
    xstep = traits.Float(argstr="-dinsert xspace:step=%f",  desc="Replace start value for xstep")
    header = traits.File(desc="MINC header for PET image stored in dictionary.")
    output_file = File(desc="Image after centering")
    in_file = File(argstr="%s", position=1, desc="Image after centering")
    time_only = traits.Bool(default_value=False)

class FixHeaderLinkOutput(TraitedSpec):
    output_file = File(desc="Image after centering")

class FixHeaderLinkCommand(BaseInterface):
    input_spec = FixHeaderLinkInput
    output_spec = FixHeaderLinkOutput

    def _run_interface(self, runtime):
        self.inputs.output_file = os.getcwd() + os.sep + os.path.basename(self.inputs.in_file)
        #FIXME : Need a better solution for fixing file headers bc this uses a lot of memory
        shutil.copy(self.inputs.in_file, self.inputs.output_file)

        fix_header_node = FixHeaderCommand()
        fix_header_node.inputs.in_file = self.inputs.output_file
        fix_header_node.inputs.header = self.inputs.header
        fix_header_node.run()

        #os.symlink(self.inputs.in_file, self.inputs.output_file)
        print("\n\nRunning FixHeaderLinkCommand\n\n")
        #print(self.inputs.in_file, self.inputs.output_file)

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_file"] = self.inputs.output_file
        return outputs
