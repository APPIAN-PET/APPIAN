import os
import numpy as np
import tempfile
import shutil
import pickle

from pyminc.volumes.factory import *
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.interfaces.minc.base import Info

from nipype.interfaces.minc.calc import CalcCommand
from nipype.interfaces.minc.smooth import SmoothCommand
from nipype.interfaces.minc.tracc import TraccCommand
from nipype.interfaces.minc.resample import ResampleCommand
from nipype.interfaces.minc.xfmOp import ConcatCommand
from nipype.interfaces.minc.xfmOp import InvertCommand
from nipype.interfaces.minc.morphomat import MorphCommand
from nipype.interfaces.minc.info import InfoCommand
from nipype.interfaces.minc.info import StatsCommand
from nipype.interfaces.minc.reshape import ReshapeCommand
from nipype.interfaces.minc.concat import ConcatCommand
import Registration.registration as reg





class T1maskingInput(BaseInterfaceInputSpec):
	nativeT1 = File(exists=True, mandatory=True, desc="Native T1 image")
	LinT1TalXfm = File(exists=True, mandatory=True, desc="Transformation matrix to register T1 image into Talairach space")
	brainmaskTal  = File(exists=True, mandatory=True, desc="Brain mask image in Talairach space")
	modelDir = traits.Str(exists=True, mandatory=True, desc="Models directory")
	T1headmask = File(desc="anatomical head mask, background removed")
	T1brainmask = File(desc="Transformation matrix to register T1 image into Talairach space")

	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class T1maskingOutput(TraitedSpec):
	T1headmask = File(desc="anatomical head mask, background removed")
	T1brainmask = File(desc="anatomical head mask, background and skull removed")

class T1maskingRunning(BaseInterface):
    input_spec = T1maskingInput
    output_spec = T1maskingOutput


    def _run_interface(self, runtime):
		model_headmask = self.inputs.modelDir+"/icbm_avg_152_t1_tal_lin_headmask.mnc"
		run_xfminvert = InvertCommand();
		run_xfminvert.inputs.in_file = self.inputs.LinT1TalXfm
		# run_xfminvert.inputs.out_file_xfm = self.inputs.Lintalt1Xfm
		if self.inputs.verbose:
		    print run_xfminvert.cmdline
		if self.inputs.run:
		    run_xfminvert.run()

		if not isdefined(self.inputs.T1headmask):
			fname = os.path.splitext(os.path.basename(self.inputs.nativeT1))[0]
			dname = os.path.dirname(self.inputs.nativeT1)
			self.inputs.T1headmask = dname +os.sep+ fname + "_headmask.mnc"

		if not isdefined(self.inputs.T1brainmask):
			fname = os.path.splitext(os.path.basename(self.inputs.nativeT1))[0]
			dname = os.path.dirname(self.inputs.nativeT1)
			self.inputs.T1brainmask = dname +os.sep+ fname + "_brainmask.mnc"


		run_resample = ResampleCommand();
		run_resample.inputs.in_file = model_headmask
		run_resample.inputs.out_file = self.inputs.T1headmask
		run_resample.inputs.model_file = self.inputs.nativeT1
		run_resample.inputs.transformation = run_xfminvert.inputs.out_file
		run_resample.inputs.interpolation = 'nearest_neighbour'
		run_resample.inputs.clobber = True
		if self.inputs.verbose:
		    print run_resample.cmdline
		if self.inputs.run:
		    run_resample.run()


		run_resample = ResampleCommand();
		run_resample.inputs.in_file = self.inputs.brainmaskTal
		run_resample.inputs.out_file = self.inputs.T1brainmask
		run_resample.inputs.model_file = self.inputs.nativeT1
		run_resample.inputs.transformation = run_xfminvert.inputs.out_file
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

        return outputs  





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
	RefmaskTemplate  = File(exists=True, desc="Reference mask on the template")
	close = traits.Bool(usedefault=True, default_value=True, desc="erosion(dilation(X))")
	refGM = traits.Bool(usedefault=True, default_value=True, desc="Only gray matter")
	refWM = traits.Bool(usedefault=True, default_value=True, desc="Only white matter")

	RefmaskTal  = File(desc="Reference mask in Talairach space")
	RefmaskT1  = File(desc="Reference mask in the native space")
	
	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class RefmaskingOutput(TraitedSpec):
	RefmaskTal  = File(mandatory=True, desc="Reference mask in Talairach space")
	RefmaskT1  = File(mandatory=True, desc="Reference mask in the native space")

