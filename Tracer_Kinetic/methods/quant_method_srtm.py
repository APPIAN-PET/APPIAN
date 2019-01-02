from quantification_template import *

global quant_format
global reference
global voxelwise
in_file_format="ECAT"
out_file_format="ECAT"
reference=True
voxelwise=True

class quantOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class quantInput(MINCCommandInputSpec):
    in_file= File(exists=True, position=-3, argstr="%s", desc="PET file")
    reference = File(exists=True,  position=-2, argstr="%s", desc="Reference file")
    out_file = File(argstr="%s", position=-1, desc="image to operate on")
    #out_file_t3map = File(argstr="-err=%s", position=0, desc="Theta3 image.")
    t3max = traits.Float(argstr="-max=%f", position=1, desc="Maximum value for theta3.")
    t3min = traits.Float(argstr="-min=%f", position=2, desc="Minimum value for theta3.")
    nBF = traits.Int(argstr="-nr=%d", position=3, desc="Number of basis functions.")


class quantCommand(quantificationCommand):
    input_spec =  quantInput
    output_spec = quantOutput
    _cmd = "imgbfbp"  
    _suffix = "_srtm" 

def check_options(tkaNode, opts):
    if opts.tka_t3max != None: tkaNode.inputs.t3max=opts.tka_t3max
    if opts.tka_t3min != None: tkaNode.inputs.t3min=opts.tka_t3min
    if opts.tka_nBF != None: tkaNode.inputs.nBF=opts.tka_nBF
    return tkaNode
