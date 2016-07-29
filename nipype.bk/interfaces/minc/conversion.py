import os
import ntpath
import nipype.pipeline.engine as pe
import re

import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec

class convertOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class convertInput(MINCCommandInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
    two= traits.Bool(argstr="-2",  default_value=False, desc="Convert from minc 1 to minc 2")


####################
# MINC 1 to MINC 2 #
####################




####################
# MINC 2 to MINC 1 #
####################
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
        	self.inputs.out_file = self._gen_output(self.inputs.in_file,)
        return super(minctoecatCommand, self)._parse_inputs(skip=skip)

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

