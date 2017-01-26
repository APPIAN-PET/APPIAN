import os
import numpy as np
import tempfile
import shutil
import pickle
import ntpath 

from pyminc.volumes.factory import *
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
#from nipype.interfaces.minc.base import Info
from nipype.interfaces.utility import Rename


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
	# LinT1TalXfm = File(exists=True, mandatory=True, desc="Transformation matrix to register T1 image into Talairach space")
	LinTalT1Xfm = File(exists=True, mandatory=True, desc="Inverted transformation matrix to register T1 image into Talairach space")
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
		model_headmask = self.inputs.modelDir+"/mni_icbm152_t1_tal_nlin_asym_09a_headmask.mnc"
		
		# run_xfminvert = InvertCommand();
		# run_xfminvert.inputs.in_file = self.inputs.LinT1TalXfm
		# #run_xfminvert.inputs.out_file_xfm = self.inputs.Lintalt1Xfm

		# if self.inputs.verbose:
		#     print run_xfminvert.cmdline
		# if self.inputs.run:
		#     run_xfminvert.run()


		#print "\n\n\nXFM Invert file created:"
		#print run_xfminvert.inputs.out_file
		#print "\n\n\n"
		if not isdefined(self.inputs.T1headmask):
			fname = os.path.splitext(os.path.basename(self.inputs.nativeT1))[0]
			dname = os.getcwd() #os.path.dirname(self.inputs.nativeT1)
			self.inputs.T1headmask = dname+ os.sep+fname + "_headmask.mnc"

		if not isdefined(self.inputs.T1brainmask):
			fname = os.path.splitext(os.path.basename(self.inputs.nativeT1))[0]
			dname = dname = os.getcwd()  #os.path.dirname(self.inputs.nativeT1)
			self.inputs.T1brainmask = dname + os.sep + fname + "_braimmask.mnc"

		run_resample = ResampleCommand();
		run_resample.inputs.in_file = model_headmask
		run_resample.inputs.out_file = self.inputs.T1headmask
		run_resample.inputs.model_file = self.inputs.nativeT1
		# run_resample.inputs.transformation = run_xfminvert.inputs.out_file
		run_resample.inputs.transformation = self.inputs.LinTalT1Xfm
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
		# run_resample.inputs.transformation = run_xfminvert.inputs.out_file
		run_resample.inputs.transformation = self.inputs.LinTalT1Xfm
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





class RegionalMaskingInput(BaseInterfaceInputSpec):
	nativeT1 = File(exists=True, mandatory=True, desc="Native T1 image")
	T1Tal = File(exists=True, mandatory=True, desc="T1 image normalized into Talairach space")
	# LinT1TalXfm = File(exists=True, mandatory=True, desc="Transformation matrix to register T1 image into Talairach space")
	LinTalT1Xfm = File(exists=True, mandatory=True, desc="Inverted transformation matrix to register T1 image into Talairach space")
	brainmaskTal  = File(exists=True, desc="Brain mask image in Talairach space")
	clsmaskTal  = File(exists=True, desc="Classification mask in Talairach space")
	segMaskTal  = File(exists=True, desc="Segmentation mask in Talairach space")

	PETVolume = File(exists=True, desc="3D PET volume")

	# pet2mriXfm = File(exists=True, desc="Transformation from PET to MRI")
	# mri2petXfm = File(exists=True, desc="Transformation from MRI to PET")

	segLabels = traits.Array(usedefault=True, value=[67, 76], desc="Label value(s) of reference region from ANIMAL. By default, cerebellum labels")
	
	subjectROI=File(desc="Segmentation mask for subject")

	_methods = ['roi-user', 'animal', 'civet', 'icbm152', 'atlas'] 
	MaskingType = traits.Enum(*_methods, mandatory=True, desc="Masking approaches")
	modelDir = traits.Str(desc="Model's directory")
	model = traits.Str(desc="Template image")
	roi_dir = File(desc="Segmentation mask in Talairach space")
	ROIMask  = File(desc="Mask on the template")
	close = traits.Bool(usedefault=False, default_value=False, desc="erosion(dilation(X))")
	refGM = traits.Bool(usedefault=False, default_value=False, desc="Only gray matter")
	refWM = traits.Bool(usedefault=False, default_value=False, desc="Only white matter")

	RegionalMaskTal = File(desc="Reference mask in Talairach space")
	RegionalMaskT1  = File(desc="Reference mask in the T1 native space")
	# RegionalMaskPET = File(desc="Reference mask in the PET native space")

	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class RegionalMaskingOutput(TraitedSpec):
	RegionalMaskTal  = File(mandatory=True, desc="Reference mask in Talairach space")
	RegionalMaskT1  = File(mandatory=True, desc="Reference mask in the T1 native space")
	# RegionalMaskPET  = File(mandatory=True, desc="Reference mask in the PET native space")

