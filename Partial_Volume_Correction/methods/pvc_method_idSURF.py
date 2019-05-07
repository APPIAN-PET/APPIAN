from pvc_template import *
import numpy as np
file_format="MINC"
separate_labels=False

class pvcOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class pvcInput(MINCCommandInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask_file = File( position=2, argstr="-mask %s", desc="Integer mask file")
    in_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    
    fwhm = traits.Float( argstr="-fwhm %f", desc="FWHM of PSF all axes") 
    max_iterations = traits.Int(argstr="-max-iterations %d",usedefault=True,default_value=10, desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-tolerance %f", desc="Tolerance", usedefault=True, default_value=0.001)
    nvoxel_to_average = traits.Int( argstr="-nvoxel-to-average %f", default_value=64, usedefault=True, desc="Number of voxels to average over.")

class pvcCommand(pvcCommand):
    input_spec =  pvcInput
    output_spec = pvcOutput
    _cmd='idSURF'
    _suffix='_idSURF'

def check_options(pvcNode, opts):
    if opts.scanner_fwhm != None: pvcNode.inputs.fwhm=np.mean(opts.scanner_fwhm) #FIXME : rewrite idsurf to take fwhm vector
    if opts.max_iterations != None: pvcNode.inputs.max_iterations=opts.max_iterations
    if opts.tolerance != None: pvcNode.inputs.tolerance=opts.tolerance
    if opts.nvoxel_to_average != None : pvcNode.inputs.nvoxel_to_average=opts.nvoxel_to_average
    return pvcNode
