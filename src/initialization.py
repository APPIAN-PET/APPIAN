import os
import numpy as np
import tempfile
import shutil
import json
import ntpath
import shutil
import src.ants_nibabel as nib
import re
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from math import *
from time import gmtime, strftime
from glob import glob
from os.path import basename
from src.utils import splitext

def pexit(pstring="Error", exitcode=1):
    print(pstring)
    exit(exitcode)


class pet_brain_maskOutput(TraitedSpec):
    out_file  = traits.File(desc="Headmask from PET volume")

class pet_brain_maskInput(BaseInterfaceInputSpec):
    in_file = traits.File( desc="PET volume")
    out_file = traits.File(desc="Head mask")


import src.ants_nibabel as nib 
from skimage.filters import threshold_otsu 
import numpy as np 
from scipy.ndimage import gaussian_filter 
class petBrainMask(BaseInterface):
    input_spec = pet_brain_maskInput
    output_spec = pet_brain_maskOutput
    _suffix = "_brain_mask"

    def _pet_brain_mask(self, in_file, out_file,verbose=True):
        img = nib.load(in_file)
        vol = img.get_fdata()

        if vol.max() == vol.min() : 
            print('\nError: PET image appears to be empty',in_file)
            print('\tMin: {}, Mean: {}, Max: {}\n'.format(vol.min(), vol.mean(), vol.max()))
            exit(1)
        vol_smooth = gaussian_filter( vol, 1 ) 

        non_zero_idx = vol>0
        non_zero_vxl = vol[non_zero_idx]
        otsu_voxel_threshold = threshold_otsu(non_zero_vxl)
        vol[ vol < otsu_voxel_threshold  ] = 0 
        vol[ vol > 0 ] = 1 
        nib.Nifti1Image(vol, img.affine).to_filename(out_file)
        return 0

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            base = os.path.basename(self.inputs.in_file)
            split = splitext(base)
            self.inputs.out_file = os.getcwd() +os.sep + split[0] + self._suffix + split[1]
            #Load PET 3D volume

        self._pet_brain_mask( self.inputs.in_file, self.inputs.out_file)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


class header_output(TraitedSpec):
    out_file=traits.File(desc="Input json header file")

class header_input(BaseInterfaceInputSpec):
    in_file=traits.File(exists=True,mandatory=True,desc="Input json header file")
    out_file=traits.File(desc="Input json header file")
    quant_method = traits.Str(desc="Quant method")

class validate_header(BaseInterface):
    input_spec = header_input
    output_spec = header_output
    
    def _set_duration(self, d):
        try :
            d['FrameTimes'] =[ [s,s+d] for s,d in zip(d["FrameTimesStart"],d["FrameTimesStart"]) ]
        except KeyError :
            print("\nError Could not find Time:FrameTimes:Values in header\n")
            exit(1)
        
        return d
    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file=os.getcwd() +os.sep+ os.path.basename(self.inputs.in_file)
        d=json.load(open(self.inputs.in_file,'r')) 
        
        fields=[["FrameTimesStart"],
                ["FrameDuration"],
                ]

        if self.inputs.quant_method == "suv" :
            fields += [["BodyWeight"],
                    ["InjectedRadioactivity"],
                    ["InjectedRadioactivityUnits"]]
        print(fields)
        for f in fields :
            try :
                test_dict=d
                for key in f :
                    print(key)
                    test_dict=test_dict[key]
            except ValueError :
                pexit("Error: json header does not contain key: "+":".join(f)+"for file"+self.inputs.in_file)
        d=self._set_duration(d)
        json.dump(d,open(self.inputs.out_file,'w+'))
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file=os.getcwd() +os.sep+ os.path.basename(self.inputs.in_file)
        outputs["out_file"] = self.inputs.out_file
        return outputs

class SplitArgsOutput(TraitedSpec):
    cid = traits.Str(mandatory=True, desc="Condition ID")
    sid = traits.Str(mandatory=True, desc="Subject ID")
    task = traits.Str(desc="Task ID")
    ses = traits.Str(desc="Session ID")
    t1_ses = traits.Str(desc="Session ID")
    run = traits.Str(desc="Run ID")
    #compression = traits.Str(desc="Compression")
    RoiSuffix = traits.Str(desc="Suffix for subject ROI")

class SplitArgsInput(BaseInterfaceInputSpec):
    task = traits.Str(desc="Task ID")
    ses = traits.Str(desc="Session ID")
    t1_ses = traits.Str(desc="Session ID for T1 MRI")
    sid = traits.Str(desc="Subject ID")
    cid = traits.Str(desc="Condition ID")
    run = traits.Str(desc="Run ID")
    ses_sub_only = traits.Bool(default_value=False, usedefault=True)
    RoiSuffix = traits.Str(desc="Suffix for subject ROI")
    args = traits.Dict(mandatory=True, desc="Overwrite output file")

