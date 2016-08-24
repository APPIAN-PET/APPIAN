import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)

class ResampleOutput(TraitedSpec):
    out_file = File(exists=True, desc="resampled image")

class ResampleInput(MINCCommandInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="image to resample")
    out_file = File(position=1, argstr="%s", desc="resampled image")
    model_file = File(position=2, argstr="-like %s", mandatory=False, desc="model image")
    
    transformation = File(argstr="-transformation %s", desc="image to resample")
    interpolation = traits.Enum('trilinear', 'tricubic', 'nearest_neighbour', 'sinc', argstr="-%s", desc="interpolation type", default='trilinear')
    invert = traits.Enum('invert_transformation', 'noinvert_transformation', argstr="-%s", desc="invert transfomation matrix", default='noinvert_transformation')
    
    use_input_sampling = traits.Bool(argstr="-use_input_sampling",  default_value=False, desc="Use sampling of input image")
    tfm_input_sampling = traits.Bool(argstr="-tfm_input_sampling", default_value=False, desc="Use sampling of transformation")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ResampleCommand(MINCCommand):
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

class param2xfmInput(MINCCommandInputSpec):
    out_file = File(position=-1, argstr="%s", desc="resampled image")
  
    rotation = traits.Str(argstr="-rotation %s", desc="image rotation x,y,z")
    translation = traits.Str(argstr="-translation %s", desc="image translation x,y,z")
    shears = traits.Str(argstr="-shears %s", desc="image shears x,y,z")
    scales = traits.Str(argstr="-scales %s", desc="image scales x,y,z")
    center = traits.Str(argstr="-center %s", desc="image center x,y,z")

    clobber = traits.Bool(argstr="-clobber", position=1, usedefault=True, default_value=True, desc="Overwrite output file")


class param2xfmCommand(MINCCommand):
    _cmd = "param2xfm"
    input_spec = param2xfmInput
    output_spec = param2xfmOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            dname = os.getcwd()
            self.inputs.out_file = dname + os.sep + "param.xfm"

        return super(param2xfmCommand, self)._parse_inputs(skip=skip)


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