class RefmaskingRunning(BaseInterface):
    input_spec = RefmaskingInput
    output_spec = RefmaskingOutput
    _suffix = "_RefMask"

  #   def _parse_inputs(self, skip=None):
		# if skip is None:
		# 	skip = []
		# if not isdefined(self.inputs.RefmaskT1):
		# 	self.inputs.RefmaskT1 = fname_presuffix(self.inputs.nativeT1, suffix=self._suffix)
		# if not isdefined(self.inputs.RefmaskTal):
		# 	self.inputs.RefmaskTal = fname_presuffix(self.inputs.T1Tal, suffix=self._suffix)



    def _run_interface(self, runtime):
		tmpDir = tempfile.mkdtemp()
		# self._parse_inputs()

		if not isdefined(self.inputs.RefmaskT1):
			self.inputs.RefmaskT1 = fname_presuffix(self.inputs.nativeT1, suffix=self._suffix)
		if not isdefined(self.inputs.RefmaskTal):
			self.inputs.RefmaskTal = fname_presuffix(self.inputs.T1Tal, suffix=self._suffix)
		
		if self.inputs.MaskingType == 'no-transform':
			run_resample = ResampleCommand();
			run_resample.inputs.in_file = self.inputs.RefmaskTemplate
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
			run_nlinreg.inputs.in_source_file = self.inputs.T1Tal
			run_nlinreg.inputs.in_file_target_file = model_T1
			run_nlinreg.inputs.in_file_source_mask = self.inputs.brainmaskTal
			run_nlinreg.inputs.in_file_target_mask = model_T1_mask
			run_nlinreg.inputs.out_file_xfm = T1toModel_ref_xfm
			run_nlinreg.inputs.clobber = self.inputs.clobber;
			run_nlinreg.inputs.verbose = self.inputs.verbose;
			run_nlinreg.inputs.run = self.inputs.run;
			run_nlinreg.run()

			run_resample = ResampleCommand();
			run_resample.inputs.in_file = self.inputs.RefmaskTemplate
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
			run_calc.inputs.in_file = self.inputs.segMaskTal
			run_calc.inputs.out_file = mask
			run_calc.inputs.expression = 'A[0] == ' + str(self.inputs.segLabels[0]) + ' || A[0] == ' + str(self.inputs.segLabels[1]) + '? 1 : 0'
			if self.inputs.verbose:
				print run_calc.cmdline
			if self.inputs.run:
				run_calc.run()

			if self.inputs.close:
				run_mincmorph = MorphCommand()
				run_mincmorph.inputs.in_file = mask
				run_mincmorph.inputs.out_file = mask_clean
				run_mincmorph.inputs.successive='CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC'
				run_mincmorph.inputs.verbose=True			 
  				run_mincmorph.inputs.clobber = True
				if self.inputs.verbose:
					print run_mincmorph.cmdline
				if self.inputs.run:
					run_mincmorph.run()
			else:
  				# mask_clean = mask
				if self.inputs.verbose:
					cmd=' '.join(['cp', mask, mask_clean])
					print(cmd)
				if self.inputs.run:
					shutil.copy(mask, mask_clean)
			
  			if self.inputs.refGM or self.inputs.refWM:
  				if self.inputs.refGM:
					run_calc = CalcCommand();
					run_calc.inputs.in_file = [mask_clean, self.inputs.clsmaskTal]
					run_calc.inputs.out_file = self.inputs.RefmaskTal
					run_calc.inputs.expression = 'A[0] == 1 && A[1] == 2 ? 1 : 0'
					if self.inputs.verbose:
						print run_calc.cmdline
					if self.inputs.run:
						run_calc.run()

				if self.inputs.refWM:
					run_calc = CalcCommand();
					run_calc.inputs.in_file = [mask_clean, self.inputs.clsmaskTal]
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
					shutil.copy(mask_clean, self.inputs.RefmaskTal)

		run_xfminvert = InvertCommand();
		run_xfminvert.inputs.in_file = self.inputs.LinT1TalXfm
		if self.inputs.verbose:
		    print run_xfminvert.cmdline
		if self.inputs.run:
		    run_xfminvert.run()

		run_resample = ResampleCommand();
		run_resample.inputs.in_file = self.inputs.RefmaskTal
		run_resample.inputs.out_file = self.inputs.RefmaskT1
		run_resample.inputs.model_file = self.inputs.nativeT1
		run_resample.inputs.transformation = run_xfminvert.inputs.out_file
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

		return outputs






class PETheadMaskingOutput(TraitedSpec):
	out_file  = File(desc="Headmask from PET volume")

