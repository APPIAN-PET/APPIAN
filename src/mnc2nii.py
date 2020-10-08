import os
import re
import nibabel as nib
import numpy as np
from glob import glob
from sys import argv

dirname=argv[1]

print(dirname)
### COLLECT ALL MNCs
all_fls = []
for dirs, things, fls in os.walk(dirname):
    if len(fls) > 0:
        for fl in fls:
            all_fls.append(os.path.join(dirs,fl))

all_mncs = [x for x in all_fls if '.mnc' in x]

print('%s .mnc and .mnc.gz files found'%(len(all_mncs)))

### SEARCH TO SEE IF NIFTI VERSIONS ALREADY EXIST
already_done = []
for mnc in all_mncs:
    print(mnc)
    flnm = re.sub('.mnc.gz', '', re.sub('.mnc', '', mnc))
    print(flnm)
    ni = glob('%s.ni*'%flnm)
    if len(ni) > 0:
    	already_done.append(mnc)

print('%s mncs already have a nifti version. Skipping these files...'%(len(already_done)))
[all_mncs.remove(x) for x in already_done]

print('the following files will be converted:')
[print(x) for x in all_mncs]

### TRANSFORM FILES
for mnc in all_mncs:
    flnm = re.sub('.mnc', '', re.sub('.mnc.gz', '', mnc))
    if mnc[-1] == 'z':
        new_nm = '%s.nii.gz'%flnm
    else:
        new_nm = '%s.nii.gz'%flnm
    print(new_nm)
    img = nib.load(mnc)
    data = img.get_data()
    affine =img.affine
    if len(data.shape) == 4 :
        out = np.zeros( [ data.shape[1], data.shape[2], data.shape[3], data.shape[0] ]  )
        for t in range(data.shape[0]) :
            out[:,:,:,t] = data[t,:,:,:]
    else : out = data

    nifti = nib.Nifti1Image(out, affine)
    nifti.to_filename(new_nm)
    print('converted %s to %s'%(mnc,new_nm))
    #if ans:
    #    os.remove(mnc)

