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
	t1headmask = File(exists=True, desc="anatomical head mask, background removed")
	t1brainmask = File(exists=True, desc="anatomical head mask, background and skull removed")

class T1maskingRunning(BaseInterface):
    input_spec = T1maskingInput
    output_spec = T1maskingOutput


    def _run_interface(self, runtime):
		tmpDir = tempfile.mkdtemp()
		model_headmask = self.inputs.modelDir+"/icbm_avg_152_t1_tal_lin_headmask.mnc"
		print "Hello"
		run_xfminvert = InvertCommand();
		run_xfminvert.inputs.in_file_xfm = self.inputs.Lint1talXfm
		# run_xfminvert.inputs.out_file_xfm = self.inputs.Lintalt1Xfm
		if self.inputs.verbose:
		    print run_xfminvert.cmdline
		if self.inputs.run:
		    run_xfminvert.run()

		run_resample = ResampleCommand();
		run_resample.inputs.input_file=model_headmask
		run_resample.inputs.out_file=self.inputs.T1headmask
		run_resample.inputs.model_file=self.inputs.nativeT1
		run_resample.inputs.transformation=run_xfminvert.inputs.out_file_xfm
		run_resample.inputs.interpolation='nearest_neighbour'
		run_resample.inputs.clobber=True
		if self.inputs.verbose:
		    print run_resample.cmdline
		if self.inputs.run:
		    run_resample.run()


		run_resample = ResampleCommand();
		run_resample.inputs.input_file=self.inputs.brainmask
		run_resample.inputs.out_file=self.inputs.T1brainmask
		run_resample.inputs.model_file=self.inputs.nativeT1
		run_resample.inputs.transformation=run_xfminvert.inputs.out_file_xfm
		run_resample.inputs.interpolation='nearest_neighbour'
		run_resample.inputs.clobber=True
		if self.inputs.verbose:
		    print run_resample.cmdline
		if self.inputs.run:
		    run_resample.run()







# def mri(nativet1, Lint1talXfm, brainmask, modelDir, t1headmask, t1brainmask, verbose, run):
# 	tmpDir = tempfile.mkdtemp()
# 	model_headmask = modelDir+"/icbm_avg_152_t1_tal_lin_headmask.mnc"

# 	run_xfminvert = InvertCommand();
# 	run_xfminvert.inputs.in_file_xfm = Lint1talXfm
# 	# run_xfminvert.inputs.out_file_xfm = Lintalt1Xfm
# 	if verbose:
# 	    print run_xfminvert.cmdline
# 	if run:
# 	    run_xfminvert.run()

# 	run_resample = ResampleCommand();
# 	run_resample.inputs.input_file=model_headmask
# 	run_resample.inputs.out_file=t1headmask
# 	run_resample.inputs.model_file=nativet1
# 	run_resample.inputs.transformation=run_xfminvert.inputs.out_file_xfm
# 	run_resample.inputs.interpolation='nearest_neighbour'
# 	run_resample.inputs.clobber=True
# 	if verbose:
# 	    print run_resample.cmdline
# 	if run:
# 	    run_resample.run()


# 	run_resample = ResampleCommand();
# 	run_resample.inputs.input_file=brainmask
# 	run_resample.inputs.out_file=t1brainmask
# 	run_resample.inputs.model_file=nativet1
# 	run_resample.inputs.transformation=run_xfminvert.inputs.out_file_xfm
# 	run_resample.inputs.interpolation='nearest_neighbour'
# 	run_resample.inputs.clobber=True
# 	if verbose:
# 	    print run_resample.cmdline
# 	if run:
# 	    run_resample.run()


# def reference(nativet1, t1tal, Lint1talXfm, brainmask, clsmask, segmask, talrefmask, t1refmask, opt, verbose, run):
# 	tmpDir = tempfile.mkdtemp()
# 	if opt.noTransf and opt.RefMaskTemplate:
# 		run_resample = ResampleCommand();
# 		run_resample.inputs.input_file=opt.RefMaskTemplate
# 		run_resample.inputs.out_file=talrefmask
# 		run_resample.inputs.model_file=t1tal
# 		run_resample.inputs.clobber=True
# 		if verbose:
# 		    print run_resample.cmdline
# 		if run:
# 		    run_resample.run()

# 	elif opt.RefTemplate and opt.RefMaskTemplate