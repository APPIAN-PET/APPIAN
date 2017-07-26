import os
import ntpath
import nipype.pipeline.engine as pe
import re
import pandas as pd
import json
from sys import argv
import numpy as np


import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
#from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec
from Extra.resample import param2xfmCommand
from Extra.modifHeader import ModifyHeaderCommand, FixHeaderCommand
from Extra.turku import imgunitCommand



class convertOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class convertInput(MINCCommandInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
    two= traits.Bool(argstr="-2",  default_value=True, desc="Convert from minc 1 to minc 2")

class mincconvertCommand(MINCCommand):
    input_spec =  convertInput
    output_spec = convertOutput

    _cmd = "mincconvert"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        if fname_list[0] == "_mnc1":
        	fname_list[0]=re.sub("_mnc1", "", fname_list[0])
        elif fname_list[0] == "_mnc2":
        	fname_list[0]=re.sub("_mnc2", "", fname_list[0])
        elif input_spec.two: #Converting from minc1 to minc2
        	fname_list[0] = fname_list[0] + "_mnc2"
        else: #Converting from minc2 to minc1
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
    sifNode = pe.Node(interface=sifCommand(), name="sifNode")
    eframeNode = pe.Node(interface=eframeCommand(), name="eframeNode")
    imgunitNode = pe.Node(interface=imgunitCommand(), name="imgunitCommand")
    imgunitNode.inputs.u = "Bq/cc"
    outputNode = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputNode')
    
    workflow.connect(inputNode, 'in_file', conversionNode, 'in_file')
    workflow.connect(inputNode, 'in_file', sifNode, 'in_file')
    workflow.connect(inputNode, 'header', sifNode, 'header')
    workflow.connect(conversionNode, 'out_file', eframeNode, 'in_file')
    workflow.connect(sifNode, 'out_file', eframeNode, 'frame_file')
    workflow.connect(eframeNode, 'out_file', imgunitNode, 'in_file')
    workflow.connect(imgunitNode, 'in_file', outputNode, 'out_file') 

    return(workflow)

def ecattomincWorkflow(name):
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputNode = pe.Node(niu.IdentityInterface(fields=["in_file", "header"]), name='inputNode')
    conversionNode = pe.Node(interface=ecattomincCommand(), name="conversionNode")
    mincConversionNode = pe.Node(interface=mincconvertCommand(), name="mincConversionNode")
    fixHeaderNode = pe.Node(interface=FixHeaderCommand(), name="fixHeaderNode")
    paramNode = pe.Node(interface=param2xfmCommand(), name="param2xfmNode")
    paramNode.inputs.rotation = "0 180 0"
    resampleNode = pe.Node(interface=ResampleCommand(), name="resampleNode")
    resampleNode.inputs.use_input_sampling=True
    outputNode  = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputNode')

    workflow.connect(inputNode, 'in_file', conversionNode, 'in_file')
    workflow.connect(conversionNode, 'out_file', fixHeaderNode, 'in_file')
    workflow.connect(inputNode, 'header', fixHeaderNode, 'header')
    workflow.connect(fixHeaderNode, 'out_file', outputNode, 'out_file')

    # workflow.connect(inputNode, 'in_file', conversionNode, 'in_file')
    # workflow.connect(conversionNode, 'out_file', outputNode, 'out_file')
    
    # workflow.connect(inputNode, 'header', fixHeaderNode, 'header')
    # workflow.connect(fixHeaderNode, 'out_file', resampleNode, 'in_file')
    # workflow.connect(paramNode, 'out_file', resampleNode, 'transformation')
    # workflow.connect(resampleNode, 'out_file', outputNode, 'out_file')  
    # workflow.connect(fixHeaderNode, 'out_file', outputNode, 'out_file')

    return(workflow)




class eframeOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="PET image with correct time frames.")

class eframeInput(MINCCommandInputSpec):
    #out_file = File(argstr="%s",  desc="PET image with correct time frames.")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
    frame_file = File(exists=True, argstr="%s", position=-1, desc="PET file")
    unit = traits.Bool(argstr="-sec", position=-3, usedefault=True, default_value=True, desc="Time units are in seconds.")


class eframeCommand(MINCCommand):
    input_spec =  eframeInput
    output_spec = eframeOutput

    _cmd = "eframe"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.in_file
        return outputs


    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        
        #self.inputs.out_file = self.inputs.in_file
        return super(eframeCommand, self)._parse_inputs(skip=skip)


class sifOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="SIF text file with correct time frames.")

class sifInput(MINCCommandInputSpec):
    out_file = File(argstr="%s",  desc="SIF text file with correct time frames.")
    in_file = File(argstr="%s",  desc="Minc PET image.")
    header= traits.Dict(exists=True, argstr="%s", desc="PET header file")


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

        data = self.inputs.header

        start=np.array(data['time']['frames-time'], dtype=float)
        duration=np.array(data['time']['frames-length'], dtype=float    )
        end=start+duration

        df=pd.DataFrame(data={ "Start" : start, "Duration" : duration})
        df=df.reindex_axis(["Start", "Duration"], axis=1)
        df.to_csv(out_file, sep=" ", header=True, index=False )

        return runtime


class minctoecatOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class minctoecatInput(MINCCommandInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")

class minctoecatCommand(MINCCommand):
    input_spec =  minctoecatInput
    output_spec = minctoecatOutput

    _cmd = "minctoecat"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + ".v"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
        	self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(minctoecatCommand, self)._parse_inputs(skip=skip)

class nii2mncOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="convert from nifti to minc")

class nii2mncInput(MINCCommandInputSpec):
    out_file = File( argstr="%s", position=-1, desc="minc file")
    in_file= File(exists=True, argstr="%s", position=-2, desc="nifti file")

class nii2mncCommand(MINCCommand):
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

class ecattomincInput(MINCCommandInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")

class ecattomincCommand(MINCCommand):
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

'''
def minctoecat_workflow(name, opts, dir):
	if dir==1: #Convert from minc2 -> minc1 -> ecat
		f1=mincconvertCommand()
		f2=minctoecatCommand()
	elif dir==-1:#Convert
		f2=mincconvertCommand()
		f1=minctoecatCommand()

	workflow = pe.Workflow(name=name)
	#Define input node that will receive input from outside of workflow
	inputnode = pe.Node(niu.IdentityInterface(fields=["in_file"]), name='inputnode')
	minc1=pe.Node(interface=, name="node1")	
	ecat=pe.Node(interface=, name="")
	outputnode = pe.Node(niu.IdentityInterface(fields=['out_file']), name='inputnode')

	workflow.connect(inputnode, 'in_file', minc1, 'in_file')
	workflow.connect(minc1, 'out_file', ecat, 'in_file')	
	workflow.connect(ecat, 'out_file', outputnode, 'out_file')

	return(workflow)'''

