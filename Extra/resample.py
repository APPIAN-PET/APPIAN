import os
import numpy as np
import re
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)

class ResampleOutput(TraitedSpec):
#    out_file = File(exists=True, desc="resampled image")
    out_file = File(desc="resampled image")

class ResampleInput(CommandLineInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="image to resample")
    out_file = File(position=1, argstr="%s", desc="resampled image")
    model_file = File(position=2, argstr="-like %s", mandatory=False, desc="model image")
    
    transformation = File(argstr="-transformation %s", desc="image to resample")
    interpolation = traits.Enum('trilinear', 'tricubic', 'nearest_neighbour', 'sinc', argstr="-%s", desc="interpolation type", default='trilinear')
    invert = traits.Enum('invert_transformation', 'noinvert_transformation', argstr="-%s", desc="invert transfomation matrix", default='noinvert_transformation')
    
    use_input_sampling = traits.Bool(argstr="-use_input_sampling",  default_value=False, desc="Use sampling of input image")
    tfm_input_sampling = traits.Bool(argstr="-tfm_input_sampling", default_value=False, desc="Use sampling of transformation")
    step = traits.Str(argstr="-step %s", desc="Step size in (X, Y, Z) dims.")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ResampleCommand(CommandLine):
    _cmd = "mincresample"
    _suffix = "_resample"
    input_spec = ResampleInput
    output_spec = ResampleOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix)

        return super(ResampleCommand, self)._parse_inputs(skip=skip)


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


class param2xfmOutput(TraitedSpec):
    out_file = File(exists=True, desc="resampled image")

class param2xfmInput(CommandLineInputSpec):
    out_file = File(position=-1, argstr="%s", desc="resampled image")
  
    rotation = traits.Str(argstr="-rotation %s", mandatory=False, default=None, desc="image rotation x,y,z")
    translation = traits.Str(argstr="-translation %s", mandatory=False, default=None, desc="image translation x,y,z")
    shears = traits.Str(argstr="-shears %s",  mandatory=False, default=None, desc="image shears x,y,z")
    scales = traits.Str(argstr="-scales %s",  mandatory=False, default=None, desc="image scales x,y,z")
    center = traits.Str(argstr="-center %s",  mandatory=False, default=None, desc="image center x,y,z")

    clobber = traits.Bool(argstr="-clobber", position=1, usedefault=True, default_value=True, desc="Overwrite output file")


class param2xfmCommand(CommandLine):
    _cmd = "param2xfm"
    input_spec = param2xfmInput
    output_spec = param2xfmOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []


        if not isdefined(self.inputs.out_file):
            dname = os.getcwd()
            params="" #Create label for output file based on the parameters applied to image
            if isdefined(self.inputs.rotation): params = params + "_rtn="+self.inputs.rotation
            if isdefined(self.inputs.translation): params = params + "_trn="+self.inputs.translation
            if isdefined(self.inputs.shears): params = params + "_shr="+self.inputs.shears
            if isdefined(self.inputs.scales): params = params + "_scl="+self.inputs.scales
            if isdefined(self.inputs.center): params = params + "_cnt="+self.inputs.center
            self.inputs.out_file = dname + os.sep + "param"+params+".xfm"
        
        comma=lambda x : re.sub(',', ' ', x)
        if isdefined(self.inputs.rotation): self.inputs.rotation=comma(self.inputs.rotation)
        if isdefined(self.inputs.translation): self.inputs.translation=comma(self.inputs.translation)
        if isdefined(self.inputs.shears): self.inputs.shears=comma(self.inputs.shears)
        if isdefined(self.inputs.scales): self.inputs.scales=comma(self.inputs.scales)
        if isdefined(self.inputs.center): self.inputs.center=comma(self.inputs.center)
        return super(param2xfmCommand, self)._parse_inputs(skip=skip)


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


