import os
import numpy as np
import tempfile
import shutil
import json
import nipype.interfaces.minc as minc

import minc as pyezminc
from os.path import basename
from math import *

from pyminc.volumes.factory import *

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from Extra.minc_filemanip import update_minchd_json
from nipype.interfaces.utility import Rename
from nipype.interfaces.minc import Resample as ResampleCommand
from Extra.info import  InfoCommand
from Extra.modifHeader import ModifyHeaderCommand
from Extra.reshape import  ReshapeCommand
from glob import glob
from Extra.modifHeader import FixHeaderCommand


def unique_file(files, attributes):
    
    if len(files) == 1: 
        return(files[0])
   
    out_files = [ f for a in attributes for f in files if a in f ]

    if attributes == [] or len(out_files) == 0 : return []

    return( out_files[0] ) 


def gen_args(opts, session_ids, task_ids, acq, rec, subjects):
    args=[]
    for sub in subjects:
        for ses in session_ids:
            for task in task_ids:
                sub_arg='sub-'+sub
                ses_arg='ses-'+ses
                task_arg=rec_arg=acq_arg=""

                pet_fn=mri_fn=""
                if  acq == '': acq_arg='acq-'+acq
                if  rec == '': rec_arg='rec-'+rec
                pet_string=opts.sourceDir+os.sep+ sub_arg + os.sep+ '*'+ ses_arg + os.sep+ 'pet/*_pet.mnc' 
                pet_list=glob(pet_string)
                arg_list = ['sub-'+sub, 'ses-'+ses]
                if not task == '': arg_list += ['task-'+task]
                if not acq == '': arg_list += ['acq-'+acq]
                if not rec == '': arg_list += ['rec-'+rec]
                if pet_list != []:
                    pet_fn = unique_file(pet_list, arg_list )

                mri_list=glob(opts.sourceDir+os.sep+ sub_arg + os.sep + '*/anat/*_T1w.mnc' )
                if mri_list != []:
                    mri_fn = unique_file(mri_list, arg_list )

                if os.path.exists(pet_fn) and os.path.exists(mri_fn):
                    d={'task':task, 'ses':ses, 'sid':sub}
                    args.append(d)
                else:
                    if not os.path.exists(pet_fn) :
                        print "Could not find PET for ", sub, ses, task, pet_fn
                    if not os.path.exists(mri_fn) :
                        print "Could not find T1 for ", sub, ses, task, mri_fn
    print(args)
    return args


class SplitArgsOutput(TraitedSpec):
    cid = traits.Str(mandatory=True, desc="Condition ID")
    sid = traits.Str(mandatory=True, desc="Subject ID") 
    task = traits.Str(desc="Task ID")
    ses = traits.Str(desc="Session ID")
    RoiSuffix = traits.Str(desc="Suffix for subject ROI")

class SplitArgsInput(BaseInterfaceInputSpec):
    task = traits.Str(desc="Task ID")
    ses = traits.Str(desc="Session ID")
    sid = traits.Str(desc="Subject ID")
    cid = traits.Str(desc="Condition ID")
    #study_prefix = traits.Str(mandatory=True, desc="Study Prefix")
    RoiSuffix = traits.Str(desc="Suffix for subject ROI")
    args = traits.Dict(mandatory=True, desc="Overwrite output file")

class SplitArgsRunning(BaseInterface):
    input_spec = SplitArgsInput
    output_spec = SplitArgsOutput

    def _run_interface(self, runtime):
        self.inputs.cid=self.inputs.args['ses']+'_'+self.inputs.args['task']
        self.inputs.task=self.inputs.args['task']
        self.inputs.ses=self.inputs.args['ses']
        self.inputs.sid=self.inputs.args['sid']
        if isdefined(self.inputs.RoiSuffix):
            self.inputs.RoiSuffix=self.inputs.RoiSuffix
        return runtime
    
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["cid"] = self.inputs.cid
        outputs["sid"] = self.inputs.sid
        outputs["ses"] = self.inputs.ses
        outputs["task"] = self.inputs.task
        if isdefined(self.inputs.RoiSuffix):
            outputs["RoiSuffix"]= self.inputs.RoiSuffix
        return outputs