class RegionalMaskingRunning(BaseInterface):
    input_spec = RegionalMaskingInput
    output_spec = RegionalMaskingOutput
    _suffix = "_RegionalMask"

    def _gen_output(self, basefile, _suffix):
		fname = ntpath.basename(basefile)
		fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
		dname = os.getcwd() 
		return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _run_interface(self, runtime):
		tmpDir = tempfile.mkdtemp()
		# self._parse_inputs()

		if not isdefined(self.inputs.RegionalMaskT1):
			self.inputs.RegionalMaskT1 = self._gen_output(self.inputs.nativeT1, self._suffix+'T1') # fname_presuffix(self.inputs.nativeT1, suffix=self._suffix)
		if not isdefined(self.inputs.RegionalMaskTal):
			self.inputs.RegionalMaskTal = self._gen_output(self.inputs.nativeT1, self._suffix+'TAL') # fname_presuffix(self.inputs.T1Tal, suffix=self._suffix)
		# if not isdefined(self.inputs.RegionalMaskPET):
		# 	self.inputs.RegionalMaskPET = self._gen_output(self.inputs.nativeT1, self._suffix+'PET') #fname_presuffix(self.inputs.PETVolume, suffix=self._suffix)

		print "\n\nMasking Type:"
		print self.inputs.MaskingType
		print "\n\n"
		#Option 1: Transform the atlas to have same resolution as T1 native 
		if self.inputs.MaskingType == 'icbm152' or self.inputs.MaskingType == 'roi-user':
			print "\nRUNNING OPTION 1\n"
			run_resample = ResampleCommand();
			if self.inputs.MaskingType == 'roi-user':
				run_resample.inputs.in_file = self.inputs.subjectROI #Subject specific ROI
			else:
				run_resample.inputs.in_file = self.inputs.ROIMask #Stereotaxic mask
			run_resample.inputs.out_file = self.inputs.RegionalMaskTal
			run_resample.inputs.model_file = self.inputs.T1Tal
			run_resample.inputs.clobber = True
			if self.inputs.verbose:
			    print run_resample.cmdline
			if self.inputs.run:
			    run_resample.run()
			
		#Option 2: Use a nonlinear transform to coregister the template of the atlas to the T1
		elif self.inputs.MaskingType == 'atlas':
			print "\nRUNNING OPTION 2\n"

			sourceToModel_xfm = tmpDir+"/T1toModel_ref.xfm"
			run_nlinreg=reg.nLinRegRunning();
			run_nlinreg.inputs.in_source_file = self.inputs.T1Tal

			#if not self.inputs.model:
				#No alternate template was specified, use MNI ICBM152
				#Deform from MNI ICBM152 to subject stereotaxic
			#	run_nlinreg.inputs.in_target_file = self.inputs.modelDir+"/mni_icbm152_t1_tal_nlin_asym_09b.mnc" #QUESTION: can't we just use the default setting?
			#	run_nlinreg.inputs.in_source_mask = self.inputs.brainmaskTal
			#	run_nlinreg.inputs.in_target_mask = self.inputs.modelDir+"/mni_icbm152_t1_tal_nlin_asym_09b_mask.mnc"
			#else:
				#Use alternate template
			run_nlinreg.inputs.in_target_file = self.inputs.model
			run_nlinreg.inputs.out_file_xfm = sourceToModel_xfm	# xfm file for the transformation from template to subject stereotaxic
			run_nlinreg.inputs.clobber = self.inputs.clobber; 
			run_nlinreg.inputs.verbose = self.inputs.verbose;
			run_nlinreg.inputs.run = self.inputs.run;
			# run_nlinreg.run() #Calculate transformation from subject stereotaxic space to model template
			if self.inputs.verbose:
			    print run_nlinreg.cmdline
			if self.inputs.run:
			    run_nlinreg.run() #Resample the template atlas to subject stereotaxic space 
			
			run_resample = ResampleCommand(); 
			run_resample.inputs.in_file = self.inputs.ROIMask
			run_resample.inputs.out_file = self.inputs.RegionalMaskTal
			run_resample.inputs.model_file = self.inputs.T1Tal
			run_resample.inputs.transformation = sourceToModel_xfm
			run_resample.inputs.interpolation = 'nearest_neighbour'
			run_resample.inputs.clobber = True
			if self.inputs.verbose:
			    print run_resample.cmdline
			if self.inputs.run:
			    run_resample.run() #Resample the template atlas to subject stereotaxic space 
			
			print "\n\nFinished running nlinreg: " + self.inputs.RegionalMaskTal

		#Option 3: ANIMAL (or CIVET)
		elif self.inputs.MaskingType == 'civet' or self.inputs.MaskingType == 'animal':
			print "\nRUNNING OPTION 3\n"
			mask = tmpDir+"/mask.mnc"
			mask_clean = tmpDir+"/mask_clean.mnc"
			machin = self.inputs.segLabels
			#self.inputs.RegionalMaskTal = self.inputs.ROIMask
			#if self.inputs.refGM or self.inputs.refWM:

			#FIXME: Add option to concatenate labeled regions into a single region
			
			run_calc = CalcCommand(); #Extract the desired labels from the atlas using minccalc.
			run_calc.inputs.in_file = self.inputs.ROIMask #The ANIMAL or CIVET classified atlas
			run_calc.inputs.out_file = mask #Output mask with desired labels
			#Select region from each hemisphere of ANIMAL:
			image_string=" || ".join([ 'A[0] == ' + str(labels) + ' ' for labels in self.inputs.segLabels ])
			#run_calc.inputs.expression = 'A[0] == ' + str(self.inputs.segLabels[0]) + ' || A[0] == ' + str(self.inputs.segLabels[1]) + '? 1 : 0'  
			# run_calc.inputs.expression = image_string + ' ? A[0] : 0'  
			run_calc.inputs.expression = image_string + ' ? A[0] : 0'  
			if self.inputs.verbose:
				print run_calc.cmdline
			if self.inputs.run:
				run_calc.run()
			
			#If we need to close the region, use mincmorph.
			#QUESTION: Why have the option to close all regions regardless of whether its an ROI
			#			or a reference region? Shouldn't there be a distrinction between the ROI
			#			and reference region? 
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
				if self.inputs.verbose:
					cmd=' '.join(['cp', mask, mask_clean])
					print(cmd)
				if self.inputs.run:
					shutil.copy(mask, mask_clean)
			

			#QUESTION:  If we already have the segmentation, why add the mask_class to GM or WM?
			if self.inputs.refGM:
				run_calc = CalcCommand();
				run_calc.inputs.in_file = [mask_clean, self.inputs.clsmaskTal]
				run_calc.inputs.out_file = self.inputs.RegionalMaskTal
				run_calc.inputs.expression = 'A[0] == 1 && A[1] == 2 ? 1 : 0' 
				if self.inputs.verbose:
					print run_calc.cmdline
				if self.inputs.run:
					run_calc.run()

			if self.inputs.refWM:
				run_calc = CalcCommand();
				run_calc.inputs.in_file = [mask_clean, self.inputs.clsmaskTal]
				run_calc.inputs.out_file = self.inputs.RegionalMaskTal
				run_calc.inputs.expression = 'A[0] == 1 && A[1] == 3 ? 1 : 0' 
				if self.inputs.verbose:
					print run_calc.cmdline
				if self.inputs.run:
					run_calc.run()
			#else:
			if self.inputs.verbose:
				cmd=' '.join(['cp', mask_clean, self.inputs.RegionalMaskTal])
				print(cmd)
			if self.inputs.run:
				shutil.copy(mask_clean, self.inputs.RegionalMaskTal)
		else: 
			print "No mask type specified"
			exit(1)
		
		#FIXME: inversion of transformation file should probably be its own node.
		#Invert transformation from Tal to T1
		# run_xfminvert = InvertCommand();
		# run_xfminvert.inputs.in_file = self.inputs.LinT1TalXfm
		# if self.inputs.verbose:
		#     print run_xfminvert.cmdline
		# if self.inputs.run:
		#     run_xfminvert.run() #Invert xfm file to get Tal to T1 transformation

		# #Invert transformation from PET to T1
		# run_xfmpetinvert = InvertCommand();
		# run_xfmpetinvert.inputs.in_file = self.inputs.pet2mriXfm
		# if self.inputs.verbose:
		#     print run_xfmpetinvert.cmdline
		# if self.inputs.run:
		#     run_xfmpetinvert.run()

		run_resample = ResampleCommand(); #Resample regional mask to T1 native
		run_resample.inputs.in_file = self.inputs.RegionalMaskTal
		run_resample.inputs.out_file = self.inputs.RegionalMaskT1
		run_resample.inputs.model_file = self.inputs.nativeT1
		# run_resample.inputs.transformation = run_xfminvert.inputs.out_file
		run_resample.inputs.transformation = self.inputs.LinTalT1Xfm
		run_resample.inputs.interpolation = 'nearest_neighbour'
		run_resample.inputs.clobber = True
		if self.inputs.verbose:
		    print run_resample.cmdline
		if self.inputs.run:
		    run_resample.run()

		# run_resample = ResampleCommand(); #Resample regional mask to T1 native
		# run_resample.inputs.in_file = self.inputs.RegionalMaskT1
		# run_resample.inputs.out_file = self.inputs.RegionalMaskPET
		# run_resample.inputs.model_file = self.inputs.PETVolume
		# # run_resample.inputs.transformation = run_xfmpetinvert.inputs.out_file
		# run_resample.inputs.transformation = self.inputs.mri2petXfm
		# run_resample.inputs.interpolation = 'nearest_neighbour'
		# run_resample.inputs.clobber = True
		# if self.inputs.verbose:
		#     print run_resample.cmdline
		# if self.inputs.run:
		#     run_resample.run()		

		shutil.rmtree(tmpDir)
		return runtime


    def _list_outputs(self):
		outputs = self.output_spec().get()
		outputs["RegionalMaskTal"] = self.inputs.RegionalMaskTal #Masks in stereotaxic space
		outputs["RegionalMaskT1"] = self.inputs.RegionalMaskT1 #Masks in native space
		# outputs["RegionalMaskPET"] = self.inputs.RegionalMaskPET #Masks in native space
		return outputs


