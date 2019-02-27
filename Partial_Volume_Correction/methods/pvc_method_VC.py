from petpvc import petpvc4DCommand
from pvc_template import *

file_format="NIFTI"
separate_labels=True

class pvcCommand(petpvc4DCommand):
    _suffix='VC'


def check_options(pvcNode, opts):
    if opts.scanner_fwhm != None: pvcNode.inputs.z_fwhm=opts.scanner_fwhm[0]
    if opts.scanner_fwhm != None: pvcNode.inputs.y_fwhm=opts.scanner_fwhm[1]
    if opts.scanner_fwhm != None: pvcNode.inputs.x_fwhm=opts.scanner_fwhm[2]
    if opts.max_iterations != None: pvcNode.inputs.iterations=opts.max_iterations
    if opts.k != None: pvcNode.inputs.iterations=opts.k
    return pvcNode
