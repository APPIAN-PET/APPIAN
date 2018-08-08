from pvc_template import *

file_format="MINC"
separate_labels=False

class pvcOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class pvcInput(MINCCommandInputSpec):
    out_file = File(position=4, argstr="-o %s",desc="image to operate on")
    mask_file = File( position=3, argstr="-mask %s", desc="Integer mask file")
    in_file = File(exists=True, position=2, argstr="-pet %s", desc="PET file")
    fwhm = traits.Float( argstr="-fwhm %f", position=1, desc="FWHM of PSF all axes") 

class pvcCommand(pvcCommand):
    input_spec =  pvcInput
    output_spec = pvcOutput
    _cmd='gtm'
    _suffix='GTM'

def check_options(pvcNode, opts):

    #Because of the way the GTM code is implemented, it only takes a single 
    #scalar value to represent an isotropic FWHM for the scanner PSF
    fwhm = opts.scanner_fwhm 
    if type(fwhm)	== list :
        fwhm = sum(fwhm) / len(fwhm)

    if opts.scanner_fwhm != None: pvcNode.inputs.fwhm=fwhm
    return pvcNode
