import src.initialization as init 
import numpy as np
import nibabel as nib
import os
import tempfile
import unittest
from src.ants import APPIANApplyTransforms, APPIANConcatenateTransforms, APPIANRegistration
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.ants import registration, segmentation
from nipype.interfaces.ants.segmentation import Atropos
from nipype.interfaces.ants import Registration, ApplyTransforms
from nipype.interfaces.utility import Rename
from nipype.interfaces.ants.registration import CompositeTransformUtil, CompositeTransformUtilInputSpec
from nipype.interfaces.ants.resampling import ApplyTransformsInputSpec
from nipype.interfaces.base import InputMultiPath

def tmp_fn() : return '{}.nii.gz'.format( tempfile.NamedTemporaryFile().name )

unit_test_dir='temp_unit_tests'
os.makedirs(unit_test_dir,exist_ok=True)

def create_temp_vol(sizes=[], center=[], r1=None, r2=None):
    if len(sizes) == 0 : sizes=[40,40,40]
    if len(center) == 0 : center = [ int(i/2) for i in sizes ]
    min_dim = np.min(sizes[0:3])
    if r1 == None : r1 = ( min_dim / 2 ) / 4
    if r2 == None : r2 = ( min_dim / 2 ) / 3

    ndim = len(sizes)

    vol = np.zeros(sizes[0:3])
    xx, yy, zz  = np.meshgrid(range(sizes[0]), range(sizes[1]), range(sizes[2]) )
    r = np.sqrt( np.power(xx-center[0],2) + np.power(yy-center[1],2) + np.power(zz-center[2],2) )
    
    gm = (r >= r1) & (r <= r2)  
    wm = r < r1
    vol[ gm ] = 1
    vol[ wm ] = 2
    
    if ndim == 4 :
        vol = vol.reshape([vol.shape[0],vol.shape[1],vol.shape[2],1]) 
        vol = np.repeat( vol, sizes[3], axis=3)    

    out_fn = tmp_fn()
    affine = np.eye(4,4)
    nib.Nifti1Image(vol, affine).to_filename(out_fn)
    print(out_fn)
    
    return out_fn

class APPIANUnitTests( unittest.TestCase ):
    def setUp(self):
        self.pet_volume_inst = init.pet3DVolume()
        self.pet_brain_mask_inst = init.petBrainMask()

    def test_pet_3d_volume_4(self):
        out_fn=tmp_fn()
        self.pet_volume_inst._pet_3D_volume(create_temp_vol(sizes=(40,40,40,5)), out_fn, verbose=False )
        self.assertTrue(os.path.exists(out_fn))

    def test_pet_3d_volume_3(self):
        out_fn=tmp_fn()
        self.pet_volume_inst._pet_3D_volume( create_temp_vol(sizes=(40,40,40)), out_fn, verbose=False )
        self.assertTrue(os.path.exists(out_fn))

    def test_pet_brain_mask(self):
        out_fn=tmp_fn()
        self.pet_brain_mask_inst._pet_brain_mask(create_temp_vol(sizes=(40,40,40)), out_fn, verbose=False)
        self.assertTrue(os.path.exists(out_fn))

class AntsUnitTests( unittest.TestCase) :
    def setUp(self) :
        self.reg = APPIANRegistration() 
        self.reg.inputs.type_of_transform='Affine'
        self.reg.inputs.fixed_image = create_temp_vol([50,50,50], [20,20,20], 10, 13  )
        self.reg.inputs.moving_image = create_temp_vol([50,50,50], [30,25,30], 13, 19  )
        self.reg.inputs.outprefix='/tmp/'
    
    def test_appian_registration(self):
        self.result = self.reg.run() 



if __name__ == '__main__':
    # begin the unittest.main()
    unittest.main()