class PETheadMaskingOutput(TraitedSpec):
	out_file  = File(desc="Headmask from PET volume")

class PETheadMaskingInput(BaseInterfaceInputSpec):
	in_file = File(exists=True, mandatory=True, desc="PET volume")
	in_json = File(exists=True, mandatory=True, desc="PET json file")
	out_file = File(desc="Head mask")
	slice_factor = traits.Float(usedefault=True, default_value=0.25, desc="Value (between 0. to 1.) that is multiplied by the maximum of the slices of the PET image. Used to threshold slices. Lower value means larger mask")
	total_factor = traits.Float(usedefault=True, default_value=0.333, desc="Value (between 0. to 1.) that is multiplied by the thresholded means of each slice. ")

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

		#tmpDir = tempfile.mkdtemp()
		#print "\n\n"
		#print self.inputs.in_file
		#print "\n\n"
		if not isdefined(self.inputs.out_file):
		    self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
                #Load PET 3D volume
		infile = volumeFromFile(self.inputs.in_file)
                zmax=infile.sizes[infile.dimnames.index("zspace")]
                #Get max slice values and multiply by pet_mask_slice_threshold (0.25 by default)
                slice_thresholds=np.amax(infile.data, axis=(1,2)) * self.inputs.slice_factor
                #Get mean for all values above slice_max
                slice_mean_f=lambda t, d, i: float(np.mean(d[i, d[i,:,:] > t[i]])) 
                slice_mean = np.array([ slice_mean_f(slice_thresholds, infile.data, i)  for i in range(zmax) ])
                #Remove nan from slice_mean
                slice_mean =slice_mean[ ~ np.isnan(slice_mean) ]
                #Calculate overall mean from mean of thresholded slices
                overall_mean = np.mean(slice_mean)
                #Calcuate threshold
		threshold = overall_mean * self.inputs.total_factor
                #Apply threshold
                # and create and write outputfile
                run_calc = CalcCommand();
                run_calc.inputs.in_file = self.inputs.in_file 
                run_calc.inputs.out_file = self.inputs.out_file
                run_calc.inputs.expression = 'A[0] >= '+str(threshold)+' ? 1 : 0'
                if self.inputs.verbose:
                        print run_calc.cmdline
                if self.inputs.run:
                        run_calc.run()

		'''mean_slices = []
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
                        '''

		'''mask_slices = []
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

		shutil.rmtree(tmpDir)'''
		return runtime


    def _list_outputs(self):
		outputs = self.output_spec().get()
		outputs["out_file"] = self.inputs.out_file

		return outputs



