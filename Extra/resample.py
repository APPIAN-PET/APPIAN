import os, ntpath
import numpy as np
import re
from nipype.interfaces.base import CommandLine, CommandLineInputSpec, BaseInterface
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
    keep_real_range=traits.Bool(argstr="-keep_real_range",  default_value=True, use_default=True, desc="Use sampling of input image")
    use_input_sampling = traits.Bool(argstr="-use_input_sampling",  default_value=False, desc="Use sampling of input image")
    tfm_input_sampling = traits.Bool(argstr="-tfm_input_sampling", default_value=False, desc="Use sampling of transformation")
    step = traits.Str(argstr="-step %s", desc="Step size in (X, Y, Z) dims.")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ResampleCommand(CommandLine):
    _cmd = "mincresample"
    _suffix = "_rsl"
    input_spec = ResampleInput
    output_spec = ResampleOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_filename(self.inputs.in_file, suffix=self._suffix)

        return super(ResampleCommand, self)._parse_inputs(skip=skip)


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, basefile, suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + suffix + fname_list[1]

    #def _gen_filename(self, name):
    #    if name == "out_file":
    #        return self._list_outputs()["out_file"]
    #    return None


class param2xfmOutput(TraitedSpec):
    out_file = File(exists=True, desc="resampled image")

class param2xfmInput(CommandLineInputSpec):
    out_file = File(position=-1, argstr="%s", desc="resampled image")

    rotation = traits.Str(argstr="-rotation %s", mandatory=False, default=None, desc="image rotation x,y,z")
    translation = traits.Str(argstr="-translation %s", mandatory=False, default=None, desc="image translation x,y,z")
    shears = traits.Str(argstr="-shears %s",  mandatory=False, default=None, desc="image shears x,y,z")
    scales = traits.Str(argstr="-scales %s",  mandatory=False, default=None, desc="image scales x,y,z")
    center = traits.Str(argstr="-center %s",  mandatory=False, default=None, desc="image center x,y,z")
    transformation = traits.Str(argstr="%s", mandatory=False, default=None, desc="generic string for parameters")
    clobber = traits.Bool(argstr="-clobber", position=1, usedefault=True, default_value=True, desc="Overwrite output file")


class param2xfmCommand(CommandLine):
    _cmd = "param2xfm"
    input_spec = param2xfmInput
    output_spec = param2xfmOutput

    def _gen_output(self):
        dname = os.getcwd()
        params="" #Create label for output file based on the parameters applied to image
        if isdefined(self.inputs.rotation): params = params + "_rtn="+self.inputs.rotation
        if isdefined(self.inputs.translation): params = params + "_trn="+self.inputs.translation
        if isdefined(self.inputs.shears): params = params + "_shr="+self.inputs.shears
        if isdefined(self.inputs.scales): params = params + "_scl="+self.inputs.scales
        if isdefined(self.inputs.center): params = params + "_cnt="+self.inputs.center
        out_file = dname + os.sep + "param"+params+".xfm"
        out_file = re.sub(' ',',',out_file)
        return out_file


    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output()

        comma=lambda x : re.sub(',', ' ', x)
        if isdefined(self.inputs.rotation): self.inputs.rotation=comma(self.inputs.rotation)
        if isdefined(self.inputs.translation): self.inputs.translation=comma(self.inputs.translation)
        if isdefined(self.inputs.shears): self.inputs.shears=comma(self.inputs.shears)
        if isdefined(self.inputs.scales): self.inputs.scales=comma(self.inputs.scales)
        if isdefined(self.inputs.center): self.inputs.center=comma(self.inputs.center)
        return super(param2xfmCommand, self)._parse_inputs(skip=skip)


    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.params)

        outputs["out_file"] = self.inputs.out_file
        return outputs


    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

class param2xfmInterfaceOutput(TraitedSpec):
    out_file = File(exists=True, desc="resampled image")

class param2xfmInterfaceInput(CommandLineInputSpec):
    out_file = File(position=-1, argstr="%s", desc="resampled image")
    transformation = traits.List(desc="Transformation to apply")

transform_exec_dict={"angle":" -rotations ", "offset":" -translation ", "shear":" -shears ", "scale":" -scales ", "center":" -center "}
transform_file_dict={"angle":" _rtn=","offset":" _trn=","shear":" _shr=", "scale":" _scl=", "center":" _cnt="}
class param2xfmInterfaceCommand(BaseInterface):
    input_spec = param2xfmInterfaceInput
    output_spec = param2xfmInterfaceOutput

    def _run_interface(self, runtime):
        transformation = self.inputs.transformation
        exec_params = ""
        file_params = ""
        for item in transformation :
            transform_type  = item[0]
            transform_param = item[1]
            exec_params += transform_exec_dict[transform_type] + transform_param
            file_params += transform_file_dict[transform_type] + transform_param

        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_output(file_params)

        paramNode = param2xfmCommand();
        paramNode.inputs.transformation = exec_params
        paramNode.inputs.out_file = self.inputs.out_file
        print paramNode.cmdline
        paramNode.run()
        return runtime

    def _gen_output(self, params):
        dname = os.getcwd()
        params = re.sub(" ", "", params)
        out_file = dname + os.sep + "param"+params+".xfm"
        out_file = re.sub(' ',',',out_file)
        return out_file

    def _list_outputs(self):
        outputs = self.output_spec().get()
        #if not isdefined(self.inputs.out_file):
        #    self.inputs.out_file = self._gen_output(self.inputs.params)
        outputs["out_file"] = self.inputs.out_file
        return outputs
