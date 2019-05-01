import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, CommandLine,  CommandLineInputSpec , File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from Extra.utils import splitext
import json
import ntpath
import os
import datetime
import numpy as np
import pandas as pd
import nibabel as nib


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
            lines += "{}\t{}\t{}\t{}\n".format(vals[0], vals[1], str(np.sum(img[:,:,:,i])), str(np.sum(img[:,:,:,i])) )

        
        with open(out_fn, 'w') as f:
            f.write(lines)

        self.inputs.out_file = out_fn
        print('Creating SIF')
        return runtime