class SplitArgsRunning(BaseInterface):
    input_spec = SplitArgsInput
    output_spec = SplitArgsOutput
    
    def _run_interface(self, runtime):
        cid=''
        if not isdefined(self.inputs.t1_ses) :
            self.inputs.t1_ses=self.inputs.args['t1_ses']

        if not isdefined(self.inputs.ses) :
            self.inputs.ses=self.inputs.args['ses']
            cid = cid + '_' +self.inputs.args['ses']
        if not isdefined(self.inputs.sid) :
            self.inputs.sid=self.inputs.args['sid']
        if self.inputs.ses_sub_only : return runtime

        try :
            self.inputs.task=self.inputs.args['task']
            cid = cid + '_' +self.inputs.args['task']
        except  KeyError:
            pass

        try:
            self.inputs.run=self.inputs.args['run']
            cid = cid + '_' +self.inputs.args['run']
        except  KeyError:
            pass
        self.inputs.cid=cid

        if isdefined(self.inputs.RoiSuffix):
            self.inputs.RoiSuffix=self.inputs.RoiSuffix
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if isdefined(self.inputs.cid):
            outputs["cid"] = self.inputs.cid
        if isdefined(self.inputs.sid):
            outputs["sid"] = self.inputs.sid

        if isdefined(self.inputs.ses):
            outputs["ses"] = self.inputs.ses
            outputs["t1_ses"] = self.inputs.ses

        if isdefined(self.inputs.t1_ses):
            outputs["t1_ses"] = self.inputs.t1_ses
            print('hello')
        
        if isdefined(self.inputs.task):
            outputs["task"] = self.inputs.task

        if isdefined(self.inputs.run):
            outputs["run"] = self.inputs.run

        if isdefined(self.inputs.RoiSuffix):
            outputs["RoiSuffix"]= self.inputs.RoiSuffix
        return outputs

class pet3DVolumeOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class pet3DVolumeInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Image")
    out_file = File(argstr="%s", desc="Image after centering")
    verbose = traits.Int(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")



class pet3DVolume(BaseInterface):
    input_spec = pet3DVolumeInput
    output_spec = pet3DVolumeOutput
    _suffix = "_3D"

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _pet_3D_volume(self,in_file, out_file,verbose=True):
        infile = nib.load(in_file)
        shape=infile.shape

        if verbose :
            print('\tCreate 3D PET volume')
            print('\t\tInput file', in_file )
            print('\t\tOutput file', out_file )

        if len(shape) >= 4 :
            affine=infile.affine
            data = infile.get_fdata()


            if data.max() == data.min() : 
                print('\nError: PET image appears to be empty',in_file)
                print('\tMin: {}, Mean: {}, Max: {}\n'.format(vol.min(), vol.mean(), vol.max()))
            ti=np.argmin(data.shape)
            dims = list(data.shape) 
            dims.remove(dims[ti])

            nFrames = shape[ti]
            rank=0.20

            first=int(floor(nFrames*rank))
            last=nFrames
            volume_subset=data[:,:,:,first:last] #volume_subsets[1]
            volume_src=np.mean(volume_subset, axis=ti)
            if verbose :
                print("\t\tFrames to concatenate -- First:", first, "Last:", last) 
            outfile = nib.Nifti1Image(volume_src, affine)
            #outfile.set_qform(affine)
            nib.save(outfile, out_file)
        else :
            #If there is no "time" dimension (i.e., in 3D file), just copy the PET file
            shutil.copy(in_file, out_file)
        if verbose :
            print('\tDone.')

        return 0


    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)

        self._pet_3D_volume(self.inputs.in_file, self.inputs.out_file)

        return runtime

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)

        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file

        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
        return outputs

"""
.. module:: initialization
    :platform: Unix
    :synopsis: Workflow to initialize PET images
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""

def get_workflow(name, infosource, opts):
    '''
    Nipype workflow that initializes the PET images by
        1. Average 4D PET image into 3D image: petVolume
        2. Extract information from header

    :param name: Name of workflow
    :param infosource: Infosource for basic variables like subject id (sid) and condition id (cid)
    :param datasink: Node in which output data is sent
    :param opts: User options

    :returns: workflow
    '''
    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    default_field=["pet","pet_header_json"]
    inputnode = pe.Node(niu.IdentityInterface(fields=default_field), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["pet_volume","pet_header_json","pet_brain_mask"]), name='outputnode')

    petVolume = pe.Node(interface=pet3DVolume(), name="petVolume")
    petVolume.inputs.verbose = opts.verbose
    
    
    petHeader=pe.Node(interface=validate_header(), name="petHeader")
    if opts.quant_method != None :
        petHeader.inputs.quant_method=opts.quant_method
    
    workflow.connect(inputnode, 'pet_header_json', petHeader, 'in_file')
    
    workflow.connect(inputnode, 'pet', petVolume, 'in_file')
   
    if  opts.pet_brain_mask :
        petBrainMaskNode=pe.Node(interface=petBrainMask(), name="pet_brain_mask")
        workflow.connect(petVolume, 'out_file', petBrainMaskNode, 'in_file')
        workflow.connect(petBrainMaskNode, 'out_file', outputnode, 'pet_brain_mask')

    workflow.connect(petVolume, 'out_file', outputnode, 'pet_volume')
    workflow.connect(petHeader, 'out_file', outputnode, 'pet_header_json')

    return(workflow)
