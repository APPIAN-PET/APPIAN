from pvc_template import *

in_file_format="MINC"
out_file_format="MINC"

class pvcOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")

class pvcInput(MINCCommandInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask = File( position=2, argstr="-mask %s", desc="Integer mask file")
    input_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    
    fwhm = traits.Float( argstr="-fwhm %f", desc="FWHM of PSF all axes") 
    max_iterations = traits.Int(argstr="-max-iterations %d", desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-tolerance %f", desc="Tolerance")
    nvoxel_to_average = traits.Int( argstr="-nvoxel-to-average %f", desc="Number of voxels to average over.")

class pvcCommand(quantificationCommand):
    input_spec =  quantInput
    output_spec = quantOutput
    _cmd='GTM'
    _suffix='GTM'

def check_options(pvcNode, opts):
    if opts.fwhm != None: pvcNode.inputs.t3max=opts.fwhm
    if opts.max_iterations != None: pvcNode.inputs.t3min=opts.max_iterations
    if opts.tolerance != None: pvcNode.inputs.nBF=opts.tolerance
    if opts.nvoxel_to_average != None : pvcNode.nvoxel_to_average
    return pvcNode
