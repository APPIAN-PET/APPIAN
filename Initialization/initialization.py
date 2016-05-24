import os
import numpy as np
import tempfile
import shutil
import nipype.interfaces.minc as minc

import minc as pyezminc
from os.path import basename
from math import *

from pyminc.volumes.factory import *
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.utils.minc_filemanip import update_minchd_json

from nipype.interfaces.minc.info import InfoCommand
from nipype.interfaces.minc.modifHeader import ModifyHeaderCommand
from nipype.interfaces.minc.reshape import ReshapeCommand
from nipype.interfaces.minc.concat import ConcatCommand




class MincHdrInfoOutput(TraitedSpec):
    out_file = File(desc="Output file")

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
   
    # def _parse_inputs(self, skip=None):
    #     if skip is None:
    #         skip = []
    #     if not isdefined(self.inputs.out_file):
    #         fname, ext = os.path.splitext(self.inputs.in_file)
    #         self.inputs.out_file = fname + _suffix

    #     return super(MincHdrInfoRunning, self)._parse_inputs(skip=skip)


    def _run_interface(self, runtime):

        if not isdefined(self.inputs.out_file):
            fname, ext = os.path.splitext(self.inputs.in_file)
            self.inputs.out_file = fname + self._suffix

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
            for subkey in hd[key].keys():
                data_in = hd[key][subkey]
                var = str(key)
                attr = str(subkey)
                update_minchd_json(self.inputs.out_file, data_in, var, attr)

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
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
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
	
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



