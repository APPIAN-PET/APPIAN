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

def get_workflow(name, infosource, datasink, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["t1", "pet"]), name='inputnode')

class T1maskingInput(BaseInterfaceInputSpec):
	t1 = File(exists=True, mandatory=True, desc="Native T1 image")
	LinTalT1Xfm = File(exists=True, mandatory=True, desc="Inverted transformation matrix to register T1 image into Talairach space")
	brainmaskTal  = File(exists=True, mandatory=True, desc="Brain mask image in Talairach space")
	modelDir = traits.Str(exists=True, mandatory=True, desc="Models directory")
	T1headmask = File(desc="anatomical head mask, background removed")
	T1brainmask = File(desc="Transformation matrix to register T1 image into Talairach space")

	clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
	run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
	verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

    pet_mri_coregistration_qc(study.dir_results_temp, subject.t1, float(mri_max)*0.1, float(mri_max)*0.50, subject.coregistered_sum, float(pet_max)*0.2, float(pet_max)*0.9, offsets, 750, 750, study.dir_results_qc_coreg)


def pet_mri_coregistration_qc(dir_results_temp, mri, mri_min, mri_max, pet, pet_max, pet_min, offsets, x_size, y_size, output_dir, colour_scheme, label_string):
    axis_list=["x", "y", "z"]
    image_base=re.sub('.mnc', '', pet)
    file_list=image_base.split('/')
    n=len(file_list)
    output_base=file_list[n-1]
    concat_arg=""
    slice=dir_results_temp+"/slice.obj"
    for axis,offset in zip(axis_list,offsets):
        shell(["make_slice", mri, slice, axis, "w", str(offset)], True )
        shell(["ray_trace", "-output", image_base+"_"+axis+".rgb", "-nolight", "-gray", str(mri_min), str(mri_max), mri, str(0), str(1), "-under", "transparent", colour_scheme, str(pet_min), str(pet_max), pet, str(0), str(0.15), slice, "-size", str(x_size), str(y_size), "-bg", "black", "-crop"], True)
        concat_arg = str.join(' ', [concat_arg, image_base+"_"+axis+".rgb" ])
    shell(["montage", "-label", label_string, "-background black -flip", "-geometry +1+1+1", concat_arg, output_dir+ output_base+".jpg"], True)
    print(output_dir+ output_base+".jpg")
    #shell(["eog", output_dir+ output_base+".jpg" ],False)
    shell(["rm", slice, concat_arg], True)



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



