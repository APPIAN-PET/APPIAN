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
from Extra.modifHeader import FixCosinesCommand
from Extra.conversion import mincconvertCommand
import numpy as np
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

def mincbeast_library(fn=default_lib_address):
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
	return out_dir

def create_alt_template(template, beast_dir, clobber=False) :
    template_rsl=os.path.splitext(template)[0] + '_rsl.mnc'
    mask=os.path.splitext(template)[0] + '_mask.mnc'
    mask_rsl_fn=os.path.splitext(template)[0] + '_rsl_mask.mnc'

    for f in glob.glob(beast_dir + os.sep + "*mnc" ) :
        if not os.path.exists(template_rsl) or clobber :
            rsl = minc.Resample()
            rsl.inputs.input_file=template
            rsl.inputs.output_file=template_rsl
            rsl.inputs.like=f
            print rsl.cmdline
            rsl.run()

        if not os.path.exists(mask_rsl_fn) or clobber :
            mask_rsl = minc.Resample()
            mask_rsl.inputs.input_file=mask
            mask_rsl.inputs.output_file=mask_rsl_fn
            mask_rsl.inputs.like=f
            mask_rsl.run()
            print(mask_rsl.cmdline)
            break
    return template_rsl



class mincbeastOutput(TraitedSpec):
	out_file = File(argstr="%s",  desc="Brain Mask")

class mincbeastInput(CommandLineInputSpec):
	out_file = File(argstr="%s",  desc="Brain Mask", position=-1)
	in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
	library_dir = File( argstr="%s", position=-3, desc="image to operate on")
	voxel_size = traits.Int( argstr="-voxel_size %s", position=-4, default=2, use_default=False  )
	same_resolution = traits.Bool(argstr="-same_resolution", position=-5, default=True, use_default=True )
	median = traits.Bool(argstr="-median", position=-6, default=True, use_default=True )
	fill = traits.Bool(argstr="-fill", position=-7, default=True, use_default=True )
	configuration = File(argstr="-configuration %s", position=-8  )

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

class mincbeast(BaseInterface):
	input_spec =  mincbeastInput
	output_spec = mincbeastOutput

	out_file = File(argstr="%s",  desc="Brain Mask", position=-1)
	in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
	library_dir = File( argstr="%s", position=-3, desc="image to operate on")
	voxel_size = traits.Int( argstr="-voxel_size %s", position=-4, default=3, use_default=True  )
	same_resolution = traits.Bool(argstr="-same_resolution", position=-5, default=True, use_default=True )
	median = traits.Bool(argstr="-median", position=-6, default=True, use_default=True )
	fill = traits.Bool(argstr="-fill", position=-7, default=True, use_default=True )
	configuration = File(argstr="-configuration %s", position=-8  )

        def _run_interface(self, runtime) :
	    if not isdefined(self.inputs.out_file):
                self.inputs.out_file = self._gen_output(self.inputs.in_file)

            beast = mincbeastCommand()
            beast.inputs.out_file = "/tmp/"+str(np.random.randint(0,9999999))+"_"+os.path.basename(self.inputs.out_file)
            beast.inputs.in_file = self.inputs.in_file
            beast.inputs.library_dir = self.inputs.library_dir
            beast.inputs.voxel_size = self.inputs.voxel_size
            beast.inputs.same_resolution = self.inputs.same_resolution
            beast.inputs.median = self.inputs.median
            beast.inputs.fill = self.inputs.fill
            beast.inputs.configuration = self.inputs.configuration
            beast.run()

            resample = FixCosinesCommand()
            resample.inputs.two = True
            resample.inputs.in_file =  beast.inputs.out_file
            resample.inputs.out_file = self.inputs.out_file
            
            print(resample.cmdline)
            resample.run()
            return runtime

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

class beast_normalizeOutput(TraitedSpec):
	out_file_vol = File(argstr="%s",  desc="Normalized image")
	out_file_xfm = File(argstr="%s",  desc="Transformation file")

class beast_normalizeInput(CommandLineInputSpec):
	out_file_xfm = File(argstr="%s", position=-1,  desc="Transformation file")
	out_file_vol = File(argstr="%s",  position=-2, desc="Normalized image")
	in_file= File(exists=True, argstr="%s", position=-3, desc="PET file")
	modelname = traits.Str( argstr="-modelname %s", position=-4, default=3, use_default=True  )
	modeldir = traits.Str( argstr="-modeldir %s", position=-5, default=3, use_default=True  )

