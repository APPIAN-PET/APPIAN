import os
import ntpath
import nipype.pipeline.engine as pe
import re
import pandas as pd
import json
from sys import argv
import numpy as np
import json
import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
import nipype.interfaces.minc as minc
from Extra.resample import param2xfmCommand
from Extra.modifHeader import ModifyHeaderCommand, FixHeaderCommand
from Extra.turku import imgunitCommand



class convertOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class convertInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
    two= traits.Bool(argstr="-2", usedefault=True, default_value=True, desc="Convert from minc 1 to minc 2")

class mincconvertCommand(CommandLine):
    input_spec =  convertInput
    output_spec = convertOutput

    _cmd = "mincconvert"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = list(os.path.splitext(fname)) # [0]= base filename; [1] =extension
        print fname_list
        if "_mnc1"  in  fname_list[0] :
        	fname_list[0]=re.sub("_mnc1", "", fname_list[0])
        elif "_mnc2"  in fname_list[0] :
        	fname_list[0]=re.sub("_mnc2", "", fname_list[0])
        elif self.inputs.two: #Converting from minc1 to minc
        	fname_list[0] = fname_list[0] + "_mnc2"
        else: #Converting from minc to minc1
        	fname_list[0] = fname_list[0] + "_mnc1"
          

        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
        	self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(mincconvertCommand, self)._parse_inputs(skip=skip)



##################
### minctoecat ###
##################
def minctoecatWorkflow(name):
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputNode = pe.Node(niu.IdentityInterface(fields=["in_file", "header"]), name='inputNode')
    conversionNode = pe.Node(interface=minctoecatCommand(), name="conversionNode")
    conversionNode.inputs.out_file=name+'.v'
    sifNode = pe.Node(interface=sifCommand(), name="sifNode")
    eframeNode = pe.Node(interface=eframeCommand(), name="eframeNode")
    ###imgunitNode = pe.Node(interface=imgunitCommand(), name="imgunitCommand")
    ###imgunitNode.inputs.u = "Bq/cc"
    outputNode = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputNode')
    
    workflow.connect(inputNode, 'in_file', conversionNode, 'in_file')
    workflow.connect(inputNode, 'in_file', sifNode, 'in_file')
    workflow.connect(inputNode, 'header', sifNode, 'header')

    workflow.connect(conversionNode, 'out_file', outputNode, 'out_file')
    workflow.connect(conversionNode, 'out_file', eframeNode, 'pet_file')
    workflow.connect(sifNode, 'out_file', eframeNode, 'frame_file')
    ###workflow.connect(eframeNode, 'out_file', imgunitNode, 'in_file')
    ###workflow.connect(imgunitNode, 'out_file', outputNode, 'out_file') 

    return(workflow)


class ecat2mincOutput(TraitedSpec):
    out_file = File(desc="PET image with correct time frames.")

class ecat2mincInput(CommandLineInputSpec):
    in_file = File(exists=True, desc="PET file")
    header  = File(exists=True, desc="PET file")
    out_file= File(argstr="%s", position=-2, desc="PET file")

class ecat2mincCommand(BaseInterface):
    input_spec = ecat2mincInput
    output_spec = ecat2mincOutput

    def _run_interface(self, runtime): 
        conversionNode = ecattomincCommand()
        conversionNode.inputs.in_file = self.inputs.in_file
        conversionNode.run()

        mincConversionNode = mincconvertCommand()
        mincConversionNode.inputs.in_file=conversionNode.inputs.out_file
        mincConversionNode.run()

        fixHeaderNode =  FixHeaderCommand()
        fixHeaderNode.inputs.in_file = mincConversionNode.inputs.out_file
        fixHeaderNode.inputs.header = self.inputs.header
        fixHeaderNode.run()

        self.inputs.out_file = fixHeaderNode.inputs.out_file
        
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs



def ecattomincWorkflow(name):
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputNode = pe.Node(niu.IdentityInterface(fields=["in_file", "header"]), name='inputNode')
    conversionNode = pe.Node(interface=ecattomincCommand(), name="conversionNode")
    mincConversionNode = pe.Node(interface=mincconvertCommand(), name="mincConversionNode")
    fixHeaderNode = pe.Node(interface=FixHeaderCommand(), name="fixHeaderNode")
    paramNode = pe.Node(interface=param2xfmCommand(), name="param2xfmNode")
    paramNode.inputs.rotation = "0 180 0"
    resampleNode = pe.Node(interface=minc.Resample(), name="resampleNode")
    resampleNode.inputs.vio_transform=True
    outputNode  = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputNode')

    workflow.connect(inputNode, 'in_file', conversionNode, 'in_file')
    workflow.connect(conversionNode, 'out_file', fixHeaderNode, 'in_file')
    workflow.connect(inputNode, 'header', fixHeaderNode, 'header')
    workflow.connect(fixHeaderNode, 'out_file', outputNode, 'out_file')



    return(workflow)

