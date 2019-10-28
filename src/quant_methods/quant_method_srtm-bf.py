from quantification_template import *

global quant_format
global reference
global voxelwise
in_file_format="NIFTI"
out_file_format="NIFTI"
reference=True
voxelwise=True

class quantOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class quantInput(CommandLineInputSpec):
    in_file= File(exists=True, position=-3, argstr="%s", desc="PET file")
    reference = File(exists=True,  position=-2, argstr="%s", desc="Reference file")
    out_file = File(argstr="%s", position=-1, desc="image to operate on") 
    sif = File(desc="Sif file for Nifti PET input")
    R1=traits.File(argstr="-R1 %s", desc="Programs computes also an R1 image.")
    k2=traits.File(argstr="-k2 %s", desc="Programs computes also a k2 image." )
    Min=traits.Float(argstr="-min %f", desc="<value (1/min)>  Set minimum value for theta3; it must be >= k2min/(1+BPmax)+lambda.  Default is 0.06 min-1. Lambda for F-18 is 0.0063 and for C-11 0.034.")
    Max=traits.Float(argstr="-max %f", desc="<value (1/min)> Set maximum value for theta3; it must be <= k2max+lambda. Default is 0.60 min-1.")
    nr=traits.Int(argstr="%d", desc="Set number of basis functions; default is 500, minimum 100.")
    bf=traits.File(argstr="-bf %s", desc="Basis function curves are written in specified file.")
    wss=traits.File(argstr="-wss %s", desc="Weighted sum-of-squares are written in specified image file.")
    err=traits.Float(argstr="-err %s",desc="Pixels with their theta3 in its min or max value are written  in the specified imagefile with values 1 and 2, respectively, others with value 0.")
    thr=traits.Float(argstr="-thr %f", desc="Pixels with AUC less than (threshold/100 x ref AUC) are set to zero;  default is 0%")
    DVR = traits.Bool(argstr="-DVR", desc="Instead of BP, program saves the DVR (=BP+1) values." )
    noneg = traits.Bool(argstr="-noneg", desc="Pixels with negative BP values are set to zero.")
    end= traits.Float(argstr="-eng %f", desc="<Fit end time (min)>  Use data from 0 to end time; by default, model is fitted to all frames.")


class quantCommand(quantificationCommand):
    input_spec =  quantInput
    output_spec = quantOutput
    _cmd = "imgbfbp"  
    _suffix = "_srtm-bf" 


class QuantCommandWrapper(srcCommandWrapper):
    input_spec =  quantInput
    output_spec = quantOutput
    _quantCommand=quantCommand

def check_options(tkaNode, opts):
    if opts.quant_R1 != None: tkaNode.inputs.R1=opts.quant_R1
    if opts.quant_k2 != None: tkaNode.inputs.k2=opts.quant_k2 
    if opts.quant_t3min != None: tkaNode.inputs.Min=opts.quant_t3min
    if opts.quant_t3max != None: tkaNode.inputs.Max=opts.quant_t4max
    if opts.quant_nBF != None: tkaNode.inputs.nr=opts.quant_nBF 
    if opts.quant_bf != None: tkaNode.inputs.bf=opts.quant_bf
    if opts.quant_wss != None: tkaNode.inputs.wss=opts.quant_wss 
    if opts.quant_err != None: tkaNode.inputs.err=opts.quant_err
    if opts.quant_thr != None: tkaNode.inputs.thr=opts.quant_thr
    if opts.quant_DVR != None: tkaNode.inputs.DVR=opts.quant_DVR
    if opts.quant_noneg != None: tkaNode.inputs.noneg=opts.quant_noneg
    if opts.quant_end != None: tkaNode.inputs.end=opts.quant_end_time

    return tkaNode
