import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.minc.minc import Resample, ResampleOutputSpec, ResampleInputSpec
from time import gmtime, strftime
import gzip
import shutil
import os 
import re

class gzipOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="compressed file")

class gzipInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="compressed")
    in_file= File(exists=True, argstr="%s", position=-2, desc="input file")

class gzipCommand(BaseInterface):
    input_spec =  gzipInput
    output_spec = gzipOutput

    def _run_interface(self, runtime):
        self.inputs.out_file = self._gen_output() 
        try :
            with open(self.inputs.in_file, 'rb') as f_in, gzip.open(self.inputs.out_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            if os.path.exists(self.inputs.out_file) :
                os.remove(self.inputs.in_file)
        except RuntimeError : 
            print("Error: Could not gzip file ", self.inputs.in_file)
            exit(1)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self):
        return self.inputs.in_file +'.gz'

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(gzipCommand, self)._parse_inputs(skip=skip)


class gunzipOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="uncompressed file")

class gunzipInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="uncompressed")
    in_file= File(exists=True, argstr="%s", position=-2, desc="compressed input file")

class gunzipCommand(BaseInterface):
    input_spec =  gzipInput
    output_spec = gzipOutput

    def _run_interface(self, runtime):
        self.inputs.out_file = self._gen_output() 
        try :
            with gzip.open(self.inputs.in_file, 'rb') as f_in, open(self.inputs.out_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            if os.path.exists(self.inputs.out_file) :
                os.remove(self.inputs.in_file)
        except RuntimeError : 
            print("Error: Could not gzip file ", self.inputs.in_file)
            exit(1)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self):
        return re.sub('.gz', '', self.inputs.in_file)

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(gzipCommand, self)._parse_inputs(skip=skip)



class gzipResampleCommand(BaseInterface):
    input_spec =    ResampleInputSpec
    output_spec =   ResampleOutputSpec

    def _run_interface(self, runtime):

        temp_fn="/tmp/tmp_mnc_"+ strftime("%Y%m%d%H%M%S", gmtime())+str(np.random.randint(9999999999))+".mnc" 

        try :
            resample = Resample()
            resample.inputs = self.inputs
            resample.inputs.out_file = temp_fn
        except RuntimeError : 
            print("Error: Could not resample file ", self.inputs.in_file)
            exit(1)

        try :
            gzip = gzipCommand()
            gzip.inputs.in_file = resample.inputs.out_file
            gzip.run()    
        except RuntimeError : 
            print("Error: After resampling, could not gzip file ", resample.inputs.out_file)
            exit(1)

        self.inputs.out_file = gzip.inputs.out_file
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        #if not isdefined(self.inputs.out_file) :
        #    self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self):
        return self.inputs.in_file +'.gz'

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        #if not isdefined(self.inputs.out_file):
        #    self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(gzipResampleCommand, self)._parse_inputs(skip=skip)


