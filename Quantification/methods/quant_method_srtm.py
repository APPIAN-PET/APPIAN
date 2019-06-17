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


class quantInput(MINCCommandInputSpec):
    in_file= File(exists=True, position=-3, argstr="%s", desc="PET file")
    reference = File(exists=True,  position=-2, argstr="%s", desc="Reference file")
    out_file = File(argstr="%s", position=-1, desc="image to operate on")

    srtm2 = traits.Bool(argstr="-srtm2", desc="STRM2 method is applied; in brief, traditional SRTM method is used first to calculate median k2 from all pixels where BPnd>0; then SRTM is run another time with fixed k2" )
    R1=traits.File(argstr="-R1 %s", desc="Programs computes also an R1 image.")
    sif = File(desc="Sif file for Nifti PET input")
    k2=traits.File(argstr="-k2 %s", desc="Programs computes also a k2 image." )
    k2s=traits.File(argstr="-k2s %s", desc="Programs computes also a k2 image." )
    theta3=traits.File(argstr="-theta3 %s", desc="Programs computes also a k2 image." )
    rp=traits.File(argstr="-rp %s", desc="Program writes regression parameters in the specified image file." )
    dual=traits.File(argstr="-dual %s", desc="Program writes number of i in set p in NNLS dual solution vector in the specified image file" )
    thr=traits.Float(argstr="-thr %f", desc="Pixels with AUC less than (threshold/100 x ref AUC) are set to zero;  default is 0%")
    DVR = traits.Bool(argstr="-DVR", desc="Instead of BP, program saves the DVR (=BP+1) values." )
    end= traits.Float(argstr="-end %f", desc="<Fit end time (min)>  Use data from 0 to end time; by default, model is fitted to all frames.")


class quantCommand(quantificationCommand):
    input_spec =  quantInput
    output_spec = quantOutput
    _cmd = "imgsrtm"  
    _suffix = "_srtm" 

class QuantCommandWrapper(QuantificationCommandWrapper):
    input_spec =  quantInput
    output_spec = quantOutput
    _quantCommand=quantCommand

def check_options(tkaNode, opts):
    if opts.tka_R1 != None: tkaNode.inputs.R1=opts.tka_R1
    if opts.tka_k2 != None: tkaNode.inputs.k2=opts.tka_k2 
    if opts.tka_k2s != None: tkaNode.inputs.k2s=opts.tka_k2s
    if opts.tka_rp != None: tkaNode.inputs.rp=opts.tka_rp

    if opts.tka_dual != None: tkaNode.inputs.err=opts.tka_dual
    if opts.tka_thr != None: tkaNode.inputs.thr=opts.tka_thr
    if opts.tka_DVR != None: tkaNode.inputs.DVR=opts.tka_DVR
    if opts.tka_srtm2 != None: tkaNode.inputs.srtm2=opts.tka_srtm2
    if opts.tka_end_time != None: tkaNode.inputs.end=opts.tka_end_time 

    return tkaNode
