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
    header = traits.File(exists=True, mandatory=True, desc="Input file ")
    in_file= File(exists=True, position=-4, argstr="%s", desc="PET file")
    reference = File(exists=True,  position=-5, argstr="%s", desc="Reference file")
    sif = File(desc="Sif file for Nifti PET input")
    start_time=traits.Float( argstr="%s",default_value=0, usedefault=True, position=-3, desc="Start time for regression in mtga.")
    end_time=traits.Float(argstr="%f", position=-2, desc="By default line is fit to the end of data. Use this option to enter the fit end time.")
    Ca=traits.Float(argstr="-Ca=%f", desc="Concentration of native substrate in arterial plasma (mM).")
    LC=traits.Float(argstr="-LC=%f", desc="Lumped constant in MR calculation; default is 1.0")
    #density=traits.Float(argstr="-density %f", desc="Tissue density in MR calculation; default is 1.0 g/ml")
    #thr=traits.Float(argstr="-thr=%f", desc="Pixels with AUC less than (threshold/100 x max AUC) are set to zero. Default is 0%")
    #Max=traits.Float(argstr="-max=%f", default=10000, use_default=True,desc="Upper limit for Vt or DVR values; by default max is set pixel-wise to 10 times the AUC ratio.")
    #Min=traits.Float(argstr="-min %f", desc="Lower limit for Vt or DVR values, 0 by default")
    #Filter=traits.Bool(argstr="-filter",  desc="Remove parametric pixel values that over 4x higher than their closest neighbours.")
    v=traits.Str(argstr="-v %s", desc="Y-axis intercepts time -1 are written as an image to specified file.")
    n=traits.Str(argstr="-n %s", desc="Numbers of selected plot data points are written as an image.")



class quantCommand(quantificationCommand):
    input_spec = quantInput
    output_spec = quantOutput
    _cmd = "patlak" #input_spec.pvc_method 
    _suffix = "_pp-roi" 

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
    #Define node for patlak plot analysis 
    if opts.tka_k2 != None: tkaNode.inputs.k2=opts.tka_k2
    if opts.tka_end_time != None: tkaNode.inputs.end_time=opts.tka_end_time
    if opts.tka_start_time != None: tkaNode.inputs.start_time=opts.tka_start_time

    return tkaNode
