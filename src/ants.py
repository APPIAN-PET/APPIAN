from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.ants import registration, segmentation
from nipype.interfaces.utility import Rename
from nipype.interfaces.ants.registration import CompositeTransformUtil, CompositeTransformUtilInputSpec
from nipype.interfaces.ants.resampling import ApplyTransformsInputSpec
from nipype.interfaces.base import InputMultiPath
from src.utils import splitext, cmd
from scipy.io import loadmat
from scipy.ndimage import center_of_mass
from sklearn.cluster import KMeans
import numpy as np
import nibabel as nib
import nipype.pipeline.engine as pe
import SimpleITK as sitk
import os
import re
import ants


class AtroposInputs(BaseInterfaceInputSpec):
    input_image = traits.File(mandatory=True, exits=True, desc="Input Image")
    mask_image = traits.File(mandatory=True, exits=True, desc="Input Image")
    prior_weighting = traits.Float(usedefault=True, default_value=0.5) 
    prior_images =  traits.List()
    classified_image = traits.File(desc="Output Image")

class AtroposOutputs(TraitedSpec):
    classified_image = traits.File(desc="Output Image")

class Atropos(BaseInterface):
    input_spec = AtroposInputs
    output_spec= AtroposOutputs

    def _run_interface(self, runtime):
        self._set_outputs()

    
        print(self.inputs.prior_images)
        print('input image', self.inputs.input_image)
        print('mask image',self.inputs.mask_image)
        print('classified image', self.inputs.classified_image)
        print()
        
        img  = nib.load(self.inputs.input_image)
        intensity_vol = img.get_fdata()

        centroids=[0]
        for fn in self.inputs.prior_images :
            mask_vol = nib.load(fn).get_fdata()
            centroids.append( np.mean( intensity_vol[ mask_vol > 0.5 ]))

        cls = KMeans(4, np.array(centroids).reshape(-1,1) ).fit_predict(intensity_vol.reshape(-1,1)).reshape(intensity_vol.shape)

        mask_vol = nib.load(self.inputs.mask_image)
        cls[ mask_vol == 0 ] = 0

        nib.Nifti1Image(cls, img.affine).to_filename(self.inputs.classified_image)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["classified_image"] = self.inputs.classified_image
        return outputs

    def _set_outputs(self):
        base_filename = os.path.basename( splitext(self.inputs.input_image)[0] )
        self.inputs.classified_image = os.getcwd() +'/'+ base_filename +'_atropos-seg.nii.gz'


    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        return super(Atropos, self)._parse_inputs(skip=skip)

########################

class APPIANCompositeTransformUtilInputSpec(CompositeTransformUtilInputSpec) :
    in_file_1 = traits.File()
    in_file_2 = traits.File()
    in_file = InputMultiPath(File(exists=True), argstr='%s...', position=3, desc='Input transform file(s)')

class APPIANCompositeTransformUtil(CompositeTransformUtil):
    input_spec = APPIANCompositeTransformUtilInputSpec

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        self.inputs.in_file = [self.inputs.in_file_1, self.inputs.in_file_2]
        self.inputs.out_file = os.getcwd()+os.sep+"composite.h5"
        return super(APPIANCompositeTransformUtil, self)._parse_inputs(skip=skip)
   
class APPIANApplyTransformsInputSpec(BaseInterfaceInputSpec) :
    transform_1 = traits.File()
    transform_2 = traits.File()
    transform_3 = traits.File()
    invert_1 = traits.Bool(default_value=False, usedefault=True)
    invert_2 = traits.Bool(default_value=False, usedefault=True)
    invert_3 = traits.Bool(default_value=False, usedefault=True)
    reference_image=traits.File(mandatory=True, exists=True)
    input_image=traits.File(mandatory=True, exists=True)
    output_image = traits.File()
    output_image_inverse = traits.File()
    target_space=traits.Str(default_value="undefined", usedefault=True)
    interpolation = traits.Str(usedefault=True, default_value='linear')

class APPIANApplyTransformsOutputSpec(TraitedSpec) :
    output_image = traits.File(exists=True)

