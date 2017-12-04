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

def unique_file(files, attributes):
	
	if len(files) == 1: 
		return(files[0])
	
	files = [ f for f in files if attributes[0] in f ]

	if attributes == [] or len(files) == 0: return []
	else: unique_file(files, attributes[1:])
	return( files[0] ) 


def gen_args(opts, session_ids, task_ids, acq, rec, subjects):
    args=[]
    for sub in subjects:
        for ses in session_ids:
            for task in task_ids:
				sub_arg='sub-'+sub
				ses_arg='ses-'+ses
				task_arg=rec_arg=acq_arg=""
				
				pet_fn=civet_fn=""
				if not acq == None: acq_arg='acq-'+acq
				if not rec == None: rec_arg='rec-'+rec
				pet_string=opts.sourceDir+os.sep+ sub_arg + os.sep+ '_'+ ses_arg + os.sep+ 'pet/*'+ 'ses-'+ses+'*'+'task-'+ task  +'*_pet.mnc' 
				pet_list=glob(pet_string)
				if pet_list != []:
					pet_fn = unique_file(pet_list,[sub, ses, task, acq, rec] )
				civet_list=glob(opts.sourceDir+os.sep+ sub_arg + os.sep + '*/anat/*_T1w.mnc' )
				if civet_list != []:
					civet_fn = unique_file(civet_list,[sub, ses, task, acq, rec] )
				if os.path.exists(pet_fn) and os.path.exists(civet_fn):
					d={'task':task, 'ses':ses, 'sid':sub}
					args.append(d)
				else:
					if not os.path.exists(pet_fn) :
						print "Could not find PET for ", sub, ses, task, pet_fn
					if not os.path.exists(civet_fn) :
						print "Could not find CIVET for ", sub, ses, task, civet_fn
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
		
		if self.inputs.run:
			run_modifHrd.run()

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
        nFrames = infile.sizes[infile.dimnames.index("time")]
        first=int(ceil(float(nFrames*rank)/100))
        last=int(nFrames)-int(ceil(float(nFrames*4*rank)/100))
        count=last-first

        #frames=[]
        #for ii in np.arange(first,last+1,1):
        #    frame = tmpDir+os.sep+'frame'+str(ii)+'.mnc'

        run_mincreshape=ReshapeCommand()
        run_mincreshape.inputs.in_file = self.inputs.in_file
        run_mincreshape.inputs.out_file = self.inputs.out_file 
        run_mincreshape.inputs.dimrange = 'time='+str(first)+','+str(count)
        if self.inputs.verbose:
            print run_mincreshape.cmdline
        if self.inputs.run:
            run_mincreshape.run()
        
        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs



def get_workflow(name, infosource, datasink, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    default_field=["pet"] # ["pet", "t1"]
    inputnode = pe.Node(niu.IdentityInterface(fields=default_field), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["pet_header","pet_json","pet_center","pet_volume"]), name='outputnode')

    #get_steps = pe.Node(interface=get_stepCommand(), name="get_steps")
    #workflow.connect(inputnode, 't1', get_steps, 'in_file')
    
    #node_name="petResample"
    #petResample= pe.Node(interface=ResampleCommand(), name=node_name)
    #petResample.inputs.interpolation = 'trilinear'
	#petResample.inputs.tfm_input_sampling = True
    #workflow.connect(inputnode, 'pet', petResample, 'in_file')
    #workflow.connect(get_steps, 'step', petResample, 'step')
	

    node_name="petCenter"
    petCenter= pe.Node(interface=VolCenteringRunning(), name=node_name)
    petCenter.inputs.verbose = opts.verbose
    petCenter.inputs.run = opts.prun    
    rPetCenter=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    node_name="petExcludeFr"
    petExFr = pe.Node(interface=PETexcludeFrRunning(), name=node_name)
    petExFr.inputs.verbose = opts.verbose   
    petExFr.inputs.run = opts.prun
    rPetExFr=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)


    node_name="petVolume"
    petVolume = pe.Node(interface=minc.Average(), name=node_name)
    #MIC: petVolume = pe.Node(interface=minc.AverageCommand(), name=node_name)
    petVolume.inputs.avgdim = 'time'
    petVolume.inputs.width_weighted = True
    petVolume.inputs.clobber = True
    petVolume.inputs.verbose = opts.verbose 
    rPetVolume=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)


    node_name="petBlur"
    #MIC: petBlur = pe.Node(interface=minc.SmoothCommand(), name=node_name)
    petBlur = pe.Node(interface=minc.Blur(), name=node_name)
    petBlur.inputs.fwhm = 3
    petBlur.inputs.clobber = True
    #MIC: petBlur.inputs.verbose = opts.verbose 

    node_name="petSettings"
    petSettings = pe.Node(interface=MincHdrInfoRunning(), name=node_name)
    petSettings.inputs.verbose = opts.verbose
    petSettings.inputs.clobber = True
    petSettings.inputs.run = opts.prun
    rPetSettings=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    # node_name="petCenterSettings"
    # petCenterSettings = pe.Node(interface=MincHdrInfoRunning(), name=node_name)
    # petCenterSettings.inputs.verbose = opts.verbose
    # petCenterSettings.inputs.clobber = True
    # petCenterSettings.inputs.run = opts.prun
    # rPetSettings=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)


    # workflow.connect([(inputnode, petSettings, [('pet', 'in_file')])])
    workflow.connect([(inputnode, petCenter, [('pet', 'in_file')])])

    workflow.connect([(petCenter, rPetCenter, [('out_file', 'in_file')])])
    workflow.connect([#(infosource, rPetCenter, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetCenter, [('sid', 'sid')]),
                      (infosource, rPetCenter, [('cid', 'cid')])
                    ])
    #workflow.connect(rPetCenter, 'out_file', datasink, 'coregistered')

    # workflow.connect([(petCenter, petCenterSettings, [('out_file', 'in_file')])])
    workflow.connect([(petCenter, petSettings, [('out_file', 'in_file')])])

    workflow.connect([(petCenter, petExFr, [('out_file', 'in_file')])])
    workflow.connect([(petExFr, rPetExFr, [('out_file', 'in_file')])])
    workflow.connect([#(infosource, rPetExFr, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetExFr, [('sid', 'sid')]),
                      (infosource, rPetExFr, [('cid', 'cid')])
                    ])
    #workflow.connect(rPetExFr, 'out_file', datasink, petExFr.name)


    #MIC: workflow.connect([(rPetExFr, petVolume, [('out_file', 'in_file')])])
    workflow.connect([(rPetExFr, petVolume, [('out_file', 'input_files')])])

    #MIC: workflow.connect([(petVolume, petBlur, [('out_file', 'in_file')])])
    workflow.connect([(petVolume, petBlur, [('output_file', 'input_file')])])
    #MIC: workflow.connect([(petBlur, rPetVolume, [('out_file', 'in_file')])])
    workflow.connect([(petBlur, rPetVolume, [('output_file', 'in_file')])])
   
   
    workflow.connect([#(infosource, rPetVolume, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetVolume, [('sid', 'sid')]),
                      (infosource, rPetVolume, [('cid', 'cid')])
                    ])
    #workflow.connect(petBlur, 'out_file', datasink, petVolume.name)


    workflow.connect(petSettings, 'header', outputnode, 'pet_header')
    workflow.connect(petSettings, 'out_file', outputnode, 'pet_json')
    workflow.connect(rPetCenter, 'out_file', outputnode, 'pet_center')
    workflow.connect(rPetVolume, 'out_file', outputnode, 'pet_volume')

    
    return(workflow)
