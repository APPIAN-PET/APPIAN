import src.initialization as init 
import numpy as np
import nibabel as nib
import os
import tempfile
import unittest

def tmp_fn() : return '{}.nii.gz'.format( tempfile.NamedTemporaryFile().name )

unit_test_dir='temp_unit_tests'
os.makedirs(unit_test_dir,exist_ok=True)


def generate_nifti(ndim=3):
    fn=tmp_fn()
    xdim=ydim=zdim=25
    tdim=3
    aff=np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])

    dims=[xdim,ydim,zdim]
    if ndim == 4 :
        dims.append(tdim)

    vol=np.random.randint(0,10,dims)
    img=nib.Nifti1Image(vol,aff)
    img.to_filename(fn)
    return fn


class APPIANUnitTests( unittest.TestCase ):
    def setUp(self):
        self.pet_volume_inst = init.pet3DVolume()
        self.pet_brain_mask_inst = init.petBrainMask()

    def test_pet_3d_volume_4(self):
        out_fn=tmp_fn()
        self.pet_volume_inst._pet_3D_volume( generate_nifti(ndim=4) , out_fn, verbose=False )
        self.assertTrue(os.path.exists(out_fn))

    def test_pet_3d_volume_3(self):
        out_fn=tmp_fn()
        self.pet_volume_inst._pet_3D_volume( generate_nifti(ndim=3) , out_fn, verbose=False )
        self.assertTrue(os.path.exists(out_fn))

    def test_pet_brain_mask(self):
        out_fn=tmp_fn()
        self.pet_brain_mask_inst._pet_brain_mask(generate_nifti(ndim=3), out_fn, verbose=False)
        self.assertTrue(os.path.exists(out_fn))


if __name__ == '__main__':
    # begin the unittest.main()
    unittest.main()