class PETheadMaskingInput(BaseInterfaceInputSpec):
	in_file = File(exists=True, mandatory=True, desc="PET volume")
	in_json = File(exists=True, mandatory=True, desc="PET json file")
	out_file = File(desc="Head mask")
	
	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETheadMaskingRunning(BaseInterface):
    input_spec = PETheadMaskingInput
    output_spec = PETheadMaskingOutput
    _suffix = "_headMask"


    # def _parse_inputs(self, skip=None):
    #     if skip is None:
    #         skip = []
    #     if not isdefined(self.inputs.out_file):
    #         self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
    #     return super(PETheadMaskingRunning, self)._parse_inputs(skip=skip)


    def _run_interface(self, runtime):

		tmpDir = tempfile.mkdtemp()

		if not isdefined(self.inputs.out_file):
			self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)

		#hd = load_json(self.inputs.in_json)
		# dim = hd['xspace']['length']+hd['yspace']['length']+hd['zspace']['length']+hd['time']['length']
		
		infile = volumeFromFile(self.inputs.in_file)

		mean_slices = []
		for ii in np.arange(1,infile.sizes[infile.dimnames.index("zspace")],1):
			slice_tmp = tmpDir + '/pet_slice.mnc'

			run_mincreshape=ReshapeCommand()
			run_mincreshape.inputs.in_file = self.inputs.in_file
			run_mincreshape.inputs.out_file = slice_tmp
			run_mincreshape.inputs.dimrange = 'zspace='+str(ii)
			if self.inputs.verbose:
			    print run_mincreshape.cmdline
			if self.inputs.run:
			    run_mincreshape.run()


			run_stats=StatsCommand()
			run_stats.inputs.in_file = slice_tmp;
			run_stats.inputs.opt_string = '-max';
			if self.inputs.verbose:
			    print run_stats.cmdline
			if self.inputs.run:
			    run_stats.run()


			outfile = os.path.join(os.getcwd(), 'stat_result.pck')
			file = open(outfile, "r")
			max_slice = pickle.load(file)
			max_slice = max_slice/4


			run_stats=StatsCommand()
			run_stats.inputs.in_file = slice_tmp;
			run_stats.inputs.opt_string = '-floor '+str(max_slice)+' -mean ';
			if self.inputs.verbose:
			    print run_stats.cmdline
			if self.inputs.run:
			    run_stats.run()

			outfile = os.path.join(os.getcwd(), 'stat_result.pck')
			file = open(outfile, "r")
			mean_slice = pickle.load(file)

			mean_slices.append(mean_slice)

		threshold = np.mean(mean_slices)
		threshold = threshold/3

		mask_slices = []
		for ii in np.arange(1,infile.sizes[infile.dimnames.index("zspace")],1):
			slice_tmp = tmpDir + '/pet_slice.mnc'
			mask_tmp = tmpDir + '/mask_slice' + str(ii) + '.mnc'

			run_mincreshape=ReshapeCommand()
			run_mincreshape.inputs.in_file = self.inputs.in_file
			run_mincreshape.inputs.out_file = slice_tmp
			run_mincreshape.inputs.dimrange = 'zspace='+str(ii)
			if self.inputs.verbose:
			    print run_mincreshape.cmdline
			if self.inputs.run:
			    run_mincreshape.run()

			run_calc = CalcCommand();
			run_calc.inputs.in_file = slice_tmp
			run_calc.inputs.out_file = mask_tmp
			run_calc.inputs.expression = 'A[0] >= '+str(threshold)+' ? 1 : 0'
			if self.inputs.verbose:
				print run_calc.cmdline
			if self.inputs.run:
				run_calc.run()

			mask_slices.append(mask_tmp)

		mask_tmp = tmpDir + '/headmask.mnc'

		run_concat=ConcatCommand()
		run_concat.inputs.in_file = mask_slices
		run_concat.inputs.out_file = mask_tmp
		run_concat.inputs.dimension = 'zspace'
		# run_concat.inputs.start = hd['zspace']['start'][0]
		# run_concat.inputs.step = hd['zspace']['step'][0]
		run_concat.inputs.start = infile.starts[infile.dimnames.index("zspace")]
		run_concat.inputs.step = infile.separations[infile.dimnames.index("zspace")]
		if self.inputs.verbose:
		    print run_concat.cmdline
		if self.inputs.run:
		    run_concat.run()

		run_resample = ResampleCommand();
		run_resample.inputs.in_file = mask_tmp
		run_resample.inputs.out_file = self.inputs.out_file
		run_resample.inputs.model_file = self.inputs.in_file
		run_resample.inputs.interpolation = 'trilinear'
		if self.inputs.verbose:
		    print run_resample.cmdline
		if self.inputs.run:
		    run_resample.run()

		return runtime


    def _list_outputs(self):
		outputs = self.output_spec().get()
		outputs["out_file"] = self.inputs.out_file

		return outputs
