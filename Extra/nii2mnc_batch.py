import os
import h5py
from conversion import  nii2mnc2Command, nii2mnc_shCommand
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
		BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import nipype.pipeline.engine as pe
import fnmatch
import re
import gzip
import shutil


def find(src, match):
    matches = []
    for root, dirnames, filenames in os.walk(src):
        for filename in fnmatch.filter(filenames, match):
            matches.append(os.path.join(root, filename))
    return(matches)

def nii2mnc_batch(sourceDir, clobber=False):
    nii_files = find(sourceDir, "*nii*") 
    ret = False

    for f in nii_files :
        f_out = re.sub( '.nii', '.mnc',  re.sub('.gz', '', f))
        if not os.path.exists(f_out) or clobber :
            if (f.endswith("gz")):
                f_gunzip = re.sub('.gz','', f)
                with gzip.open(f, 'r') as f_in, open(f_gunzip, 'wb') as f2:
                    shutil.copyfileobj(f_in, f2)
                f=f_gunzip
            nii2mnc =nii2mnc2Command()
            nii2mnc.inputs.in_file = f 
            nii2mnc.inputs.out_file=f_out
            nii2mnc.run()
        ret = True
    return ret 	

if __name__ == '__main__' : 
	import sys
	nii2mnc_batch(sys.argv[1])