class minc2ecatOutput(TraitedSpec):
    out_file = File(desc="PET image with correct time frames.")
    #out_file_bkp = File(desc="PET image with correct times frames backup.")

class minc2ecatInput(CommandLineInputSpec):
    in_file = File(exists=True, desc="PET file")
    header  = File(exists=True, desc="PET file")
    out_file= File(argstr="%s", position=-2, desc="PET file")


class minc2ecatCommand(BaseInterface):
    input_spec =  minc2ecatInput
    output_spec = minc2ecatOutput

    def _run_interface(self, runtime):
        conversionNode = minctoecatCommand()
        conversionNode.inputs.in_file = self.inputs.in_file    
        conversionNode.inputs.out_file='out.v'
        conversionNode.run()     
        
        sifNode = sifCommand()
        sifNode.inputs.in_file = self.inputs.in_file
        sifNode.inputs.header = self.inputs.header
        sifNode.run()
        
        eframeNode = eframeCommand()
        eframeNode.inputs.frame_file = sifNode.inputs.out_file 
        eframeNode.inputs.pet_file = conversionNode.inputs.out_file 
        eframeNode.run()

        imgunitNode = imgunitCommand()
        imgunitNode.inputs.in_file = eframeNode.inputs.pet_file
        imgunitNode.inputs.u = "Bq/cc"
        imgunitNode.run()
   
        self.inputs.out_file = imgunitNode.inputs.out_file

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs




class eframeOutput(TraitedSpec):
    pet_file = File(desc="PET image with correct time frames.")
    #out_file_bkp = File(desc="PET image with correct times frames backup.")

class eframeInput(CommandLineInputSpec):
    #out_file = File(desc="PET image with correct time frames.")
    out_file_bkp = File(desc="PET image with correct times frames backup.")
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
        #    self.inputs.out_file = self.inputs.in_file
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
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + "_frames.sif"


    def _run_interface(self, runtime):
        #Define the output file based on the input file
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)

        in_file = self.inputs.in_file
        out_file = self.inputs.out_file

        #data = self.inputs.header
        data = json.load( open( self.inputs.header, "rb" ) )
        
        start=np.array(data['time']['frames-time'], dtype=float)
        if data['time']['frames-length'] == 'unknown':
            duration=1.0
            print 'Warning: Converting \"unknown\" time duration to 1.'
        else:
            duration=np.array(data['time']['frames-length'], dtype=float    )
            end=start+duration
            df=pd.DataFrame(data={ "Start" : start, "Duration" : duration})
            df=df.reindex_axis(["Start", "Duration"], axis=1)
            df.to_csv(out_file, sep=" ", header=True, index=False )
        return runtime


class minctoecatOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class minctoecatInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")

class minctoecatCommand(CommandLine):
    input_spec =  minctoecatInput
    output_spec = minctoecatOutput
    _cmd = "minctoecat"

    def _gen_output(self, basefile):
        print basefile
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + ".v"

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
 
        return super(minctoecatCommand, self)._parse_inputs(skip=skip)

class nii2mncOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="convert from nifti to minc")

class nii2mncInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="minc file")
    in_file= File(exists=True, argstr="%s", position=-2, desc="nifti file")

class nii2mncCommand(CommandLine):
    input_spec =  nii2mncInput
    output_spec = nii2mncOutput

    _cmd = "nii2mnc"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
        	self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(nii2mncCommand, self)._parse_inputs(skip=skip)


##################
### ecattominc ###
##################

class ecattomincOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class ecattomincInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")

class ecattomincCommand(CommandLine):
    input_spec =  ecattomincInput
    output_spec = ecattomincOutput

    _cmd = "ecattominc"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    #def _gen_filename(self, name):
    #    if name == "out_file":
    #        return self._list_outputs()["out_file"]
    #    return None

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(ecattomincCommand, self)._parse_inputs(skip=skip)

