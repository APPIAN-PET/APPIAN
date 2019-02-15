import os
import numpy as np
import pandas as pd
from re import sub
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,  BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)

class concat_dfOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class concat_dfInput(BaseInterfaceInputSpec):
    in_list = traits.List(mandatory=True, exists=True, desc="Input list")
    out_file = traits.File(mandatory=True, desc="Output file")
    test = traits.Bool(default=False, usedefault=True, desc="Flag for if df is part of test run of pipeline")

class concat_df(BaseInterface):
    input_spec =  concat_dfInput 
    output_spec = concat_dfOutput 
   
    def _run_interface(self, runtime):
        df=pd.DataFrame([])
        test = self.inputs.test

        for f in self.inputs.in_list:
            dft = pd.read_csv(f)
            print(f)
            print(dft)
            if test :
                s=f.split('/')
                error = s[-3].split('.')[-1]
                errortype = s[-3].split('.')[-2]
		errortype = sub('_error_', '', errortype )
                dft['error'] = error
                dft["errortype"]=errortype
            df = pd.concat([df, dft], axis=0)
        #if test : print df
        df.to_csv(self.inputs.out_file, index=False)
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.getcwd() + os.sep + self.inputs.out_file
        return outputs
      
class ConcatOutput(TraitedSpec):
    out_file = File(exists=True, desc="resampled image")

class ConcatInput(CommandLineInputSpec):
    in_file = InputMultiPath(File(mandatory=True), position=0, argstr='%s', desc='List of input images.')
    out_file = File(position=1, argstr="%s", mandatory=True, desc="Output image.")
    
    dimension = traits.Str(argstr="-concat_dimension %s", desc="Concatenate along a given dimension.")
    start = traits.Float(argstr="-start %s", desc="Starting coordinate for new dimension.")
    step = traits.Float(argstr="-step %s", desc="Step size for new dimension.")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ConcatCommand(CommandLine):
    _cmd = "mincconcat"
    _suffix = "_concat"
    input_spec = ConcatInput
    output_spec = ConcatOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix)

        return super(ConcatCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None


