import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
		BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
import wget
import os
import tarfile
import inspect
import shutil
import ntpath
import re
import glob
from numpy.random import choice
import nipype.interfaces.minc as minc

global default_lib_address
default_lib_address="http://packages.bic.mni.mcgill.ca/tgz/beast-library-1.0.tar.gz"

def utar(fn) :
	if (fn.endswith("tar.gz")):
		tar = tarfile.open(fn, "r:gz")
		tar.extractall()
		tar.close()
	elif (fn.endswith("tar")):
		tar = tarfile.open(fn, "r:")
		tar.extractall()
		tar.close()

def mincbeast_library(template, fn=default_lib_address):
        print(default_lib_address)
	base_fn=os.path.basename(fn)
	file_dir=os.path.dirname(__file__)
	base_dir = re.sub('.tar', '', base_fn)
	base_dir = re.sub('.gz', '', base_dir)
	base_dir = base_dir
	out_dir = file_dir+os.sep+base_dir
	if not os.path.exists(out_dir) : 
		wget.download(fn)
		utar(base_fn)
		shutil.move(base_dir, out_dir)
		os.remove(base_fn)
		tmp_fn = "tmp_"+ ''.join(map(str, list(choice(20,20)))) +".mnc"
		for f in glob.glob(out_dir + os.sep + "*mnc" ) : 
			rsl = minc.Resample()	
			rsl.inputs.input_file=f
			rsl.inputs.output_file=tmp_fn
			rsl.inputs.like=template
			print rsl.cmdline
			rsl.run()
			print tmp_fn, rsl.inputs.output_file
			shutil.copy( tmp_fn, f)
			#shutil.move( tmp_fn, rsl.inputs.output_file)

	return out_dir




class mincbeastOutput(TraitedSpec):
	out_file = File(argstr="%s",  desc="Brain Mask")

class mincbeastInput(CommandLineInputSpec):
	out_file = File(argstr="%s",  desc="Brain Mask", position=-1)
	in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
	library_dir = File( argstr="%s", position=-3, desc="image to operate on")
	voxel_size = traits.Int( argstr="-voxel_size %s", position=-4, default=3, use_default=True  )
	same_resolution = traits.Bool(argstr="-same_resolution", position=-5, default=True, use_default=True )

class mincbeastCommand(CommandLine):
	input_spec =  mincbeastInput
	output_spec = mincbeastOutput

	_cmd = "mincbeast"

	def _gen_output(self, basefile):
		fname = ntpath.basename(basefile)
		fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
		dname = os.getcwd() 
		return dname+ os.sep+fname_list[0] + "_brain_mask" + fname_list[1]

	def _list_outputs(self):
		if not isdefined(self.inputs.out_file):
			self.inputs.out_file = self._gen_output(self.inputs.in_file)
		outputs = self.output_spec().get()
		outputs["out_file"] = self.inputs.out_file
		return outputs

	def _parse_inputs(self, skip=None):
		if skip is None:
			skip = []
		if not isdefined(self.inputs.out_file):
			self.inputs.out_file = self._gen_output(self.inputs.in_file)

		return super(mincbeastCommand, self)._parse_inputs(skip=skip)