class APPIANApplyTransforms(BaseInterface):
    input_spec = APPIANApplyTransformsInputSpec
    output_spec = APPIANApplyTransformsOutputSpec

    def _run_interface(self, runtime):
        transforms = [] 
        invert_transform_flags = []
        if isdefined(self.inputs.transform_1) :
            transforms.append(self.inputs.transform_1)
            invert_transform_flags.append(self.inputs.invert_1)

        if isdefined(self.inputs.transform_2) :
            transforms.append(self.inputs.transform_2)
            invert_transform_flags.append(self.inputs.invert_2)
        
        if isdefined(self.inputs.transform_3) :
            transforms.append(self.inputs.transform_3)
            invert_transform_flags.append(self.inputs.invert_3)
       
        flipped_invert_transform_flags = [ not flag for flag in invert_transform_flags ]

        #output files
        split =splitext(os.path.basename( self.inputs.input_image))
        self.inputs.output_image =os.getcwd() + os.sep + split[0] + split[1] 
        source_space='rsl'
        target_space='rsl'
        print('Input image', self.inputs.input_image)
        print('Reference image', self.inputs.reference_image)
        if '_space-' in self.inputs.input_image :
            get_space = lambda filename : [ re.sub('space-','',s)  for s in filename.split('_') if 'space-' in s ][0]
            source_space = get_space(self.inputs.input_image)
            target_space = get_space(self.inputs.reference_image)
            print('\tsource space',source_space)
            print('\ttarget space',target_space)
        print('Interpolation:', self.inputs.interpolation)
        self.inputs.output_image = re.sub('_space-[A-z]*_',f'_space-{target_space}_', self.inputs.output_image)
        self.inputs.output_image_inverse = re.sub('_space-[A-z]*_',f'_space-{source_space}_', self.inputs.output_image)
        
        # apply forward transform
        vol = ants.apply_transforms(  
                                    fixed=self.inputs.reference_image,
                                    moving=self.inputs.input_image,
                                    transformlist=transforms, 
                                    interpolator=self.inputs.interpolation,
                                    whichtoinvert=invert_transform_flags)
        nib.Nifti1Image(vol, nib.load(self.inputs.reference_image).affine ).to_filename(self.inputs.output_image)
        #cmdline = "antsApplyTransforms --float -v 1 -e 3 -d 3 -n "+  + " -i "+self.inputs.input_image+" "+ transform_string +" -r "+self.inputs.reference_image+" -o "+self.inputs.output_image
        
        # apply inverse transform
        vol = ants.apply_transforms(  fixed=self.inputs.input_image,
                                moving=self.inputs.reference_image,
                                transformlist=transforms, 
                                interpolator=self.inputs.interpolation,
                                whichtoinvert=flipped_invert_transform_flags)

        nib.Nifti1Image(vol, nib.load(self.inputs.input_image).affine ).to_filename(self.inputs.output_image)

        #cmdline = "antsApplyTransforms --float -v 1 -e 3 -d 3 -n "+ self.inputs.interpolation + " -r "+self.inputs.input_image+" "+ flipped_transform_string +" -i "+self.inputs.reference_image+" -o "+self.inputs.output_image_inverse
        #cmd(cmdline)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_image"] =  self.inputs.output_image
        outputs["inverse_output_image"] =  self.inputs.output_image_inverse

        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        return super(APPIANApplyTransforms, self)._parse_inputs(skip=skip)


class APPIANConcatenateTransformsInputSpec(BaseInterfaceInputSpec) :
    transform_1 = traits.File(mandatory=True, exists=True) 
    transform_2 = traits.File(mandatory=True, exists=True)
    #reference_image = traits.File()
    out_file = traits.File(desc="Composite transorfmation matrix")

class APPIANConcatenateTransformsOutputSpec(TraitedSpec):
    out_file = traits.File(desc="Composite transorfmation matrix")

class APPIANConcatenateTransforms(BaseInterface):
    input_spec = APPIANConcatenateTransformsInputSpec
    output_spec= APPIANConcatenateTransformsOutputSpec
    
    def _run_interface(self, runtime):
        #Get extension for input transformation files
        ext_1=splitext(self.inputs.transform_1)[1]
        ext_2=splitext(self.inputs.transform_2)[1]

        if  ext_1 in ['.mat','.txt'] and ext_2 in ['.mat','.txt']:
            self.inputs.out_file=os.getcwd()+os.sep+'composite_affine.mat'
        elif ext_1 == '.h5' or ext_2 == '.h5':
            self.inputs.out_file=os.getcwd()+os.sep+'composite_warp.h5'
        cmd("CompositeTransformUtil --assemble " + ' '.join([self.inputs.out_file, self.inputs.transform_1, self.inputs.transform_2]) )
        
        return runtime
        
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

