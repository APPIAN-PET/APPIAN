import os
import numpy as np
import tempfile
import shutil
import json
import nipype.interfaces.minc as minc
import ntpath
import minc as pyezminc
from os.path import basename
import shutil
from math import *
from time import gmtime, strftime
from glob import glob
import re

from pyminc.volumes.factory import *

from nipype.algorithms.misc import Gunzip
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.interfaces.utility import Rename
from nipype.interfaces.minc import Resample as ResampleCommand
from Extra.minc_filemanip import update_minchd_json
from Extra.info import  InfoCommand
from Extra.modifHeader import ModifyHeaderCommand, FixCosinesCommand
from Extra.reshape import  ReshapeCommand
from Extra.modifHeader import FixHeaderCommand
#from Extra.compression import gunzipCommand, gzipCommand


global isotope_dict
isotope_dict={
        "C-11" : 20.334*60 ,
        "F-18" : 109.7*60,
        "O-15" : 122.24
        }

def string_test(s):
    t = type(s)
    if  t == str : return True
    elif t == unicode : return True
    elif t == ascii : return True
    return False


def recursive_dict_search(d, target, level=0):
    if level == 0 : print("Target:", target)
    level+=1
    for k,v  in zip(d.keys(), d.values()) :

        #End condition
        if string_test(k) :
            if target.lower() in k.lower().split("_") :
                return [k]

        #Search dictionary
        if type(v) == dict :
            test = [k] + recursive_dict_search(v, target, level)
            if not None in test :
                return test

    return [None]

def fix_df(d, target):
    dict_path = recursive_dict_search(d,target)
    temp_d = d
    value=None
    if not None in dict_path :
        for i in dict_path :
            temp_d = temp_d[i]
        value = temp_d[0]
    return value

def set_isotope_halflife(d, user_halflife=None, target="halflife"):
    #find path in dictionary to target
    dict_path = recursive_dict_search(d, target=target)
    #if there is no path to target, try backup
    if None in dict_path :
        isotope  = fix_df(d, "isotope")
        try :
            halflife = isotope_dict[ isotope ]
        except KeyError :
            if user_halflife != None :
                halflife = user_halflife
            else :
                print("Could not find either halflife or isotope")
                exit(1)
    else :
        temp_d = d
        for i in dict_path :
            temp_d = temp_d[i]
        halflife = temp_d

    if type(halflife) == list :
        halflife=halflife[0]

    try :
        d["acquisition"]
    except :
        d["acquisition"]={"radionuclide_halflife": halflife }
    else :
        d["acquisition"]["radionuclide_halflife"] = halflife

    return d



def set_frame_duration(d, minc_input=False, json_frame_path=["Time","FrameTimes","Values"], verbose=True):
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
    #compression = traits.Str(desc="Compression")
    ses_sub_only = traits.Bool(default_value=False, usedefault=True)
    #study_prefix = traits.Str(mandatory=True, desc="Study Prefix")
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

class MincHdrInfoOutput(TraitedSpec):
    out_file = File(desc="Output file")
    header = traits.Dict(desc="Dictionary")


class MincHdrInfoInput(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="Native dynamic PET image")
    halflife = traits.Float(desc="Radioisotope halflife (in seconds)")
    json_header = File(desc="PET header")
    out_file = File(desc="Output file")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class MincHdrInfoRunning(BaseInterface):
    input_spec = MincHdrInfoInput
    output_spec = MincHdrInfoOutput
    _suffix = ".info"
    _params={}

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            fname = os.path.splitext(os.path.basename(self.inputs.in_file))[0]
            dname = os.getcwd() #os.path.dirname(self.inputs.nativeT1)
            self.inputs.out_file = dname+ os.sep+fname + self._suffix
        try :
            os.remove(self.inputs.out_file)
        except OSError:
            pass

        class InfoOptions:
            def __init__(self, command, variable, attribute, type_):
                self.command = command
                self.variable = variable
                self.attribute = attribute
                self.type_ = type_

        temp_out_file=os.getcwd()+os.sep+"temp.json"

        try :
            img = pyezminc.Image(self.inputs.in_file, metadata_only=True)
            hd = img.get_MINC_header()
            for key in hd.keys():
                self._params[key]={}
                for subkey in hd[key].keys():
                    self._params[key][subkey]={}
                    data_in = hd[key][subkey]
                    var = str(key)
                    attr = str(subkey)
                    #Populate dictionary with some useful image parameters (e.g., world coordinate start values of dimensions)
                    self._params[key][subkey]=data_in
                    update_minchd_json(temp_out_file, data_in, var, attr)
        except RuntimeError :
            print("Warning: Could not read header file from", self.inputs.in_file)


        header = json.load(open(temp_out_file, "r+") )

        minc_input=True
        if not isdefined(self.inputs.json_header) :
            print("Error: could not find json file", self.inputs.json_header)
            exit(1)

        json_header = json.load(open(self.inputs.json_header, "r+"))
        header.update(json_header)
        minc_input=False

        header = set_frame_duration(header, minc_input)
        header = set_isotope_halflife(header, self.inputs.halflife, 'halflife')

        fp=open(self.inputs.out_file, "w+")
        fp.seek(0)
        json.dump(header, fp, sort_keys=True, indent=4)
        fp.close()

        self._params=header

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        outputs["header"] = self._params
        return outputs

class VolCenteringOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class VolCenteringInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Image")
    header = File(desc="Header")
    out_file = File(argstr="%s", desc="Image after centering")

    run = traits.Bool(argstr="-run", usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Int(argstr="-verbose", usedefault=True, default_value=1, desc="Write messages indicating progress")

class VolCenteringRunning(BaseInterface):
    input_spec = VolCenteringInput
    output_spec = VolCenteringOutput
    _suffix = "_center"

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            fname = os.path.splitext(os.path.basename(self.inputs.in_file))[0]
            dname = dname = os.getcwd()
            self.inputs.out_file = dname + os.sep + fname + self._suffix + '.mnc'

        temp_fn="/tmp/tmp_mnc_"+ strftime("%Y%m%d%H%M%S", gmtime())+str(np.random.randint(9999999999))+".mnc"
        shutil.copy(self.inputs.in_file, temp_fn)
        #infile = volumeFromFile(self.inputs.in_file)
        infile = nib.load(self.inputs.in_file)
        #infile = volumeFromFile(self.inputs.in_file)
        #infile = nib.load(self.inputs.in_file)

        for view in ['xspace','yspace','zspace']:
            dim = infile.dimnames.index( view )
            start = infile.starts[dim]

            run_modifHrd=ModifyHeaderCommand()
            run_modifHrd.inputs.in_file = temp_fn
            run_modifHrd.inputs.dinsert = True;
            run_modifHrd.inputs.opt_string = view+":start="+str(start);
            run_modifHrd.run()

        node_name="fixIrregularDimension"
        fixIrregular = ModifyHeaderCommand()
        fixIrregular.inputs.opt_string = " -sinsert time-width:spacing=\"regular__\" -sinsert xspace:spacing=\"regular__\" -sinsert yspace:spacing=\"regular__\" -sinsert zspace:spacing=\"regular__\""
        if "time" in infile.dimnames : 
            fixIrregular.inputs.opt_string += " -sinsert time:spacing=\"regular__\""
        fixIrregular.inputs.in_file = temp_fn
        if self.inputs.verbose >= 2:
            print( fixIrregular.cmdline )
        fixIrregular.run()

        fixCosine = FixCosinesCommand()
        fixCosine.inputs.in_file = fixIrregular.inputs.out_file
        fixCosine.inputs.keep_real_range=True
        fixCosine.inputs.dircos=True
        fixCosine.run()
        if self.inputs.verbose >= 2:
            print(fixCosine.cmdline)
        shutil.copy(fixCosine.inputs.out_file, self.inputs.out_file)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file

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
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        infile = volumeFromFile(self.inputs.in_file)
        #FIXME : infile = nib.load(self.inputs.in_file)
        try :
            t=infile.dimnames.index("time")
            nFrames = infile.sizes[infile.dimnames.index("time")]
        except ValueError :
            t=0
            nFrames=1

        z=infile.dimnames.index("zspace")
        y=infile.dimnames.index("yspace")
        x=infile.dimnames.index("xspace")
        rank=0.25

        if nFrames > 1 :
            dimnames=[ infile.dimnames[z], infile.dimnames[y],infile.dimnames[x] ]
            sizes=[ infile.sizes[z], infile.sizes[y],infile.sizes[x] ]
            starts=[ infile.starts[z], infile.starts[y],infile.starts[x] ]
            separations=[ infile.separations[z], infile.separations[y],infile.separations[x] ]
            outfile = volumeFromDescription(self.inputs.out_file, dimnames, sizes, starts, separations)
            first=int(floor(nFrames*rank) )
            last=nFrames
            if t == 0 :
                volume_subset=infile.data[first:last,:,:,:]
            elif t == 1:
                volume_subset=infile.data[:,first:last,:,:]
            elif t == 2:
                volume_subset=infile.data[:,:,first:last,:]
            else:
                volume_subset=infile.data[:,:,f:,irst:last]
            volume_average=np.mean(volume_subset, axis=t)
            #FIXME volume_average.to_file(self.inputs.in_)
            outfile.data=volume_average
            outfile.writeFile()
            outfile.closeVolume()
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
    default_field=["pet","json_header"] # ["pet", "t1"]
    inputnode = pe.Node(niu.IdentityInterface(fields=default_field), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["pet_header_dict","pet_header_json","pet_center","pet_volume"]), name='outputnode')

    node_name="petCenter"
    petCenter= pe.Node(interface=VolCenteringRunning(), name=node_name)
    petCenter.inputs.verbose = opts.verbose

    node_name="petVolume"
    petVolume = pe.Node(interface=pet3DVolume(), name=node_name)
    petVolume.inputs.verbose = opts.verbose

    node_name="petSettings"
    petSettings = pe.Node(interface=MincHdrInfoRunning(), name=node_name)
    petSettings.inputs.halflife = opts.halflife
    petSettings.inputs.clobber = True

    workflow.connect([(inputnode, petCenter, [('pet', 'in_file')])])

    workflow.connect([(petCenter, petSettings, [('out_file', 'in_file')])])
    workflow.connect(inputnode, 'json_header', petSettings, 'json_header')
    workflow.connect([(petCenter, petVolume, [('out_file', 'in_file')])])


    workflow.connect(petSettings, 'header', outputnode, 'pet_header_dict')
    workflow.connect(petSettings, 'out_file', outputnode, 'pet_header_json')
    workflow.connect(petCenter, 'out_file', outputnode, 'pet_center')
    workflow.connect(petVolume, 'out_file', outputnode, 'pet_volume')

    return(workflow)
