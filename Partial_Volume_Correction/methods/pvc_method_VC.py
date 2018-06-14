from petpvc import petpvc4DCommand
from pvc_template import *
import nibabel as nib

file_format="NIFTI"
separate_labels=True
split_frames=True



class pvcCommand(petpvc4DCommand):
    
    _suffix='VC'


def check_options(pvcNode, opts):
    if opts.scanner_fwhm != None: pvcNode.inputs.z_fwhm=opts.scanner_fwhm
    if opts.scanner_fwhm != None: pvcNode.inputs.y_fwhm=opts.scanner_fwhm
    if opts.scanner_fwhm != None: pvcNode.inputs.x_fwhm=opts.scanner_fwhm
    return pvcNode
