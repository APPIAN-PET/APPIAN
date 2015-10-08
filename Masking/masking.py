import os
import numpy as np
import tempfile
import shutil

from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile

from nipype.interfaces.minc.calc import CalcCommand
from nipype.interfaces.minc.smooth import SmoothCommand
from nipype.interfaces.minc.tracc import TraccCommand
from nipype.interfaces.minc.resample import ResampleCommand
from nipype.interfaces.minc.xfmOp import ConcatCommand
from nipype.interfaces.minc.xfmOp import InvertCommand







class T1maskingInput(BaseInterfaceInputSpec):
	nativeT1 = File(exists=True, mandatory=True, desc="Native T1 image")
	Lint1talXfm = File(exists=True, mandatory=True, desc="Transformation matrix to register T1 image into Talairach space")
	brainmask  = File(exists=True, mandatory=True, desc="Brain mask image in Talairach space")
	modelDir = traits.Str(exists=True, mandatory=True, desc="Models directory")
	T1headmask = File( exists=True, mandatory=True, desc="anatomical head mask, background removed")
	T1brainmask = File(exists=True, mandatory=True, desc="Transformation matrix to register T1 image into Talairach space")

	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class T1maskingOutput(TraitedSpec):
	T1headmask = File(exists=True, desc="anatomical head mask, background removed")
	T1brainmask = File(exists=True, desc="anatomical head mask, background and skull removed")

class T1maskingRunning(BaseInterface):
    input_spec = T1maskingInput
    output_spec = T1maskingOutput


    def _run_interface(self, runtime):
		tmpDir = tempfile.mkdtemp()

		model_headmask = self.inputs.modelDir+"/icbm_avg_152_t1_tal_lin_headmask.mnc"
		run_xfminvert = InvertCommand();
		run_xfminvert.inputs.in_file_xfm = self.inputs.Lint1talXfm
		# run_xfminvert.inputs.out_file_xfm = self.inputs.Lintalt1Xfm
		if self.inputs.verbose:
		    print run_xfminvert.cmdline
		if self.inputs.run:
		    run_xfminvert.run()

		run_resample = ResampleCommand();
		run_resample.inputs.input_file =  = model_headmask
		run_resample.inputs.out_file = self.inputs.T1headmask
		run_resample.inputs.model_file = self.inputs.nativeT1
		run_resample.inputs.transformation = run_xfminvert.inputs.out_file_xfm
		run_resample.inputs.interpolation = 'nearest_neighbour'
		run_resample.inputs.clobber = True
		if self.inputs.verbose:
		    print run_resample.cmdline
		if self.inputs.run:
		    run_resample.run()


		run_resample = ResampleCommand();
		run_resample.inputs.input_file = self.inputs.brainmask
		run_resample.inputs.out_file = self.inputs.T1brainmask
		run_resample.inputs.model_file = self.inputs.nativeT1
		run_resample.inputs.transformation = run_xfminvert.inputs.out_file_xfm
		run_resample.inputs.interpolation = 'nearest_neighbour'
		run_resample.inputs.clobber = True
		if self.inputs.verbose:
		    print run_resample.cmdline
		if self.inputs.run:
		    run_resample.run()

		return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["T1headmask"] = self.inputs.T1headmask
        outputs["T1brainmask"] = self.inputs.T1brainmask




class RefmaskingInput(BaseInterfaceInputSpec):
	nativeT1 = File(exists=True, mandatory=True, desc="Native T1 image")
	T1Tal = File(exists=True, mandatory=True, desc="T1 image normalized into Talairach space")
	LinT1TalXfm = File(exists=True, mandatory=True, desc="Transformation matrix to register T1 image into Talairach space")
	brainmask  = File(exists=True, mandatory=True, desc="Brain mask image in Talairach space")
	clsmaskTal  = File(exists=True, mandatory=True, desc="Classification mask in Talairach space")
	segmaskTal  = File(exists=True, mandatory=True, desc="Segmentation mask in Talairach space")
	
	_RefOpts = ["atlas", "nonlinear", "no-transform"]
	user_opts = traits.Enum(*_RefOpts, mandatory=True, desc="Masking approaches")
	modelDir = traits.Str(exists=True, mandatory=True, desc="Models directory")
	RefmaskTemplate  = File(exists=True, mandatory=True, desc="Reference mask on the template")

	RefmaskTal  = File(exists=True, mandatory=True, desc="Reference mask in Talairach space")
	RefmaskT1  = File(exists=True, mandatory=True, desc="Reference mask in the native space")
	
	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class RefmaskingOutput(TraitedSpec):
	RefmaskTal  = File(exists=True, mandatory=True, desc="Reference mask in Talairach space")
	RefmaskT1  = File(exists=True, mandatory=True, desc="Reference mask in the native space")

class RefmaskingRunning(BaseInterface):
    input_spec = RefmaskingInput
    output_spec = RefmaskingOutput


    def _run_interface(self, runtime):
		tmpDir = tempfile.mkdtemp()


		if self.inputs.RefOpts is 'no-transform':
			run_resample = ResampleCommand();
			run_resample.inputs.input_file = self.inputs.RefmaskTemplate
			run_resample.inputs.out_file = self.inputs.RefmaskTal
			run_resample.inputs.model_file = self.inputs.T1Tal
			run_resample.inputs.clobber = True
			if self.inputs.verbose:
			    print run_resample.cmdline
			if self.inputs.run:
			    run_resample.run()

		elif self.inputs.RefOpts is 'nonlinear':
			run_nlinreg=reg.T1toTalnLinRegRunning();
			run_nlinreg.inputs.input_source_file = self.inputs.T1Tal
			run_nlinreg.inputs.input_target_file = 
			run_nlinreg.inputs.input_source_mask = 
			run_nlinreg.inputs.input_target_mask = 
			run_nlinreg.inputs.out_file_xfm = 
			run_nlinreg.inputs.out_file_img = 
			run_nlinreg.inputs.clobber = True;
			run_nlinreg.inputs.verbose = True;
			run_nlinreg.inputs.run = False;


		return runtime




