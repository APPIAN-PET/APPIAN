from pyminc.volumes.factory import volumeLikeFile, volumeFromFile
import numpy as np
from quantification_template import *
from scipy.integrate import simps
import json

in_file_format="NIFTI"
out_file_format="NIFTI"
reference=True
voxelwise=True


class quantOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image")

class quantInput( CommandLineInputSpec):
    out_file = File(argstr="%s",  desc="Parametric image")
    end_time=traits.Float(argstr="%f", desc="End time")
    header = traits.File(exists=True, mandatory=True, desc="Input file ")
    start_time=traits.Float(argstr="%f",default_value=0, usedefault=True,  desc="Start time (min).")
    in_file = File(argstr="%s", mandatory=True, desc="image to operate on")
    reference = File(exists=True,mandatory=True,desc="Mask file")
   
class quantCommand(BaseInterface):
    input_spec = quantInput
    output_spec = quantOutput
    _suffix = "_suv"

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]


    def _run_interface(self, runtime):
        header = json.load(open(self.inputs.header, "r") )
        if not isdefined(self.inputs.out_file) : 
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        
        try :
            dose = float(header["RadioChem"]["InjectedRadioactivity"])
        except ValueError :
            print("Error: Could not find injected dose in subject's header. Make sure subject has a .json header in BIDS format with [RadioChem][InjectedRadioactivity]")
            exit(1)

        try :
            weight   = float(header["Info"]["BodyWeight"])
        except ValueError :
            print("Error: Could not find subject's body weight in header. Make sure subject has a .json header in BIDS format with [Info][BodyWeight]")
            exit(1)
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
            
            #time_frames = time_indices = []
            #for i in range(vol.shape[i]) :
            #    s=header['Time']["FrameTimes"]["Values"][i][0]
            #    e=header['Time']["FrameTimes"]["Values"][i][1]
            #    print(i)
            #    if s >= start_time and e <= end_time :
            #        time_indices.append(i)
            #        time_frames.append(float(e) - float(s)  )
            #print(time_indices) 
            #print(time_frames)
            time_frames = [ float(s) for s,e in  header['Time']["FrameTimes"]["Values"] ]
            vol = simps( pet.data, time_frames, axis=i)
        vol = vol / ( dose / weight)  
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
        return super(suvCommand, self)._parse_inputs(skip=skip)


def check_options(tkaNode, opts):
    #Define node for suv analysis 
    if opts.tka_end != None: tkaNode.inputs.end=opts.tka_end
    if opts.tka_start_time != None: tkaNode.inputs.start_time=opts.tka_start_time

    return tkaNode


