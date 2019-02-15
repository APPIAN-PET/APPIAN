from pvc_template import *

file_format="MINC"
separate_labels=False

class pvcOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class pvcInput(MINCCommandInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask_file = File( position=2, argstr="-mask %s", desc="Integer mask file")
    in_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    x_fwhm = traits.Float( argstr="-x %f", desc="FWHM of PSF x axis") 
    y_fwhm = traits.Float( argstr="-y %f", desc="FWHM of PSF y axis") 
    z_fwhm = traits.Float( argstr="-z %f", desc="FWHM of PSF z axis") 


class pvcCommand(pvcCommand):
    input_spec =  pvcInput
    output_spec = pvcOutput
    _cmd='gtm'
    _suffix='_GTM'

def check_options(pvcNode, opts):
    if opts.scanner_fwhm != None: pvcNode.inputs.z_fwhm=opts.scanner_fwhm[0]
    if opts.scanner_fwhm != None: pvcNode.inputs.y_fwhm=opts.scanner_fwhm[1]
    if opts.scanner_fwhm != None: pvcNode.inputs.x_fwhm=opts.scanner_fwhm[2]
    return pvcNode
