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

def nii2mnc_batch(opts, clobber=False):
    for sub in opts.args :
        for ses in opts.sessionList :
            sub_ses_dir = opts.sourceDir + os.sep + 'sub-' + sub + os.sep + '*ses-'+ses
            t1_files = find(sub_ses_dir, "*_T1w.nii*") 
            derived_files = [ f for f in find(sub_ses_dir, "*nii*") if f not in t1_files and 'anat/' in f ]
            pet_files = find(sub_ses_dir, "*_pet.nii*")
            nii_files = t1_files + derived_files + pet_files

            for f in nii_files :
                f_out_mnc = re.sub('.gz', '', re.sub( '.nii', '.mnc', f) )
                if not os.path.exists(f_out_mnc) or clobber :
                    nii2mnc = nii2mnc2Command()
                    nii2mnc.inputs.in_file = f
                    
                    #For t1 and pet files, set data type to float
                    #otherwise int for label images
                    if f in t1_files + pet_files :
                        nii2mnc.inputs.dfloat = True
                    else :
                        nii2mnc.inputs.dint = True

                    nii2mnc.inputs.out_file=f_out_mnc
                    nii2mnc.run()
                    

if __name__ == '__main__' : 
	import sys
	nii2mnc_batch(sys.argv[1])