def get_workflow(name, infosource, datasink, opts):

	workflow = pe.Workflow(name=name)

	#Define input node that will receive input from outside of workflow
	inputnode = pe.Node(niu.IdentityInterface(fields=["nativeT1nuc","xfmT1Tal","T1Tal","brainmaskTal",
													"clsmask","animalmask","subjectROI","pet_volume","pet_json"]), name='inputnode')

	#Define empty node for output
	outputnode = pe.Node(niu.IdentityInterface(fields=["t1_brainMask","t1_headMask","pet_headMask","tal_refMask",
													"t1_refMask","tal_ROIMask","t1_ROIMask","tal_PVCMask","t1_PVCMask"]), name='outputnode')


	node_name="t1Masking"
	t1Masking = pe.Node(interface=T1maskingRunning(), name=node_name)
	t1Masking.inputs.modelDir = opts.modelDir
	t1Masking.inputs.clobber = True
	t1Masking.inputs.verbose = opts.verbose
	t1Masking.inputs.run = opts.prun
	rT1MaskingHead=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"_head.mnc"), name="r"+node_name+"Head")
	rT1MaskingBrain=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"_brain.mnc"), name="r"+node_name+"Brain")


	node_name="petMasking"
	petMasking = pe.Node(interface=PETheadMaskingRunning(), name=node_name)
	petMasking.inputs.verbose = opts.verbose
	petMasking.inputs.run = opts.prun
	rPetMasking=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)


	node_name="refMasking"
	refMasking = pe.Node(interface=RegionalMaskingRunning(), name=node_name)
	refMasking.inputs.MaskingType = opts.RefMaskingType
	# refMasking.inputs.modelDir = opts.RefTemplateDir
	refMasking.inputs.model = opts.RefTemplate
	refMasking.inputs.segLabels = opts.RefAtlasLabels
	refMasking.inputs.close = opts.RefClose
	refMasking.inputs.refGM = True if opts.RefMatter == 'gm' else False
	refMasking.inputs.refWM = True if opts.RefMatter == 'wm' else False
	refMasking.inputs.clobber = True
	refMasking.inputs.verbose = opts.verbose
	refMasking.inputs.run = opts.prun
	rRefMaskingTal=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"Tal.mnc"), name="r"+node_name+"Tal")
	rRefMaskingT1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"T1.mnc"), name="r"+node_name+"T1")

	node_name="roiMasking"
	roiMasking = pe.Node(interface=RegionalMaskingRunning(), name=node_name)
	roiMasking.inputs.MaskingType = opts.ROIMaskingType
	roiMasking.inputs.model = opts.ROITemplate
	roiMasking.inputs.segLabels = opts.ROIAtlasLabels
	# roiMasking.inputs.erosion = False
	roiMasking.inputs.clobber = True
	roiMasking.inputs.verbose = opts.verbose
	roiMasking.inputs.run = opts.prun
	rROIMaskingTal=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"Tal.mnc"), name="r"+node_name+"Tal")
	rROIMaskingT1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"T1.mnc"), name="r"+node_name+"T1")

	node_name="pvcMasking"
	pvcMasking = pe.Node(interface=RegionalMaskingRunning(), name=node_name)
	pvcMasking.inputs.MaskingType = opts.PVCMaskingType
	pvcMasking.inputs.model = opts.pvcTemplate
	pvcMasking.inputs.segLabels = opts.PVCAtlasLabels
	pvcMasking.inputs.clobber = True
	pvcMasking.inputs.verbose = opts.verbose
	pvcMasking.inputs.run = opts.prun
	rPVCMaskingTal=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"Tal.mnc"), name="r"+node_name+"Tal")
	rPVCMaskingT1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"T1.mnc"), name="r"+node_name+"T1")



	node_name="Tal2T1xfm"
	invert_Tal2T1 = pe.Node(interface=InvertCommand(), name=node_name)
	invert_Tal2T1.inputs.clobber = True
	invert_Tal2T1.inputs.verbose = opts.verbose
	rInvert_Tal2T1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".xfm"), name="r"+node_name)
	




	workflow.connect([(inputnode, invert_Tal2T1, [('xfmT1Tal', 'in_file')])])

	workflow.connect([(invert_Tal2T1, rInvert_Tal2T1, [('out_file', 'in_file')])])

	workflow.connect([(infosource, rInvert_Tal2T1, [('study_prefix', 'study_prefix')]),
					  (infosource, rInvert_Tal2T1, [('sid', 'sid')]),
					  (infosource, rInvert_Tal2T1, [('cid','cid')])])

	workflow.connect(rInvert_Tal2T1, 'out_file', datasink, invert_Tal2T1.name)




	workflow.connect([(inputnode, t1Masking, [('nativeT1nuc', 'nativeT1')]), 
					  # (inputnode, t1Masking, [('xfmT1Tal', 'LinT1TalXfm')]),
					  (invert_Tal2T1, t1Masking, [('out_file', 'LinTalT1Xfm')]),
					  (inputnode, t1Masking, [('brainmaskTal', 'brainmaskTal')])])

	workflow.connect([(t1Masking, rT1MaskingBrain, [('T1brainmask', 'in_file')])])
	workflow.connect([(t1Masking, rT1MaskingHead, [('T1headmask', 'in_file')])])

	workflow.connect([(infosource, rT1MaskingBrain, [('study_prefix', 'study_prefix')]),
					  (infosource, rT1MaskingBrain, [('sid', 'sid')]),
					  (infosource, rT1MaskingBrain, [('cid','cid')])])
	workflow.connect([(infosource, rT1MaskingHead, [('study_prefix', 'study_prefix')]),
	 				  (infosource, rT1MaskingHead, [('sid', 'sid')]),
	 				  (infosource, rT1MaskingHead, [('cid','cid')])])

	workflow.connect(rT1MaskingBrain, 'out_file', datasink, t1Masking.name+"Head")
	workflow.connect(rT1MaskingHead, 'out_file', datasink, t1Masking.name+"Brain")







	workflow.connect([(inputnode, petMasking, [('pet_volume', 'in_file')]), 
					  (inputnode, petMasking, [('pet_json', 'in_json')])])

	workflow.connect([(petMasking, rPetMasking, [('out_file', 'in_file')])])

	workflow.connect([(infosource, rPetMasking, [('study_prefix', 'study_prefix')]),
					(infosource, rPetMasking, [('sid', 'sid')]),
					(infosource, rPetMasking, [('cid', 'cid')])
					])

	workflow.connect(rPetMasking, 'out_file', datasink, petMasking.name)







	workflow.connect([(inputnode, roiMasking, [('nativeT1nuc','nativeT1')]),
                      (inputnode, roiMasking, [('T1Tal','T1Tal')]),
                      # (inputnode, roiMasking, [('xfmT1Tal','LinT1TalXfm')]),
                      (invert_Tal2T1, roiMasking, [('out_file', 'LinTalT1Xfm')]),
                      (inputnode, roiMasking, [('brainmaskTal','brainmaskTal')]),
                      (inputnode, roiMasking, [('clsmask','clsmaskTal')]),
                      (inputnode, roiMasking, [('animalmask','segMaskTal')])
                    ])

	if opts.ROIMaskingType == "roi-user":
		workflow.connect([(inputnode, roiMasking, [('subjectROI','ROIMask')])])	
	elif opts.ROIMaskingType in [ "animal" ]:
		workflow.connect([(inputnode, roiMasking, [('animalmask','ROIMask')])]) 
	elif opts.ROIMaskingType in [ "civet" ]:
		workflow.connect([(inputnode, roiMasking, [('clsmask','ROIMask')])])
	elif opts.ROIMaskingType in [ "icbm152", "atlas"] :
		roiMasking.inputs.ROIMask=opts.ROIMask


	workflow.connect([(roiMasking, rROIMaskingTal, [('RegionalMaskTal', 'in_file')])])
	workflow.connect([(infosource, rROIMaskingTal, [('study_prefix', 'study_prefix')]),
                      (infosource, rROIMaskingTal, [('sid', 'sid')]),
                      (infosource, rROIMaskingTal, [('cid', 'cid')])
                    ])

	workflow.connect([(roiMasking, rROIMaskingT1, [('RegionalMaskT1', 'in_file')])])
	workflow.connect([(infosource, rROIMaskingT1, [('study_prefix', 'study_prefix')]),
                      (infosource, rROIMaskingT1, [('sid', 'sid')]),
                      (infosource, rROIMaskingT1, [('cid', 'cid')])
                    ])

	workflow.connect(rROIMaskingT1, 'out_file', datasink, roiMasking.name+"T1")
	workflow.connect(rROIMaskingTal, 'out_file', datasink, roiMasking.name+"Tal")
	# workflow.connect(rROIMaskingPET, 'out_file', datasink, roiMasking.name+"PET")






	workflow.connect([(inputnode, refMasking, [('nativeT1nuc','nativeT1')]),
                      (inputnode, refMasking, [('T1Tal','T1Tal')]),
                      # (inputnode, refMasking, [('xfmT1Tal','LinT1TalXfm')]),
                      (invert_Tal2T1, refMasking, [('out_file', 'LinTalT1Xfm')]),
                      (inputnode, refMasking, [('brainmaskTal','brainmaskTal' )]),
                      (inputnode, refMasking, [('clsmask','clsmaskTal')]),
                      (inputnode, refMasking, [('animalmask','segMaskTal' )])
                    ])
  
	if opts.RefMaskingType == "roi-user":
		workflow.connect([(inputnode, refMasking, [('subjectROI','ROIMask')]) ])	
	elif opts.RefMaskingType in [ "animal" ]:
		workflow.connect([(inputnode, refMasking, [('animalmask','ROIMask')]) ]) 
	elif opts.RefMaskingType in [ "civet" ]:
		workflow.connect([(inputnode, refMasking, [('clsmask','ROIMask')]) ])
	elif opts.RefMaskingType in [ "icbm152", "atlas"] :
		refMasking.inputs.ROIMask=opts.ROIMask






	workflow.connect([(refMasking, rRefMaskingTal, [('RegionalMaskTal', 'in_file')])])
	workflow.connect([(infosource, rRefMaskingTal, [('study_prefix', 'study_prefix')]),
                      (infosource, rRefMaskingTal, [('sid', 'sid')]),
                      (infosource, rRefMaskingTal, [('cid', 'cid')])
                    ])	

	workflow.connect([(refMasking, rRefMaskingT1, [('RegionalMaskT1', 'in_file')])])
	workflow.connect([(infosource, rRefMaskingT1, [('study_prefix', 'study_prefix')]),
                      (infosource, rRefMaskingT1, [('sid', 'sid')]),
                      (infosource, rRefMaskingT1, [('cid', 'cid')])
                    ])

	workflow.connect(rRefMaskingT1, 'out_file', datasink, refMasking.name+"T1")
	workflow.connect(rRefMaskingTal, 'out_file', datasink, refMasking.name+"Tal")
	# workflow.connect(rRefMaskingPET, 'out_file', datasink, refMasking.name+"PET")






	workflow.connect(rT1MaskingBrain, 'out_file', outputnode, 't1_brainMask')
	workflow.connect(rT1MaskingHead, 'out_file', outputnode, 't1_headMask')
	workflow.connect(rPetMasking, 'out_file', outputnode, 'pet_headMask')
	workflow.connect(rRefMaskingTal, 'out_file', outputnode, 'tal_refMask')
	workflow.connect(rRefMaskingT1, 'out_file', outputnode, 't1_refMask')
	workflow.connect(rROIMaskingTal, 'out_file', outputnode, 'tal_ROIMask')
	workflow.connect(rROIMaskingT1, 'out_file', outputnode, 't1_ROIMask')






	if not opts.nopvc:
		workflow.connect([(inputnode, pvcMasking, [('nativeT1nuc','nativeT1')]),
	                      (inputnode, pvcMasking, [('T1Tal','T1Tal')]),
	                      # (inputnode, pvcMasking, [('xfmT1Tal','LinT1TalXfm')]),
	                      (invert_Tal2T1, pvcMasking, [('out_file', 'LinTalT1Xfm')]),
	                      (inputnode, pvcMasking, [('brainmaskTal','brainmaskTal' )]),
	                      (inputnode, pvcMasking, [('clsmask','clsmaskTal')]),
	                      (inputnode, pvcMasking, [('animalmask','segMaskTal' )])
	                    ])


		if opts.PVCMaskingType == "roi-user":
			workflow.connect([(inputnode, pvcMasking, [('subjectROI','ROIMask')]) ])	
		elif opts.PVCMaskingType in [ "animal" ]:
			workflow.connect([(inputnode, pvcMasking, [('animalmask','ROIMask')]) ]) 
		elif opts.PVCMaskingType in [ "civet" ]:
			workflow.connect([(inputnode, pvcMasking, [('clsmask','ROIMask')]) ])
		elif opts.PVCMaskingType in [ "icbm152", "atlas"] :
			pvcMasking.inputs.ROIMask=opts.ROIMask

		workflow.connect([(pvcMasking, rPVCMaskingTal, [('RegionalMaskTal', 'in_file')])])
		workflow.connect([(infosource, rPVCMaskingTal, [('study_prefix', 'study_prefix')]),
	                      (infosource, rPVCMaskingTal, [('sid', 'sid')]),
	                      (infosource, rPVCMaskingTal, [('cid', 'cid')])
	                    ])

		workflow.connect([(pvcMasking, rPVCMaskingT1, [('RegionalMaskT1', 'in_file')])])
		workflow.connect([(infosource, rPVCMaskingT1, [('study_prefix', 'study_prefix')]),
	                      (infosource, rPVCMaskingT1, [('sid', 'sid')]),
	                      (infosource, rPVCMaskingT1, [('cid', 'cid')])
	                    ])

		workflow.connect(rPVCMaskingT1, 'out_file', datasink, pvcMasking.name+"T1")
		workflow.connect(rPVCMaskingTal, 'out_file', datasink, pvcMasking.name+"Tal")

		workflow.connect(rPVCMaskingTal, 'out_file', outputnode, 'tal_PVCMask')
		workflow.connect(rPVCMaskingT1, 'out_file', outputnode, 't1_PVCMask')


	return(workflow)

