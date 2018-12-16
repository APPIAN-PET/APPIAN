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
    t1_files = find(sourceDir, "*_T1w.nii*") 
    pet_files= find(sourceDir, "*_pet.nii*")
    nii_files = t1_files + pet_files
    ret = False

    for f in nii_files :
        f_out = re.sub( '.nii', '.mnc',  re.sub('.gz', '', f))
        if not os.path.exists(f_out) or clobber :
           #Not sure why this uncompression was put it
            #doesn't seem necessary
           #if (f.endswith("gz")):
           #     f_gunzip = re.sub('.gz','', f)
           #     with gzip.open(f, 'r') as f_in, open(f_gunzip, 'wb') as f2:
           #         shutil.copyfileobj(f_in, f2)
           #     f=f_gunzip
            nii2mnc =nii2mnc2Command()
            nii2mnc.inputs.in_file = f 
            nii2mnc.inputs.out_file=f_out
            nii2mnc.run()
            
            #shutil.remove(f_gunzip) 
            #if os.path.exists(nii2mnc.inputs.out_file):
               # with open(nii2mnc.inputs.out_file, 'rb') as f_in, gzip.open(nii2mnc.inputs.out_file+'.gz', 'wb') as f_out:
                #        shutil.copyfileobj(f_in, f_out)
                #if os.path.exists(nii2mnc.inputs.out_file+'.gz') :
                #    shutil.remove(nii2mnc.inputs.out_file)
            #else :
            #    print("Error : could not find ", nii2mnc.inputs.out_file, "to gzip it.")

        ret = True
    return ret 	

if __name__ == '__main__' : 
	import sys
	nii2mnc_batch(sys.argv[1])