class APPIANRegistrationInputs(BaseInterfaceInputSpec):
    fixed_image = traits.File(mandatory=True, exits=True, desc="Fixed Image")
    moving_image = traits.File(mandatory=True, exits=True, desc="Moving Image")

    type_of_transform = traits.Str(usedefault=True, default_value='SyN')
    initial_transform = traits.File()
    outprefix = traits.Str()

    fixed_image_mask = traits.File(desc='fixed mask')
    moving_image_mask = traits.File( desc='moving mask')

    grad_step = traits.Float(usedefault=True, default_value=0.2)
    flow_sigma = traits.Float(usedefault=True, default_value=3)
    total_sigma = traits.Float(usedefault=True, default_value=9)
    
    aff_metric = traits.Str(usedefault=True, default_value='mattes')
    aff_sampling = traits.Int(usedefault=True, default_value=32)
    aff_random_sampling_rate =traits.Float(usedefault=True, default_value=0.2)

    syn_metric = traits.Str(usedefault=True, default_value='mattes')
    syn_sampling = traits.Int(usedefault=True, default_value=32) 
    
    reg_iterations = traits.List()
    aff_iterations = traits.List()
    aff_shrink_factors = traits.List()
    aff_smoothing_sigmas = traits.List()



    write_composite_transform  = traits.Bool(usedefault=True, default_value=True)

    warped_image = traits.File(desc="Warped image")
    inverse_warped_image = traits.File(desc="Inverse warped image")
    composite_transform = traits.File(desc="Composite transorfmation matrix")
    inverse_composite_transform = traits.File(desc="Inverse composite transorfmation matrix")
    
    moving_image_space = traits.Str(desc="Name of coordinate space for moving image", usedefault=True, default_value="source")
    fixed_image_space = traits.Str(desc="Name of coordinate space for fixed image", usedefault=True, default_value="target")
    
    rotation_error = traits.List( desc="Rotation Error")
    translation_error = traits.List(desc="Translation Error"  )
    out_matrix = traits.File(desc="Composite transorfmation matrix")
    out_matrix_inverse = traits.File(desc="Composite transorfmation matrix")

class APPIANRegistrationOutputs(TraitedSpec):
    warped_image = traits.File(desc="Warped image")
    inverse_warped_image = traits.File(desc="Inverse warped image")
    composite_transform = traits.File(desc="Composite transorfmation matrix")
    out_matrix = traits.File(desc="Composite transorfmation matrix")
    out_matrix_inverse = traits.File(desc="Composite transorfmation matrix")
    inverse_composite_transform = traits.File(desc="Inverse composite transorfmation matrix")

