from quantification_template import *
import json 

in_file_format="NIFTI"
out_file_format="DFT"
reference=True
voxelwise=False


class quantOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image")

class quantInput( MINCCommandInputSpec):
    out_file = File(argstr="%s", position=-1, desc="image to operate on")
    in_file = File(exists=True, mandatory=True, position=-5, argstr="%s", desc="PET file")
    reference = File(exists=True, mandatory=True, position=-4, argstr="%s", desc="Reference file")
    BPnd = traits.Bool(argstr="-BPnd", position=1, usedefault=True, default_value=True)
    header = traits.File(exists=True, mandatory=True, desc="Input file ")
    sif = File(desc="Sif file for Nifti PET input")
    C = traits.Bool(argstr="-C", position=2, usedefault=True, default_value=True)
    start_time=traits.Float(argstr="%f",default_value=0, usedefault=True,position=-3, desc="Start time for regression in mtga.")
    k2=  traits.Float(argstr="-k2=%f", desc="With reference region input it may be necessary to specify also the population average for regerence region k2")
    end_time=traits.Float(argstr="%s", position=-2, desc="By default line is fit to the end of data. Use this option to enter the fit end time.")

class quantCommand(quantificationCommand):
    input_spec = quantInput
    output_spec = quantOutput
    _cmd = "logan" #input_spec.pvc_method 
    _suffix = "_lp-roi" 

    def _parse_inputs(self, skip=None):
        header = json.load(open(self.inputs.header, "r") )
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        
        if not isdefined(self.inputs.start_time) : 
            self.inputs.start_time=header['Time']['FrameTimes']['Values'][0][0]
            if header['Time']['FrameTimes']['Units'][0] == 's' : self.inputs.start_time /= 60.
            elif header['Time']['FrameTimes']['Units'][0] == 'm' : pass
            elif header['Time']['FrameTimes']['Units'][0] == 'h' : self.inputs.start_time *= 60.
            else :
                print("Error : unrecognized time units in ", self.inputs.header)
                exit(1)
        if not isdefined(self.inputs.end_time) : 
            self.inputs.end_time=header['Time']['FrameTimes']['Values'][-1][1]
            if header['Time']['FrameTimes']['Units'][1] == 's' : self.inputs.end_time /= 60.
            elif header['Time']['FrameTimes']['Units'][1] == 'm' :  pass
            elif header['Time']['FrameTimes']['Units'][0] == 'h' : self.inputs.end_time *= 60.
            else :
                print("Error : unrecognized time units in ", self.inputs.header)
                exit(1)       

        return super(quantCommand, self)._parse_inputs(skip=skip)

class QuantCommandWrapper(QuantificationCommandWrapper):
    input_spec =  quantInput
    output_spec = quantOutput
    _quantCommand=quantCommand
def check_options(tkaNode, opts):
    #Define node for logan plot analysis 
    if opts.tka_k2 != None: tkaNode.inputs.k2=opts.tka_k2
    if opts.tka_end_time != None: tkaNode.inputs.end_time=opts.tka_end_time
    if opts.tka_start_time != None: tkaNode.inputs.start_time=opts.tka_start_time

    return tkaNode