class beast_normalize(CommandLine):
	input_spec =  beast_normalizeInput
	output_spec = beast_normalizeOutput
	_cmd = "beast_normalize"

	def _gen_output_xfm(self, basefile):
		fname = ntpath.basename(basefile)
		fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
		dname = os.getcwd()
                out_xfm=dname+ os.sep+fname_list[0] + "_normalized" + '.xfm'
                return out_xfm

	def _gen_output_vol(self, basefile):
		fname = ntpath.basename(basefile)
		fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
		dname = os.getcwd()
		out_vol=dname+ os.sep+fname_list[0] + "_normalized" + fname_list[1]
                return out_vol
            
        def _list_outputs(self):
            if not isdefined(self.inputs.out_file_xfm) :
                    self.inputs.out_file_xfm = self._gen_output_xfm(self.inputs.in_file)
            if not isdefined(self.inputs.out_file_vol):
                    self.inputs.out_file_vol = self._gen_output_vol(self.inputs.in_file)
            outputs = self.output_spec().get()
            outputs["out_file_vol"] = self.inputs.out_file_vol
            outputs["out_file_xfm"] = self.inputs.out_file_xfm
	    return outputs

	def _parse_inputs(self, skip=None):
	    if skip is None:
		skip = []
            if not isdefined(self.inputs.out_file_xfm) :
                self.inputs.out_file_xfm = self._gen_output_xfm(self.inputs.in_file)
            if not isdefined(self.inputs.out_file_vol):
                self.inputs.out_file_vol = self._gen_output_vol(self.inputs.in_file)
	    return super(beast_normalize, self)._parse_inputs(skip=skip)


class beast_normalize_with_conversion(BaseInterface):
    input_spec =  beast_normalizeInput
    output_spec = beast_normalizeOutput

    def _run_interface(self, runtime):

        if not isdefined(self.inputs.out_file_xfm) :
            self.inputs.out_file_xfm = self._gen_output_xfm(self.inputs.in_file)
        if not isdefined(self.inputs.out_file_vol):
            self.inputs.out_file_vol = self._gen_output_vol(self.inputs.in_file)
        
        
        os.mkdir( os.getcwd() + os.sep + 'tmp' )
        convert = minc.Convert()
        convert.inputs.input_file = self.inputs.in_file
        convert.inputs.output_file=os.getcwd()+os.sep+'tmp'+os.sep+ os.path.basename(self.inputs.in_file)
        print(convert.cmdline)
        convert.run()

        beast = beast_normalize()
        beast.inputs.out_file_xfm = self.inputs.out_file_xfm
        beast.inputs.out_file_vol = os.getcwd()+os.sep+'tmp'+os.sep+ "mri_norm.mnc" 
        beast.inputs.in_file = convert.inputs.output_file
        beast.inputs.modelname = self.inputs.modelname
        beast.inputs.modeldir = self.inputs.modeldir
        print(beast.cmdline)
        beast.run()

        convert2 =mincconvertCommand()
        convert2.inputs.in_file = beast.inputs.out_file_vol
        convert2.inputs.out_file=self.inputs.out_file_vol
        convert2.inputs.two=True
        print(convert2.cmdline)
        convert2.run()

        shutil.rmtree(os.getcwd()+os.sep+'tmp' )
        return runtime


    def _gen_output_xfm(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        out_xfm=dname+ os.sep+fname_list[0] + "_normalized" + '.xfm'
        return out_xfm

    def _gen_output_vol(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        out_vol=dname+ os.sep+fname_list[0] + "_normalized" + fname_list[1]
        return out_vol

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file_xfm) :
            self.inputs.out_file_xfm = self._gen_output_xfm(self.inputs.in_file)
        if not isdefined(self.inputs.out_file_vol):
            self.inputs.out_file_vol = self._gen_output_vol(self.inputs.in_file)
        outputs = self.output_spec().get()
        outputs["out_file_vol"] = self.inputs.out_file_vol
        outputs["out_file_xfm"] = self.inputs.out_file_xfm
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
                skip = []
        if not isdefined(self.inputs.out_file_vol) or not isdefined(self.inputs.out_file_vol):
                self.inputs.out_file_vol, self.inputs.out_file_xfm = self._gen_output(self.inputs.in_file)

        return super(beast_normalize, self)._parse_inputs(skip=skip)
