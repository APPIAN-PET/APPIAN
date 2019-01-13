import os
import ntpath
import nipype.pipeline.engine as pe


import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from Extra.base import MINCCommand, MINCCommandInputSpec

def read_dft(in_fn) :
    read=False
    times=[]
    with open(in_fn) as f :
        for l in f.readlines() :
            if read :
                times += [l.split()]
            
            if 'Times' in l :
                read=True
    return times

def max_time_dft(in_fn) :
    times = read_dft(in_fn)
    n=len(times)-1
    max_time = times[n][1]
    return float(max_time)

def min_time_dft(in_fn) :
    times = read_dft(in_fn)
    min_time = times[0][0]
    return float(min_time)


class img2dftOutput(TraitedSpec):
    out_file = File(argstr=" %s", position=-1,  desc="Patlak plot ki parametric image.")

class img2dftInput(MINCCommandInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-3, desc="PET file")
    mask_file = File(exists=True, argstr="%s", position=-2, desc="Reference file")


class img2dftCommand(MINCCommand):
    input_spec =  img2dftInput
    output_spec = img2dftOutput

    _cmd = "img2dft" 
    _file_type = ".dft" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) 
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + self._file_type

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(img2dftCommand, self)._parse_inputs(skip=skip)


class tacunitOutput(TraitedSpec):
    in_file = File(argstr=" %s", position=-1,  desc="dft image.")


class tacunitInput(MINCCommandInputSpec):
    in_file= File(exists=True, argstr="%s", position=-1, desc="dft file")
    xconv = traits.Str(argstr="-xconv=%s", position=-2, desc="Convert x (time) axis")
    yconv = traits.Str(argstr="-yconv=%s", position=-3, desc="Convert y (radioactivity) axis")
    x = traits.Bool(argstr="-x", position=-4,desc="Print x (time) axis")
    y = traits.Bool(argstr="-y", position=-5,desc="Print y (radioactivity) axis")

class tacunitCommand(MINCCommand):
    input_spec =  tacunitInput
    output_spec = tacunitOutput

    _cmd = "tacunit" 
    _file_type = ".dft" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["in_file"] = self.inputs.in_file
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        return super(tacunitCommand, self)._parse_inputs(skip=skip)

class img2dftOutput(TraitedSpec):
    out_file = File(argstr=" %s", position=-1,  desc="Patlak plot ki parametric image.")

class img2dftInput(MINCCommandInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-3, desc="PET file")
    mask_file = File(exists=True, argstr="%s", position=-2, desc="Reference file")


class img2dftCommand(MINCCommand):
    input_spec =  img2dftInput
    output_spec = img2dftOutput

    _cmd = "img2dft" 
    _file_type = ".dft" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) 
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + self._file_type

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(img2dftCommand, self)._parse_inputs(skip=skip)


class img2dft_unit_conversion(BaseInterface) :
    input_spec =  img2dftInput
    output_spec = img2dftOutput

    def _run_interface(self, runtime) :

        img2dft = img2dftCommand()
        img2dft.inputs.in_file = self.inputs.in_file
        img2dft.inputs.mask_file = self.inputs.mask_file
        img2dft.run()
        print(img2dft.cmdline)

        convert_time = tacunitCommand()
        convert_time.inputs.in_file = img2dft.inputs.out_file
        convert_time.inputs.xconv="min"
        convert_time.run()
        print("")
        print("")
        print(convert_time.cmdline)
        print("")
        print("")
        self.inputs.out_file = convert_time.inputs.in_file
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

