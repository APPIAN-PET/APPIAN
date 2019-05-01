import os
import ntpath
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from Extra.utils import splitext, check_gz
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, CommandLine,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import json




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

class img2dftInput(BaseInterfaceInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-3, desc="PET file")
    mask_file = File(exists=True, argstr="%s", position=-2, desc="Reference file")


class img2dftCommand(CommandLine):
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
        fname_list = splitext(fname) 
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


class tacunitInput(BaseInterfaceInputSpec):
    in_file= File(exists=True, argstr="%s", position=-1, desc="dft file")
    xconv = traits.Str(argstr="-xconv=%s", position=-2, desc="Convert x (time) axis")
    yconv = traits.Str(argstr="-yconv=%s", position=-3, desc="Convert y (radioactivity) axis")
    x = traits.Bool(argstr="-x", position=-4,desc="Print x (time) axis")
    y = traits.Bool(argstr="-y", position=-5,desc="Print y (radioactivity) axis")

class tacunitCommand(CommandLine):
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

class img2dftInput(BaseInterfaceInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True,mandatory=True, argstr="%s", position=-3, desc="PET file")
    mask_file = File(exists=True,mandatory=True, argstr="%s", position=-2, desc="Reference file")
    pet_header_json = File(exists=True,  desc="Header file")


class img2dftCommand(CommandLine):
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
        fname_list = splitext(fname) 
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
        
        in_file = check_gz(self.inputs.in_file)
        mask_file = check_gz(self.inputs.mask_file)

        img2dft = img2dftCommand()
        img2dft.inputs.in_file = in_file
        img2dft.inputs.mask_file = mask_file
        img2dft.inputs.out_file = os.getcwd() + os.sep + splitext(os.path.basename(self.inputs.in_file))[0] + '.dft'
        img2dft.run()
        print(img2dft.cmdline)

        header = json.load(open(self.inputs.pet_header_json,'r'))
        
        frame_times = header["Time"]["FrameTimes"]["Values"]

        c0=c1=1. #Time unit conversion variables. Time should be in seconds
        if header["Time"]["FrameTimes"]["Units"][0] == 's' :
            c0=1./60
        elif header["Time"]["FrameTimes"]["Units"][0] == 'h' :
            c0=60.
        
        if header["Time"]["FrameTimes"]["Units"][1] == 's' :
            c1=1/60.
        elif header["Time"]["FrameTimes"]["Units"][1] == 'h' :
            c1=60.

        line_counter=-1
        newlines=''
        with open(img2dft.inputs.out_file, 'r') as f :
            for line in f.readlines() :
                print(line)
                if 'Times' in line : 
                    line_counter=0
                    line=line.replace('sec','min')
                    newlines += line
                    continue 

                if line_counter >= 0 :
                    line_split = line.split('\t')
                    line_split[0] = frame_times[line_counter][0] * c0
                    line_split[1] = frame_times[line_counter][1] * c1
                    line_split_str = [ str(i) for i in line_split ]
                    newlines+='\t'.join(line_split_str)
                    line_counter += 1
                else : 
                    newlines+=line
        print(newlines)
        
        with open(img2dft.inputs.out_file, 'w') as f :
            f.write(newlines)
        #convert_time = tacunitCommand()
        #convert_time.inputs.in_file = img2dft.inputs.out_file
        #convert_time.inputs.xconv="min"
        #convert_time.run()
        
        self.inputs.out_file = img2dft.inputs.out_file
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