class APPIANRegistration(BaseInterface):
    input_spec = APPIANRegistrationInputs
    output_spec= APPIANRegistrationOutputs


    def _run_interface(self, runtime):
        self._set_outputs()

        if not isdefined(self.inputs.reg_iterations) : self.inputs.reg_iterations = [40,20,1]
        if not isdefined(self.inputs.aff_iterations) : self.inputs.aff_iterations = [2100,1200,1200,10]
        if not isdefined(self.inputs.aff_shrink_factors) : self.inputs.aff_shrink_factors = [6,4,2,1]
        if not isdefined(self.inputs.aff_smoothing_sigmas) : self.inputs.aff_smoothing_sigmas = [3,2,1,0]
        if not isdefined(self.inputs.initial_transform): initial_transform = None
        else : initial_transform = self.inputs.initial_transform

        if isdefined(self.inputs.fixed_image_mask) :
            mask = self.inputs.fixed_image_mask
        elif isdefined(self.inputs.fixed_image_mask) and isdefined(self.inputs.moving_image_mask) :
            mask = [ self.inputs.fixed_image_mask, self.inputs.moving_image_mask ]
        else :
            mask = None

        if not isdefined(self.inputs.outprefix) :
            self.inputs.outprefix = os.getcwd() +'./'+ os.path.basename(splitext(self.inputs.moving_image)[0])+'_'+self.inputs.type_of_transform

        fixed_image_ants = ants.image_read(self.inputs.fixed_image)
        moving_image_ants =ants.image_read(self.inputs.moving_image)
        if mask != None :
            mask_ants = ants.image_read(mask)
        else :
            mask_ants = None
        print('type of transform', self.inputs.type_of_transform)
        reg = ants.registration( fixed_image_ants ,
                            moving_image_ants,
                            type_of_transform = self.inputs.type_of_transform,
                            mask = mask_ants,
                            initial_transform=initial_transform,
                            grad_step = self.inputs.grad_step,
                            flow_sigma = self.inputs.flow_sigma, 
                            total_sigma = self.inputs.total_sigma,
                            aff_metric = self.inputs.aff_metric,
                            aff_sampling = self.inputs.aff_sampling,
                            aff_random_sampling_rate = self.inputs.aff_random_sampling_rate,
                            syn_metric = self.inputs.syn_metric,
                            syn_sampling = self.inputs.syn_sampling,
                            reg_iterations = self.inputs.reg_iterations,
                            aff_iterations = self.inputs.aff_iterations,
                            aff_shrink_factors = tuple(self.inputs.aff_shrink_factors),
                            aff_smoothing_sigmas = self.inputs.aff_smoothing_sigmas,
                            write_composite_transform  = self.inputs.write_composite_transform
                            )
       
        fixed_img = nib.load(self.inputs.fixed_image)
        moving_img = nib.load(self.inputs.moving_image)
        nib.Nifti1Image(reg['warpedmovout'].numpy(), moving_img.affine).to_filename(self.inputs.warped_image) 

        nib.Nifti1Image(reg['warpedfixout'].numpy(), fixed_img.affine).to_filename(self.inputs.inverse_warped_image)
        assert os.path.exists(self.inputs.warped_image), 'Error: file does not exist ' + self.input.warped_image
        assert os.path.exists(self.inputs.inverse_warped_image), 'Error: file does not exist ' + self.input.inverse_warped_image

        #linear_transforms = [ 'Translation', 'Rigid', 'Similarity', 'Affine' ]
        #if True in [ transform in self.inputs.type_of_transform  for transform in linear_transforms ]:
            #Convert linear transforms from .mat to .txt. antsRegistration produces .mat file based on output
            #prefix, but this format seems to be harder to work with / lead to downstream errors
            #If linear transform, then have to apply transformations to input image
            #self.apply_linear_transforms()

        #if isdefined( self.inputs.rotation_error) or isdefined( self.inputs.translation_error ) : 
            #if self.inputs.rotation_error != [0,0,0] and self.inputs.translation_error != [0,0,0] : 
                #print('Warning: Applying misalignment')
                #print("\tRotation:",self.inputs.rotation_error)
                #print("\tTranslation:",self.inputs.translation_error)
                #exit(1)
                #self.apply_misalignment()
            

        return runtime

    def apply_misalignment(self) :
        com = center_of_mass( nib.load(self.inputs.fixed_image).get_data() )

        img = nib.load(self.inputs.fixed_image)
        com_world = [img.affine[0,3]+com[0] * img.affine[0,2],
                    img.affine[1,3]+com[1] * img.affine[1,1],
                    img.affine[2,3]+com[2] * img.affine[2,0]
                    ]

        tfm = sitk.VersorRigid3DTransform()
        rotations_radians = list(np.pi * np.array(self.inputs.rotation_error)/180.)
        tfm.SetParameters(rotations_radians + self.inputs.translation_error)
        tfm.SetFixedParameters(com_world)
        print('Center of Mass :', com_world)
        print(tfm.GetParameters())
        print(tfm.GetFixedParameters())
        misalign_matrix=os.getcwd()+os.sep+'misalignment_rot_x-{}_y-{}_z-{}_trans_x-{}_y-{}_z-{}.tfm'.format(*self.inputs.rotation_error,*self.inputs.translation_error)
        sitk.WriteTransform(tfm, misalign_matrix)

        print('Warning: misaligning PET to MRI alignment using file', misalign_matrix)
        
        cmdline = "antsApplyTransforms -e 3 -d 3  -n Linear -i "+self.inputs.moving_image+" -t "+ misalign_matrix+" "+self.inputs.out_matrix +" -r "+self.inputs.fixed_image+" -o Linear["+self.inputs.out_matrix+",0]"
        print(cmdline)
        cmd( cmdline  )

        cmdline = "antsApplyTransforms -e 3 -d 3  -n Linear -i "+self.inputs.moving_image+" -t "+ misalign_matrix+" "+self.inputs.out_matrix +" -r "+self.inputs.fixed_image+" -o Linear["+self.inputs.out_matrix_inverse+",1]"
        print(cmdline)
        cmd( cmdline  )
        
        cmdline = "antsApplyTransforms -e 3 -d 3 -n Linear  -i "+self.inputs.moving_image+" -t "+self.inputs.out_matrix +" -r "+self.inputs.fixed_image+" -o "+self.inputs.warped_image
        print(cmdline)
        cmd( cmdline  )

        cmdline = "antsApplyTransforms -e 3 -d 3 -n Linear  -i "+self.inputs.fixed_image+" -t "+self.inputs.out_matrix_inverse +" -r "+self.inputs.moving_image+" -o "+self.inputs.inverse_warped_image
        print(cmdline)
        cmd( cmdline  )

    def apply_linear_transforms(self):
        
        #Command line to 
        if not os.path.exists(self.inputs.warped_image) :
            cmdline = "antsApplyTransforms -e 3 -d 3 -n Linear  -i " + self.inputs.moving_image + " -t "+ self.inputs.out_matrix +" -r "+self.inputs.fixed_image+" -o "+self.inputs.warped_image
            print(cmdline)
            cmd( cmdline  )

        if not os.path.exists(self.inputs.out_matrix_inverse) :
            cmdline = "antsApplyTransforms -e 3 -d 3  -n Linear -i "+self.inputs.moving_image+" -t "+self.inputs.out_matrix +" -r "+self.inputs.fixed_image+" -o Linear["+self.inputs.out_matrix_inverse+",1]"
            print(cmdline)
            cmd( cmdline  )

        def mat2txt(self, ii_fn, oo_fn):
            print(ii_fn, oo_fn)
            tfm=sitk.ReadTransform(ii_fn)
            sitk.WriteTransform( tfm, oo_fn  )
            return 0 

    def _create_output_prefix(self, fn, space):
        basefn = os.path.basename(fn) 
        if not '_space-' in basefn :
            basefn_split = splitext(basefn)
            return basefn_split[0] + '_space-' + space + basefn_split[1]
        else : 
            return '_'.join( [ f  if not 'space-' in f else 'space-'+space for f in basefn.split('_') ] )

    def _set_outputs(self):
        outprefix = self.inputs.outprefix 
        moving_prefix=splitext(os.path.basename(self.inputs.moving_image))[0]
        fixed_prefix =splitext(os.path.basename(self.inputs.fixed_image))[0]
        self.inputs.warped_image = f'{os.getcwd()}/{moving_prefix}_space-{self.inputs.fixed_image_space}_{self.inputs.type_of_transform}.nii.gz'
        self.inputs.inverse_warped_image = f'{os.getcwd()}/{fixed_prefix}_space-{self.inputs.moving_image_space}_{self.inputs.type_of_transform}.nii.gz'

        #if self.inputs.normalization_type == 'nl' :
        self.inputs.composite_transform = f'{outprefix}Composite.h5'
        self.inputs.inverse_composite_transform = f'{outprefix}InverseComposite.h5'
        #else :
        #    self.inputs.out_matrix=os.getcwd()+os.sep+'transform0GenericAffine.mat'
        #    self.inputs.out_matrix_inverse=os.getcwd()+os.sep+'transform0GenericAffine_inverse.mat'

    def _list_outputs(self):
        self._set_outputs()
        outputs = self.output_spec().get()
        if isdefined(self.inputs.warped_image):
            outputs["warped_image"] = self.inputs.warped_image
        if isdefined(self.inputs.inverse_warped_image):
            outputs["inverse_warped_image"] = self.inputs.inverse_warped_image
        if isdefined(self.inputs.composite_transform):
            outputs["composite_transform"]=self.inputs.composite_transform
        if isdefined(self.inputs.out_matrix):
            outputs["out_matrix"]=self.inputs.out_matrix
        if isdefined(self.inputs.out_matrix_inverse):
            outputs["out_matrix_inverse"]=self.inputs.out_matrix_inverse
        if isdefined(self.inputs.inverse_composite_transform):
            outputs["inverse_composite_transform"]= self.inputs.inverse_composite_transform
        return outputs
