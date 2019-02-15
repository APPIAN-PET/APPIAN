from quantification_template import *
from pyminc.volumes.factory import volumeLikeFile, volumeFromFile
import numpy as np
import json
from scipy.integrate import simps
### Required for a quantification node:
in_file_format="MINC"
### Required for a quantification node:
out_file_format="MINC"
### Required for a quantification node:
reference=True
### Required for a quantification node:
voxelwise=True


### <check_options> is required for a quantification node
def check_options(tkaNode, opts) :
    return tkaNode

class quantOutput(TraitedSpec):
    out_file = File(argstr="%s", position=-1, desc="Output SUV image.")

class quantInput(TraitedSpec):
    in_file = File(exists=True,mandatory=True, desc="PET file")
    reference = File(exists=True,mandatory=True,desc="Mask file")
    header = traits.File(exists=True, mandatory=True, desc="Input file ")
    end_time=traits.Float(argstr="%f", desc="End time")
    start_time=traits.Float(argstr="%f",default_value=0, usedefault=True,  desc="Start time (min).")
    out_file = File(desc="Output SUV image")

class quantCommand(BaseInterface):
    input_spec =  quantInput
    output_spec = quantOutput

    _suffix = "_suvr" 
    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file) : self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        header = json.load(open(self.inputs.header, "r") )
        pet = volumeFromFile(self.inputs.in_file)
        reference = volumeFromFile(self.inputs.reference)
        out = volumeLikeFile(self.inputs.reference, self.inputs.out_file )
        ndim = len(pet.data.shape)
        
        vol = pet.data
        if ndim > 3 :

            dims = pet.getDimensionNames()
            i = dims.index('time')

            if not isdefined(self.inputs.start_time) : 
                start_time=0
            else :
                start_time=self.inputs.start_time

            if not isdefined(self.inputs.end_time) : 
                end_time=header['Time']['FrameTimes']['Values'][-1][1]
            else :
                end_time=self.inputs.end_time

            try : 
                #time_frames = [ float(s) for s,e in  header['Time']["FrameTimes"]["Values"] ]
                time_frames = [ float(s) for s,e in  header['Time']["FrameTimes"]["Values"] if s >= start_time and e <= end_time ]
            except ValueError :
                time_frames = [1.]
            vol = simps( pet.data, time_frames, axis=i)
        
        idx = reference.data > 0
        ref = np.mean(vol[idx])
        print "SUVR Reference = ", ref
        vol = vol / ref
        out.data=vol
        out.writeFile()
        out.closeVolume()


        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(quantCommand, self)._parse_inputs(skip=skip)
