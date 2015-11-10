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
from nipype.interfaces.minc.morphomat import MorphCommand
import Registration.registration as reg





class T1maskingInput(BaseInterfaceInputSpec):
	nativeT1 = File(exists=True, mandatory=True, desc="Native T1 image")
	LinT1TalXfm = File(exists=True, mandatory=True, desc="Transformation matrix to register T1 image into Talairach space")
	brainmaskTal  = File(exists=True, mandatory=True, desc="Brain mask image in Talairach space")
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
		model_headmask = self.inputs.modelDir+"/icbm_avg_152_t1_tal_lin_headmask.mnc"
		run_xfminvert = InvertCommand();
		run_xfminvert.inputs.in_file_xfm = self.inputs.LinT1TalXfm
		# run_xfminvert.inputs.out_file_xfm = self.inputs.Lintalt1Xfm
		if self.inputs.verbose:
		    print run_xfminvert.cmdline
		if self.inputs.run:
		    run_xfminvert.run()

		run_resample = ResampleCommand();
		run_resample.inputs.input_file = model_headmask
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
		run_resample.inputs.input_file = self.inputs.brainmaskTal
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
	brainmaskTal  = File(exists=True, mandatory=True, desc="Brain mask image in Talairach space")
	clsmaskTal  = File(exists=True, mandatory=True, desc="Classification mask in Talairach space")
	segMaskTal  = File(exists=True, mandatory=True, desc="Segmentation mask in Talairach space")
	segLabels = traits.Array(usedefault=True, value=[67, 76], desc="Label value(s) of reference region from ANIMAL. By default, cerebellum labels")
	
	_methods = ["atlas", "nonlinear", "no-transform"]
	MaskingType = traits.Enum(*_methods, mandatory=True, desc="Masking approaches")
	modelDir = traits.Str(exists=True, mandatory=True, desc="Models directory")
	RefmaskTemplate  = File(exists=True, mandatory=True, desc="Reference mask on the template")
	close = traits.Bool(usedefault=True, default_value=True, desc="erosion(dilation(X))")
	refGM = traits.Bool(usedefault=True, default_value=True, desc="Only gray matter")
	refWM = traits.Bool(usedefault=True, default_value=True, desc="Only white matter")

	RefmaskTal  = File(mandatory=True, desc="Reference mask in Talairach space")
	RefmaskT1  = File(mandatory=True, desc="Reference mask in the native space")
	
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

		if self.inputs.MaskingType == 'no-transform':
			run_resample = ResampleCommand();
			run_resample.inputs.input_file = self.inputs.RefmaskTemplate
			run_resample.inputs.out_file = self.inputs.RefmaskTal
			run_resample.inputs.model_file = self.inputs.T1Tal
			run_resample.inputs.clobber = True
			if self.inputs.verbose:
			    print run_resample.cmdline
			if self.inputs.run:
			    run_resample.run()

		elif self.inputs.MaskingType == 'nonlinear':
			model_T1 = self.inputs.modelDir+"/mni_icbm152_t1_tal_nlin_asym_09b.mnc"
			model_T1_mask = self.inputs.modelDir+"/mni_icbm152_t1_tal_nlin_asym_09b.mnc"
			T1toModel_ref_xfm = tmpDir+"/T1toModel_ref.xfm"

			run_nlinreg=reg.nLinRegRunning();
			run_nlinreg.inputs.input_source_file = self.inputs.T1Tal
			run_nlinreg.inputs.input_target_file = model_T1
			run_nlinreg.inputs.input_source_mask = self.inputs.brainmaskTal
			run_nlinreg.inputs.input_target_mask = model_T1_mask
			run_nlinreg.inputs.out_file_xfm = T1toModel_ref_xfm
			run_nlinreg.inputs.clobber = self.inputs.clobber;
			run_nlinreg.inputs.verbose = self.inputs.verbose;
			run_nlinreg.inputs.run = self.inputs.run;
			run_nlinreg.run()

			run_resample = ResampleCommand();
			run_resample.inputs.input_file = self.inputs.RefmaskTemplate
			run_resample.inputs.out_file = self.inputs.RefmaskTal
			run_resample.inputs.model_file = self.inputs.T1Tal
			run_resample.inputs.transformation = T1toModel_ref_xfm
			run_resample.inputs.interpolation = 'nearest_neighbour'
			run_resample.inputs.clobber = True
			if self.inputs.verbose:
			    print run_resample.cmdline
			if self.inputs.run:
			    run_resample.run()

		else:
			mask = tmpDir+"/mask.mnc"
			mask_clean = tmpDir+"/mask_clean.mnc"
			machin = self.inputs.segLabels
			
			run_calc = CalcCommand();
			run_calc.inputs.input_file = self.inputs.segMaskTal
			run_calc.inputs.out_file = mask
			run_calc.inputs.expression = 'A[0] == ' + str(self.inputs.segLabels[0]) + ' || A[0] == ' + str(self.inputs.segLabels[1]) + '? 1 : 0'
			if self.inputs.verbose:
				print run_calc.cmdline
			if self.inputs.run:
				run_calc.run()

			if self.inputs.close:
				run_mincmorph = MorphCommand()
				run_mincmorph.inputs.input_file = mask
				run_mincmorph.inputs.output_file = mask_clean
				run_mincmorph.inputs.successive='CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC'
				run_mincmorph.inputs.verbose=True			 
  				run_mincmorph.inputs.clobber = True
				if self.inputs.verbose:
					print run_mincmorph.cmdline
				if self.inputs.run:
					run_mincmorph.run()
			else:
  				mask_clean = mask

  			if self.inputs.refGM or self.inputs.refWM:
  				if self.inputs.refGM:
					run_calc = CalcCommand();
					run_calc.inputs.input_file = [mask_clean, self.inputs.clsmaskTal]
					run_calc.inputs.out_file = self.inputs.RefmaskTal
					run_calc.inputs.expression = 'A[0] == 1 && A[1] == 2 ? 1 : 0'
					if self.inputs.verbose:
						print run_calc.cmdline
					if self.inputs.run:
						run_calc.run()

  				if self.inputs.refWM:
					run_calc = CalcCommand();
					run_calc.inputs.input_file = [mask_clean, self.inputs.clsmaskTal]
					run_calc.inputs.out_file = self.inputs.RefmaskTal
					run_calc.inputs.expression = 'A[0] == 1 && A[1] == 3 ? 1 : 0'
					if self.inputs.verbose:
						print run_calc.cmdline
					if self.inputs.run:
						run_calc.run()

			else:
				if self.inputs.verbose:
					cmd=' '.join(['cp', mask_clean, self.inputs.RefmaskTal])
					print(cmd)
				if self.inputs.run:
					copyfile(mask_clean, self.inputs.RefmaskTal)

		run_xfminvert = InvertCommand();
		run_xfminvert.inputs.in_file_xfm = self.inputs.LinT1TalXfm
		if self.inputs.verbose:
		    print run_xfminvert.cmdline
		if self.inputs.run:
		    run_xfminvert.run()

		run_resample = ResampleCommand();
		run_resample.inputs.input_file = self.inputs.RefmaskTal
		run_resample.inputs.out_file = self.inputs.RefmaskT1
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
		outputs["RefmaskTal"] = self.inputs.RefmaskTal
		outputs["RefmaskT1"] = self.inputs.RefmaskT1





class PETheadMaskingOutput(TraitedSpec):
	RefmaskTal  = File(desc="Headmask from PET volume")

class PETheadMaskingInput(BaseInterfaceInputSpec):
    input_volume = File(exists=True, mandatory=True, desc="PET volume")
    input_json = File(exists=True, mandatory=True, desc="PET json file")
    output_file = File(mandatory=True, desc="Head mask")
	
	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETheadMaskingRunning(BaseInterface):
    input_spec = PETheadMaskingInput
    output_spec = PETheadMaskingOutput


    def _run_interface(self, runtime):
		tmpDir = tempfile.mkdtemp()

		hd = load_json(self.inputs.input_json)
		dim = hd['xspace']['length']+hd['yspace']['length']+hd['zspace']['length']+hd['time']['length']

		for ii in np.arange(1,dim[3],1):
			slice_tmp = tmpdir + '/pet_slice.mnc'
			



		if self.inputs.verbose:
		    print run_resample.cmdline
		if self.inputs.run:
		    run_resample.run()		

		return runtime


    def _list_outputs(self):
		outputs = self.output_spec().get()
		outputs["output_file"] = self.inputs.output_file