class MincHdrInfoOutput(TraitedSpec):
    out_file = File(desc="Output file")
    header = traits.Dict(desc="Dictionary")


class MincHdrInfoInput(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="Native dynamic PET image")
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
        try:
            os.remove(self.inputs.out_file)
        except OSError:
            pass

        class InfoOptions:
            def __init__(self, command, variable, attribute, type_):
                self.command = command
                self.variable = variable
                self.attribute = attribute
                self.type_ = type_

        options = [ InfoOptions('-dimnames','time','dimnames','string'),
                InfoOptions('-varvalue time','time','frames-time','integer'),
                InfoOptions('-varvalue time-width','time','frames-length','integer') ]

        for opt in options:
            run_mincinfo=InfoCommand()
            run_mincinfo.inputs.in_file = self.inputs.in_file
            run_mincinfo.inputs.out_file = self.inputs.out_file
            run_mincinfo.inputs.opt_string = opt.command
            run_mincinfo.inputs.json_var = opt.variable
            run_mincinfo.inputs.json_attr = opt.attribute
            run_mincinfo.inputs.json_type = opt.type_
            run_mincinfo.inputs.error = 'unknown'

            if self.inputs.verbose:
                print run_mincinfo.cmdline
            if self.inputs.run:
                run_mincinfo.run()

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
                update_minchd_json(self.inputs.out_file, data_in, var, attr)


        fp=open(self.inputs.out_file)
        header = json.load(fp)
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
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class VolCenteringRunning(BaseInterface):
    input_spec = VolCenteringInput
    output_spec = VolCenteringOutput
    _suffix = "_center"


    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            fname = os.path.splitext(os.path.basename(self.inputs.in_file))[0]
            dname = dname = os.getcwd()
            self.inputs.out_file = dname + os.sep + fname + self._suffix + '.mnc'


        shutil.copy(self.inputs.in_file, self.inputs.out_file)
        infile = volumeFromFile(self.inputs.in_file)
        for view in ['xspace','yspace','zspace']:
            start = -1*infile.separations[infile.dimnames.index(view)]*infile.sizes[infile.dimnames.index(view)]/2

            run_modifHrd=ModifyHeaderCommand()
            run_modifHrd.inputs.in_file = self.inputs.out_file;
            run_modifHrd.inputs.dinsert = True;
            run_modifHrd.inputs.opt_string = view+":start="+str(start);
            run_modifHrd.run()
            
        node_name="fixIrregularDimension"
        fixIrregular = ModifyHeaderCommand()
        fixIrregular.inputs.sinsert = True;
        fixIrregular.inputs.opt_string = "time:spacing=\"regular__\" -sinsert time-width:spacing=\"regular__\" -sinsert xspace:spacing=\"regular__\" -sinsert yspace:spacing=\"regular__\" -sinsert zspace:spacing=\"regular__\"  "
        fixIrregular.inputs.in_file = run_modifHrd.inputs.out_file
        fixIrregular.run()


        pettot1_4d_header_fixed = pe.Node(interface=FixHeaderCommand(), name="pettot1_4d_header_fixed")
        pettot1_4d_header_fixed.inputs.time_only=True
        pettot1_4d_header_fixed.inputs.in_file = fixIrregular.inputs.out_file
        pettot1_4d_header_fixed.inputs.header = self.inputs.header


        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file

        return outputs

class get_stepOutput(TraitedSpec):
    step =traits.Str(desc="Step size (X, Y, Z)")

class get_stepInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Step size (X, Y, Z)")
    step = traits.Str( desc="Image after centering")


class get_stepCommand(BaseInterface):
    input_spec = get_stepInput
    output_spec = get_stepOutput

    def _run_interface(self, runtime):
        img = volumeFromFile(self.inputs.in_file)
        zi=img.dimnames.index('zspace')
        yi=img.dimnames.index('yspace')
        xi=img.dimnames.index('xspace')
        zstep = img.separations[zi]
        ystep = img.separations[yi]
        xstep = img.separations[xi]
        self.inputs.step = str(xstep) +' ' + str(ystep) +' '+str(zstep)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["step"] = self.inputs.step
        return outputs



class PETexcludeFrOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class PETexcludeFrInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Image")
    out_file = File(argstr="%s", desc="Image after centering")

    run = traits.Bool(argstr="-run", usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETexcludeFrRunning(BaseInterface):
    input_spec = PETexcludeFrInput
    output_spec = PETexcludeFrOutput
    _suffix = "_reshaped"


    def _run_interface(self, runtime):
        #tmpDir = tempfile.mkdtemp()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)

        infile = volumeFromFile(self.inputs.in_file)      
        rank=10
        #If there is no "time" dimension (i.e., in 3D file), then set nFrames to 1
        try: 
            nFrames = infile.sizes[infile.dimnames.index("time")]
            first=int(ceil(float(nFrames*rank)/100))
            last=int(nFrames)-int(ceil(float(nFrames*4*rank)/100))
            count=last-first
            run_mincreshape=ReshapeCommand()
            run_mincreshape.inputs.dimrange = 'time='+str(first)+','+str(count)
            run_mincreshape.inputs.in_file = self.inputs.in_file
            run_mincreshape.inputs.out_file = self.inputs.out_file 
            if self.inputs.verbose:
                print run_mincreshape.cmdline
            if self.inputs.run:
                run_mincreshape.run()
        except ValueError : 
            self.inputs.out_file = self.inputs.in_file 

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

"""
.. module:: initialization 
    :platform: Unix
    :synopsis: Workflow to initialize PET images
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""

def get_workflow(name, infosource, datasink, opts):
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
    default_field=["pet"] # ["pet", "t1"]
    inputnode = pe.Node(niu.IdentityInterface(fields=default_field), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["pet_header_dict","pet_header_json","pet_center","pet_volume"]), name='outputnode')

    header_init = pe.Node(interface=MincHdrInfoRunning(), name="header_init")
    workflow.connect(inputnode, 'pet',  header_init, 'in_file')
    
    node_name="petCenter"
    petCenter= pe.Node(interface=VolCenteringRunning(), name=node_name)
    petCenter.inputs.verbose = opts.verbose



    node_name="petExcludeFr"
    petExFr = pe.Node(interface=PETexcludeFrRunning(), name=node_name)
    petExFr.inputs.verbose = opts.verbose   
    #petExFr.inputs.run = opts.prun
    rPetExFr=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    node_name="petVolume"
    petVolume = pe.Node(interface=minc.Average(), name=node_name)
    petVolume.inputs.avgdim = 'time'
    petVolume.inputs.width_weighted = False
    petVolume.inputs.clobber = True
    rPetVolume=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".mnc"),name="r"+node_name)

    node_name="petSettings"
    petSettings = pe.Node(interface=MincHdrInfoRunning(), name=node_name)
    petSettings.inputs.clobber = True
    #petSettings.inputs.run = opts.prun
    rPetSettings=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)



    workflow.connect([(inputnode, petCenter, [('pet', 'in_file')])])
    workflow.connect(header_init, 'out_file', petCenter, 'header')

    workflow.connect([(petCenter, petSettings, [('out_file', 'in_file')])])

    workflow.connect([(petCenter, petExFr, [('out_file', 'in_file')])])
    workflow.connect([(petExFr, rPetExFr, [('out_file', 'in_file')])])
    workflow.connect([(infosource, rPetExFr, [('sid', 'sid')]),
        (infosource, rPetExFr, [('cid', 'cid')])
        ])

    workflow.connect([(rPetExFr, petVolume, [('out_file', 'input_files')])])

    workflow.connect([(petVolume, rPetVolume, [('output_file', 'in_file')])])


    workflow.connect([(infosource, rPetVolume, [('sid', 'sid')]),
        (infosource, rPetVolume, [('cid', 'cid')])
        ])

    workflow.connect(petSettings, 'header', outputnode, 'pet_header_dict')
    workflow.connect(petSettings, 'out_file', outputnode, 'pet_header_json')
    workflow.connect(petCenter, 'out_file', outputnode, 'pet_center')
    workflow.connect(rPetVolume, 'out_file', outputnode, 'pet_volume')


    return(workflow)
