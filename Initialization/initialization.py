import os
import numpy as np
import tempfile
import shutil
import json
import ntpath
import shutil
import nibabel as nib
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
from Extra.utils import splitext
from sets import Set

def pexit(pstring="Error", exitcode=1):
    print(pstring)
    exit(exitcode)


class pet_brain_maskOutput(TraitedSpec):
    out_file  = File(desc="Headmask from PET volume")

class pet_brain_maskInput(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="PET volume")
    in_json = File(exists=True, mandatory=True, desc="PET json file")
    out_file = File(desc="Head mask")
    slice_factor = traits.Float(usedefault=True, default_value=0.25, desc="Value (between 0. to 1.) that is multiplied by the maximum of the slices of the PET image. Used to threshold slices. Lower value means larger mask")
    total_factor = traits.Float(usedefault=True, default_value=0.333, desc="Value (between 0. to 1.) that is multiplied by the thresholded means of each slice. ")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Int(usedefault=True, default_value=True, desc="Write messages indicating progress")

class pet_brain_mask(BaseInterface):
    input_spec = pet_brain_maskInput
    output_spec = pet_brain_maskOutput
    _suffix = "_brain_mask"

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            base = os.path.basename(self.inputs.in_file)
            split = splitext(base)
            self.inputs.out_file = os.getcwd() +os.sep + split[0] + self._suffix + split[1]
            #Load PET 3D volume
        infile = nib.load(self.inputs.in_file)
        shape=infile.get_shape()
        zmax=shape[2]
        data=infile.get_data()
        #Get max slice values and multiply by pet_mask_slice_threshold (0.25 by default)
        slice_thresholds=np.amax(data, axis=(1,2)) * self.inputs.slice_factor
        #Get mean for all values above slice_max
        slice_mean_f=lambda t, d, i: float(np.mean(d[i, d[i,:,:] > t[i]]))
        slice_mean = np.array([slice_mean_f(slice_thresholds, data, i) for i in range(zmax) ])
        #Remove nan from slice_mean
        slice_mean =slice_mean[ ~ np.isnan(slice_mean) ]
        #Calculate overall mean from mean of thresholded slices
        overall_mean = np.mean(slice_mean)
        #Calcuate threshold
        threshold = overall_mean * self.inputs.total_factor
        #Apply threshold and create and write outputfile
        
        idx = data >= threshold
        data[ idx ] = 1
        data[~idx ] = 0

        outfile = nib.Nifti1Image(data, infile.get_affine())
        outfile.to_file(self.inputs.out_file)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
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
        frame_times=[]
        try :
            frame_times = d["Time"]["FrameTimes"]["Values"]
        except KeyError :
            print("\nError Could not find Time:FrameTimes:Values in header\n")
            exit(1)
        FrameLengths=[]

        c0=c1=1 #Time unit conversion variables. Time should be in seconds
        try :
            if d["Time"]["FrameTimes"]["Units"][0] == 'm' :
                c0=60
            elif d["Time"]["FrameTimes"]["Units"][0] == 'h' :
                c0=60*60
            if d["Time"]["FrameTimes"]["Units"][1] == 'm' :
                c1=60
            elif d["Time"]["FrameTimes"]["Units"][1] == 'h' :
                c1=60*60
        except KeyError :
            print("\nError Could not find Time:FrameTimes:Units in header\n")
            exit(1)

        for s, e in frame_times :
            FrameLengths.append(c1*e - c0*s)

        d["Time"]["FrameTimes"]["Duration"] = FrameLengths
        return d

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file=os.getcwd() +os.sep+ os.path.basename(self.inputs.in_file)
        d=json.load(open(self.inputs.in_file,'r')) 
        
        fields=[["Time","FrameTimes","Units"],
                ["Time","FrameTimes","Values"],
                ]
        if self.inputs.quant_method == "suv" :
            fields.append([["Info","BodyWeight"],
                    ["RadioChem", "InjectedRadioactivity"],
                    ["InjectedRadioactivityUnits", "kBq"]])

        for f in fields :
            try :
                test_dict=d
                for key in f :
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
    run = traits.Str(desc="Run ID")
    #compression = traits.Str(desc="Compression")
    RoiSuffix = traits.Str(desc="Suffix for subject ROI")

class SplitArgsInput(BaseInterfaceInputSpec):
    task = traits.Str(desc="Task ID")
    ses = traits.Str(desc="Session ID")
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

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        infile = nib.load(self.inputs.in_file)
        shape=infile.get_shape()

        if len(shape) >= 4 :
            affine=infile.get_affine()
            data = infile.get_data()
            ti=np.argmin(data.shape)
            dims = list(data.shape) 
            dims.remove(dims[ti])

            nFrames = shape[ti]
            rank=0.20

            first=int(floor(nFrames*rank))
            last=nFrames
            
            volume_subsets=np.split(data, [first,last], axis=ti) 
            volume_subset=volume_subsets[1]
            
            volume_average=np.mean(volume_subset, axis=ti)
            print("Frames to concatenate -- First:", first, "Last:", last) 
            outfile = nib.Nifti1Image(volume_average, affine)
            nib.save(outfile, self.inputs.out_file)
        else :
            #If there is no "time" dimension (i.e., in 3D file), just copy the PET file
            shutil.copy(self.inputs.in_file, self.inputs.out_file)
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
        1. Centering the PET image: petCenter
        2. Exlcude start and end frames: petExcludeFr
        3. Average 4D PET image into 3D image: petVolume
        4. Extract information from header

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
   
    if opts.pet_brain_mask :
        petBrainMask=pe.Node(pet_brain_mask(), "pet_brain_mask")
        workflow.connect(petVolume, 'out_file', petBrainMask, 'in_file')
        workflow.connect(petBrainMask, 'out_file', outputnode, 'pet_brain_mask')
    
    workflow.connect(petVolume, 'out_file', outputnode, 'pet_volume')
    workflow.connect(petHeader, 'out_file', outputnode, 'pet_header_json')

    return(workflow)
