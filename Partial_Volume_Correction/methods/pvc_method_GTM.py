from pvc_template import *

file_format="MINC"
separate_labels=False

class pvcOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class pvcInput(MINCCommandInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask_file = File( position=2, argstr="-mask %s", desc="Integer mask file")
    in_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    fwhm = traits.Float( argstr="-fwhm %f", desc="FWHM of PSF all axes") 

class pvcCommand(pvcCommand):
    input_spec =  pvcInput
    output_spec = pvcOutput
    _cmd='gtm'
    _suffix='GTM'

def check_options(pvcNode, opts):
    if opts.scanner_fwhm != None: pvcNode.inputs.fwhm=opts.scanner_fwhm
    return pvcNode
