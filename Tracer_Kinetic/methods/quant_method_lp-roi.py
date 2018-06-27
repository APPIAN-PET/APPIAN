from quantification_template import *

in_file_format="ECAT"
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
    C = traits.Bool(argstr="-C", position=2, usedefault=True, default_value=True)
    start_time=traits.Float(argstr="%s", mandatory=True, position=-3, desc="Start time for regression in mtga.")
    k2=  traits.Float(argstr="-k2=%f", desc="With reference region input it may be necessary to specify also the population average for regerence region k2")
    end_time=traits.Float(argstr="%s", mandatory=True, position=-2, desc="By default line is fit to the end of data. Use this option to enter the fit end time.")

class quantCommand(quantificationCommand):
    input_spec = quantInput
    output_spec = quantOutput
    _cmd = "logan" #input_spec.pvc_method 
    _suffix = "_lp-roi" 


def check_options(tkaNode, opts):
    #Define node for logan plot analysis 
    if opts.tka_k2 != None: tkaNode.inputs.k2=opts.tka_k2
    if opts.tka_end_time != None: tkaNode.inputs.end_time=opts.tka_end_time
    if opts.tka_start_time != None: tkaNode.inputs.start_time=opts.tka_start_time

    return tkaNode
