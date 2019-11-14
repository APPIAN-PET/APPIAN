import os
import ntpath
import json
import datetime
import numpy as np
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
import nibabel as nib
from src.utils import splitext, check_gz
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, CommandLine, CommandLineInputSpec, BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)

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

class imgunitInput(CommandLineInputSpec): #CommandLineInputSpec):
    in_file = File(argstr="%s", position=-1, desc="Input image.")
    out_file = File(desc="Output image.")
    u = traits.Str(argstr="-u=%s", position=1, desc="-u=<New unit; e.g. Bq/cc or kBq/ml>. Set the unit, but does NOT change the pixel values.")
    us = traits.Str(argstr="-us=%s", position=1, desc="-us=<New unit; e.g. Bq/cc or kBq/ml>. Set the unit only if unit is not originally defined in the image. This does NOT change the pixel values.")
    uc = traits.Str(argstr="-uc=%s", position=1, desc="-uc=<New unit; e.g. Bq/cc or kBq/ml>. Converts pixel values to the specified unit.")


class imgunitOutput(TraitedSpec):
    out_file = File(desc="Output image.")


class imgunitCommand(CommandLine): #CommandLine): 
    input_spec =  imgunitInput
    output_spec = imgunitOutput

    _cmd = "imgunit" 

    def _parse_inputs(self, skip=None):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self.inputs.in_file
        return super(imgunitCommand, self)._parse_inputs(skip=skip)
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs


class e7emhdrInput(CommandLineInputSpec): #CommandLineInputSpec):
    in_file = File(argstr="%s", position=-2, desc="Input image.")
    out_file = File(desc="Output image.")
    isotope = traits.Str(argstr="isotope_halflife :=  %s", position=-1, desc="Set isotope half life")
    header= traits.File(exists=True, argstr="%s", desc="PET header file")

class e7emhdrOutput(TraitedSpec):
    out_file = File(desc="Output image.")


class e7emhdrCommand(CommandLine): #CommandLine): 
    input_spec =  e7emhdrInput
    output_spec = e7emhdrOutput

    _cmd = "e7emhdr" 

    def _parse_inputs(self, skip=None):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self.inputs.in_file
        return super(e7emhdrCommand, self)._parse_inputs(skip=skip)
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs


class e7emhdrInterface(BaseInterface): #CommandLine): 
    input_spec =  e7emhdrInput
    output_spec = e7emhdrOutput

    def _run_interface(self, runtime): 
        data = json.load( open( self.inputs.header, "rb" ) )
        e7emhdrNode = e7emhdrCommand() 
        e7emhdrNode.inputs.in_file = self.inputs.in_file

        e7emhdrNode.inputs.isotope = str(data["acquisition"]["radionuclide_halflife"])

        e7emhdrNode.run()
        self.inputs.out_file = self.inputs.in_file

        return runtime

    def _parse_inputs(self, skip=None):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self.inputs.in_file
        return super(e7emhdrCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file

        return outputs


class eframeOutput(TraitedSpec):
    pet_file = File(desc="PET image with correct time frames.")
    #out_file_bkp = File(desc="PET image with correct times frames backup.")

class eframeInput(CommandLineInputSpec):
    #out_file = File(desc="PET image with correct time frames.")
    #out_file_bkp = File(desc="PET image with correct times frames backup.")
    pet_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
    frame_file = File(exists=True, argstr="%s", position=-1, desc="PET file")
    unit = traits.Bool(argstr="-sec", position=-3, usedefault=True, default_value=True, desc="Time units are in seconds.")
    silent = traits.Bool(argstr="-s", position=-4, usedefault=True, default_value=True, desc="Silence outputs.")


class eframeCommand(CommandLine):
    input_spec =  eframeInput
    output_spec = eframeOutput

    _cmd = "eframe"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["pet_file"] = self.inputs.pet_file
        #outputs["out_file_bkp"] = self.inputs.out_file_bkp
        return outputs


    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        #if not isdefined(self.inputs.out_file):
        #    self.inputs.pet_file = self.inputs.pet_file
        #if not isdefined(self.inputs.out_file_bkp):
        #    self.inputs.out_file_bkp = self.inputs.in_file + '.bak'
        return super(eframeCommand, self)._parse_inputs(skip=skip)


class sifOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="SIF text file with correct time frames.")

class sifInput(CommandLineInputSpec):
    out_file = File(argstr="%s",  desc="SIF text file with correct time frames.")
    in_file = File(argstr="%s",  desc="Minc PET image.")
    header= traits.File(exists=True, argstr="%s", desc="PET header file")


class sifCommand(BaseInterface):
    input_spec =  sifInput
    output_spec = sifOutput

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list =splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + "_frames.sif"


    def _run_interface(self, runtime):
        #Define the output file based on the input file
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)

        in_file = self.inputs.in_file
        out_file = self.inputs.out_file

        print(self.inputs.header)
        data = json.load( open( self.inputs.header, "rb" ) )

        #if data['Time']['frames-time'] == 'unknown':
        #    start = 0
        #    print 'Warning: Converting \"unknown\" start time to 0.'
        #else :
        #    start=np.array(data['time']['frames-time'], dtype=float)

        #if data['time']['frames-length'] == 'unknown':
        #    duration=1.0
        #    print 'Warning: Converting \"unknown\" time duration to 1.'
        #else :
        #    duration=np.array(data['time']['frames-length'], dtype=float    )

        frame_times = data["Time"]["FrameTimes"]["Values"]
        start=[]
        duration = data["Time"]["FrameTimes"]["Duration"]
        for s, e in frame_times :
            start.append(s)

        print("Start -- Duration:", start, duration)
        df=pd.DataFrame(data={ "Start" : start, "Duration" : duration})
        df=df.reindex_axis(["Start", "Duration"], axis=1)
        df.to_csv(out_file, sep=" ", header=True, index=False )
        return runtime


class JsonToSifOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="SIF text file with correct time frames.")

class JsonToSifInput(CommandLineInputSpec):
    out_file = File(argstr="%s",  desc="SIF text file with correct time frames.")
    pet = File(exists=True, argstr="%s",  desc="Minc PET image.")
    pet_header_json = traits.File(exists=True, argstr="%s", desc="PET header file")


class JsonToSifCommand(BaseInterface):
    input_spec =  JsonToSifInput
    output_spec = JsonToSifOutput

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _run_interface(self, runtime):
        img_fn=self.inputs.pet
        json_fn=self.inputs.pet_header_json

        out_fn= splitext(img_fn)[0] + '.sif' 

        img = nib.load(img_fn).get_data()

        d = json.load(open(json_fn)) 
        nframes=len(d["Time"]["FrameTimes"]["Values"])
        date_string = datetime.datetime.now().strftime("%d/%m/%Y %H:%m:%S")
        lines=date_string+"  "+str(nframes)+" 4 1 sub "+d['Info']['Tracer']['Isotope'][0] + "\n"
        for i, vals in enumerate(d["Time"]["FrameTimes"]["Values"]) : 
            lines += "{}\t{}\t{}\t{}\n".format(vals[1], vals[1], str(np.sum(img[:,:,:,i])), str(np.sum(img[:,:,:,i])) )


        with open(out_fn, 'w') as f:
            f.write(lines)

        self.inputs.out_file = out_fn
        print('Creating SIF', out_fn)
        return runtime
