import os
import h5py
from conversion import  nii2mncCommand, nii2mnc_shCommand
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
		BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import nipype.pipeline.engine as pe
import fnmatch


def find(src, match):
	matches = []
	for root, dirnames, filenames in os.walk(src):
		for filename in fnmatch.filter(filenames, match):
			matches.append(os.path.join(root, filename))
	return(matches)

def nii2mnc_batch(sourceDir, clobber=False):
	nii_files = find(sourceDir, "*nii") 
	for f in nii_files :
		f_out = os.path.splitext(f)[0] + '.mnc'
		if not os.path.exists(f_out) or clobber :
			print('Converting', f)
			nii2mnc =nii2mnc_shCommand()
			nii2mnc.inputs.in_file = f 
			nii2mnc.inputs.out_file=f_out
			nii2mnc.run()
	return 0 	

if __name__ == '__main__' : 
	import sys
	nii2mnc_batch(sys.argv[1])
