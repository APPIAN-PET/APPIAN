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
from nipype.utils.minc_filemanip import update_minchd_json
from nipype.interfaces.utility import Rename

from nipype.interfaces.minc.info import InfoCommand
from nipype.interfaces.minc.modifHeader import ModifyHeaderCommand
from nipype.interfaces.minc.reshape import ReshapeCommand
from nipype.interfaces.minc.concat import ConcatCommand




class MincHdrInfoOutput(TraitedSpec):
    out_file = File(desc="Output file")
    header = traits.Dict(desc="Dictionary")


class MincHdrInfoInput(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="Native dynamic PET image")
    out_file = File(desc="Output file")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class MincHdrInfoRunning(BaseInterface):
    input_spec = MincHdrInfoInput
    output_spec = MincHdrInfoOutput
    _suffix = ".info"
    _params={}
    # def _parse_inputs(self, skip=None):
    #     if skip is None:
    #         skip = []
    #     if not isdefined(self.inputs.out_file):
    #         fname, ext = os.path.splitext(self.inputs.in_file)
    #         self.inputs.out_file = fname + _suffix

    #     return super(MincHdrInfoRunning, self)._parse_inputs(skip=skip)


    def _run_interface(self, runtime):
        

        if not isdefined(self.inputs.out_file):
            fname = os.path.splitext(os.path.basename(self.inputs.in_file))[0]
            dname = os.getcwd() #os.path.dirname(self.inputs.nativeT1)
            self.inputs.out_file = dname+ os.sep+fname + self._suffix
        # if os.path.exists(self.inputs.out_file):
        #     os.remove(self.inputs.out_file)
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

    run = traits.Bool(argstr="-run", usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class VolCenteringRunning(BaseInterface):
    input_spec = VolCenteringInput
    output_spec = VolCenteringOutput
    _suffix = "_center"


    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            fname = os.path.splitext(os.path.basename(self.inputs.in_file))[0]
            dname = dname = os.getcwd()
            # self.inputs.out_file = dname + os.sep + fname + self._suffix
            self.inputs.out_file = dname + os.sep + fname + self._suffix + '.mnc'

	
        shutil.copy(self.inputs.in_file, self.inputs.out_file)
        infile = volumeFromFile(self.inputs.in_file)
        for view in ['xspace','yspace','zspace']:
            start = -1*infile.separations[infile.dimnames.index(view)]*infile.sizes[infile.dimnames.index(view)]/2

            run_modifHrd=ModifyHeaderCommand()
            run_modifHrd.inputs.in_file = self.inputs.out_file;
            run_modifHrd.inputs.dinsert = True;
            run_modifHrd.inputs.opt_string = view+":start="+str(start);
            if self.inputs.verbose:
                print run_modifHrd.cmdline
            if self.inputs.run:
                run_modifHrd.run()
	
        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file

        return outputs



class PETexcludeFrOutput(TraitedSpec):
    out_file = File(desc="Image after centering")

class PETexcludeFrInput(BaseInterfaceInputSpec):
    in_file = File(position=0, argstr="%s", mandatory=True, desc="Image")
    out_file = File(argstr="%s", desc="Image after centering")

    run = traits.Bool(argstr="-run", usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETexcludeFrRunning(BaseInterface):
    input_spec = PETexcludeFrInput
    output_spec = PETexcludeFrOutput
    _suffix = "_reshaped"


    def _run_interface(self, runtime):
        tmpDir = tempfile.mkdtemp()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
    
        infile = volumeFromFile(self.inputs.in_file)      
        rank=10
        nFrames = infile.sizes[infile.dimnames.index("time")]
        first=int(ceil(float(nFrames*rank)/100))
        last=int(nFrames)-int(ceil(float(nFrames*4*rank)/100))

        frames=[]
        for ii in np.arange(first,last+1,1):
            frame = tmpDir+os.sep+'frame'+str(ii)+'.mnc'

            run_mincreshape=ReshapeCommand()
            run_mincreshape.inputs.in_file = self.inputs.in_file
            run_mincreshape.inputs.out_file = frame
            run_mincreshape.inputs.dimrange = 'time='+str(ii)+',1'
            if self.inputs.verbose:
                print run_mincreshape.cmdline
            if self.inputs.run:
                run_mincreshape.run()
            
            frames.append(frame)
        
        run_concat=ConcatCommand()
        run_concat.inputs.in_file = ' '.join(frames)
        run_concat.inputs.out_file = self.inputs.out_file
        run_concat.inputs.dimension = 'time'
        if self.inputs.verbose:
            print run_concat.cmdline
        if self.inputs.run:
            run_concat.run()

        shutil.rmtree(tmpDir)
        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        
        return outputs



def get_workflow(name, infosource, datasink, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet"]), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["pet_header","pet_json","pet_center","pet_volume"]), name='outputnode')


    node_name="petCenter"
    petCenter= pe.Node(interface=VolCenteringRunning(), name=node_name)
    petCenter.inputs.verbose = opts.verbose
    petCenter.inputs.run = opts.prun    
    rPetCenter=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    node_name="petExcludeFr"
    petExFr = pe.Node(interface=PETexcludeFrRunning(), name=node_name)
    petExFr.inputs.verbose = opts.verbose   
    petExFr.inputs.run = opts.prun
    rPetExFr=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    node_name="petVolume"
    petVolume = pe.Node(interface=minc.AverageCommand(), name=node_name)
    petVolume.inputs.avgdim = 'time'
    petVolume.inputs.width_weighted = True
    petVolume.inputs.clobber = True
    petVolume.inputs.verbose = opts.verbose 
    rPetVolume=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    node_name="petSettings"
    petSettings = pe.Node(interface=MincHdrInfoRunning(), name=node_name)
    petSettings.inputs.verbose = opts.verbose
    petSettings.inputs.clobber = True
    petSettings.inputs.run = opts.prun
    rPetSettings=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    # node_name="petCenterSettings"
    # petCenterSettings = pe.Node(interface=MincHdrInfoRunning(), name=node_name)
    # petCenterSettings.inputs.verbose = opts.verbose
    # petCenterSettings.inputs.clobber = True
    # petCenterSettings.inputs.run = opts.prun
    # rPetSettings=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)




    # workflow.connect([(inputnode, petSettings, [('pet', 'in_file')])])
    workflow.connect([(inputnode, petCenter, [('pet', 'in_file')])])

    workflow.connect([(petCenter, rPetCenter, [('out_file', 'in_file')])])
    workflow.connect([(infosource, rPetCenter, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetCenter, [('sid', 'sid')]),
                      (infosource, rPetCenter, [('cid', 'cid')])
                    ])
    workflow.connect(rPetCenter, 'out_file', datasink, petCenter.name)

    # workflow.connect([(petCenter, petCenterSettings, [('out_file', 'in_file')])])
    workflow.connect([(petCenter, petSettings, [('out_file', 'in_file')])])

    workflow.connect([(petCenter, petExFr, [('out_file', 'in_file')])])
    workflow.connect([(petExFr, rPetExFr, [('out_file', 'in_file')])])
    workflow.connect([(infosource, rPetExFr, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetExFr, [('sid', 'sid')]),
                      (infosource, rPetExFr, [('cid', 'cid')])
                    ])
    workflow.connect(rPetExFr, 'out_file', datasink, petExFr.name)

    workflow.connect([(petExFr, petVolume, [('out_file', 'in_file')])])
    workflow.connect([(petVolume, rPetVolume, [('out_file', 'in_file')])])
    workflow.connect([(infosource, rPetVolume, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetVolume, [('sid', 'sid')]),
                      (infosource, rPetVolume, [('cid', 'cid')])
                    ])
    workflow.connect(rPetVolume, 'out_file', datasink, petVolume.name)


    workflow.connect(petSettings, 'header', outputnode, 'pet_header')
    workflow.connect(petSettings, 'out_file', outputnode, 'pet_json')
    workflow.connect(rPetCenter, 'out_file', outputnode, 'pet_center')
    workflow.connect(rPetVolume, 'out_file', outputnode, 'pet_volume')

    
    return(workflow)
