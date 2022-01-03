from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.ants import registration, segmentation
from nipype.interfaces.ants.segmentation import Atropos
from nipype.interfaces.ants import Registration, ApplyTransforms
from nipype.interfaces.utility import Rename
from nipype.interfaces.ants.registration import CompositeTransformUtil, CompositeTransformUtilInputSpec
from nipype.interfaces.ants.resampling import ApplyTransformsInputSpec
from nipype.interfaces.base import InputMultiPath
from src.utils import splitext, cmd
from scipy.io import loadmat
from scipy.ndimage import center_of_mass
import numpy as np
import nibabel as nib
import nipype.pipeline.engine as pe
import SimpleITK as sitk
import os
import re

def get_space(filename, default) : 
    if '_space-' in filename :
        return [ re.sub('space-','',s)  for s in filename.split('_') if 'space-' in s ][0]
    else : 
        return default 

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
    source_space = traits.Str(default_value='src', usedefault=True)
    target_space = traits.Str(default_value='tgt', usedefault=True)
    reference_image=traits.File(mandatory=True, exists=True)
    input_image=traits.File(mandatory=True, exists=True)
    output_image = traits.File()
    output_image_inverse = traits.File()
    target_space=traits.Str(default_value="undefined", usedefault=True)
    interpolation = traits.Str(usedefault=True, default_value='BSpline')

class APPIANApplyTransformsOutputSpec(TraitedSpec) :
    output_image = traits.File(exists=True)
    output_image_inverse = traits.File()

class APPIANApplyTransforms(BaseInterface):
    input_spec = APPIANApplyTransformsInputSpec
    output_spec = APPIANApplyTransformsOutputSpec

    def gen_output_filename(self, filename, default):
        space = get_space(filename, default)
        print('---> filename ',filename)
        if '_space-' in filename :
            output_image = re.sub('_space-[A-z]*_',f'_space-{space}_', filename)
        else :
            output_image = re.sub('.nii',f'_space-{space}.nii',filename)

        return output_image

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
       
        flip  = lambda x : 0 if x == 1 else 1
        flipped_invert_transform_flags = map(flip, invert_transform_flags)

        src_dims=nib.load(self.inputs.input_image).shape
        tgt_dims=nib.load(self.inputs.reference_image).shape
        get_ndim = lambda dims : 0 if len(dims)==3 or (len(dims) == 4 and dims[-1] == 1) else 3
        src_ndim= get_ndim(src_dims)
        tgt_ndim= get_ndim(tgt_dims)

        #output files
        self.inputs.output_image = self.gen_output_filename(self.inputs.input_image, self.inputs.source_space)
        self.inputs.output_image_inverse = self.gen_output_filename(self.inputs.reference_image, self.inputs.target_space)

        print('1',self.inputs.output_image_inverse)
        print('2', self.inputs.output_image)
        #combine transformation files and output flags
        transforms_zip = zip(transforms, invert_transform_flags)
        flipped_transforms_zip = zip(transforms, flipped_invert_transform_flags)

        transform_string = ' '.join( [ '-t [ '+str(t)+' , '+str(int(f))+' ]' for t, f in transforms_zip  if t != None ]) 
        flipped_transform_string = ' '.join( [ '-t [ '+str(t)+' , '+str(int(f))+' ]' for t, f in flipped_transforms_zip  if t != None ])
       
        # apply forward transform
        cmdline = f'antsApplyTransforms --float -v 1 -d 3 -e {src_ndim} -n '+ self.inputs.interpolation + " -i "+self.inputs.input_image+" "+ transform_string +" -r "+self.inputs.reference_image+" -o "+self.inputs.output_image
        print(cmdline) 
        cmd(cmdline)
        
        # apply inverse transform
        cmdline = f'antsApplyTransforms --float -v 1 -d 3 -e {tgt_ndim} -n '+ self.inputs.interpolation + " -r "+self.inputs.input_image+" "+ flipped_transform_string +" -i "+self.inputs.reference_image+" -o "+self.inputs.output_image_inverse
        cmd(cmdline)
        print('hello hello')
        print( nib.load(self.inputs.output_image).shape); 

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_image"] =  self.inputs.output_image
        outputs["output_image_inverse"] =  self.inputs.output_image_inverse

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
    fixed_image_mask = traits.File(desc="Mask for fixed image")
    moving_image = traits.File(mandatory=True, exits=True, desc="Moving Image")
    moving_image_mask = traits.File(desc="Mask for moving image")
    warped_image = traits.File(desc="Warped image")
    inverse_warped_image = traits.File(desc="Inverse warped image")
    composite_transform = traits.File(desc="Composite transorfmation matrix")
    inverse_composite_transform = traits.File(desc="Inverse composite transorfmation matrix")
    user_ants_command = traits.File(desc="User provided normalization file")
    normalization_type = traits.Str(desc="Type of registration: rigid, affine, nl", usedefault=True, default_value="nl")
    moving_image_space = traits.Str(desc="Name of coordinate space for moving image", usedefault=True, default_value="source")
    fixed_image_space = traits.Str(desc="Name of coordinate space for fixed image", usedefault=True, default_value="target")
    interpolation = traits.Str(desc="Type of registration: Linear, NearestNeighbor, MultiLabel[<sigma=imageSpacing>,<alpha=4.0>], Gaussian[<sigma=imageSpacing>,<alpha=1.0>], BSpline[<order=3>], CosineWindowedSinc, WelchWindowedSinc, HammingWindowedSinc, LanczosWindowedSinc, GenericLabel", usedefault=True, default_value="Linear")
    #misalign_matrix = traits.Str(desc="Misalignment matrix", usedefault=True, default_value=" ")
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

    def read_user_command_line(self) :
        cmdline=''
        if not os.path.exists(self.inputs.user_ants_command) :
            print("Error : could not read --user-ants-command file specified by user ", self.inputs.user_ants_command)
            exit(1)
        else :
            with open(self.inputs.user_ants_command) as f:
                for l in f.readlines():
                    print('read', l)
                    cmdline += ' ' + l.rstrip("\n")  

        if 'SyN' in cmdline : 
            normalization_type = 'nl' 
        elif 'Affine' in cmdline :
            normalization_type = 'affine' 
        else  :
            normalization_type = 'rigid' 

        return cmdline, normalization_type
        
    def replace_user_command_line(self, cmdline): 
        replacement=[   ['fixed_image',self.inputs.fixed_image], 
                        ['moving_image',self.inputs.moving_image],
                        ['fixed_image_mask', self.inputs.fixed_image_mask], 
                        ['moving_image_mask', self.inputs.moving_image_mask], 
                        ['composite_transform', self.inputs.composite_transform], 
                        ['inverse_composite_transform', self.inputs.inverse_composite_transform],
                        ['inverse_warped_image', self.inputs.inverse_warped_image], 
                        #Warning, inverse_warped_image must come before warped_image
                        ['warped_image', self.inputs.warped_image],
                        ['interpolation_method', self.inputs.interpolation]
                        ]
        for string, variable in replacement :
            if isdefined(variable) :
                cmdline = re.sub(string, variable, cmdline) 
        
        print("User provided ANTs command line")
        return cmdline

    def default_command_line(self):
        # If user has not specified their own file with an ANTs command line argument
        # create a command line argument based on whether the normalization type is set to 
        # rigid, affine, or non-linear. 
        mask_string=""
        if isdefined(self.inputs.fixed_image_mask) and isdefined(self.inputs.moving_image_mask) :
            if os.path.exists(self.inputs.fixed_image_mask) and os.path.exists(self.inputs.moving_image_mask) :
                mask_string=" --masks ["+self.inputs.fixed_image_mask+","+self.inputs.moving_image_mask+"] "
            
        ### Base Options
        cmdline="antsRegistration --verbose 1 --float --collapse-output-transforms 1 --dimensionality 3 "+mask_string+" --initial-moving-transform [ "+self.inputs.fixed_image+", "+self.inputs.moving_image+", 1 ] --initialize-transforms-per-stage 0 --interpolation "+self.inputs.interpolation+' '

        ### Rigid
        cmdline+=" --transform Rigid[ 0.1 ] --metric Mattes[ "+self.inputs.fixed_image+", "+self.inputs.moving_image+", 1, 32, Regular, 0.3 ] --convergence [ 500x250x200x100, 1e-08, 20 ] --smoothing-sigmas 8.0x4.0x2.0x1.0vox --shrink-factors 8x4x2x1 --use-estimate-learning-rate-once 1 --use-histogram-matching 0 " 
        #output = " --output [ transform ] "

        ### Affine
        if self.inputs.normalization_type == 'affine' or self.inputs.normalization_type == 'nl':
            cmdline += " --transform Affine[ 0.1 ] --metric Mattes[ "+self.inputs.fixed_image+", "+self.inputs.moving_image+", 1, 32, Regular, 0.3 ] --convergence [ 500x400x300 , 1e-08, 20 ] --smoothing-sigmas 4.0x2.0x1.0vox --shrink-factors 4x2x1 --use-estimate-learning-rate-once 1 --use-histogram-matching 0 " 
       
        ### Non-linear
        if  self.inputs.normalization_type == 'nl':
            #cmdline += " --transform SyN[ 0.1, 3.0, 0.0] --metric Mattes[ "+self.inputs.fixed_image+", "+self.inputs.moving_image+", 0.5, 64, None ]  --convergence [ 100x100x100x100, 1e-6,10 ] --smoothing-sigmas 4.0x2.0x1.0x0.0vox --shrink-factors 4x2x1x1  --winsorize-image-intensities [ 0.005, 0.995 ]  --write-composite-transform 1 "
            cmdline += " --transform SyN[ 0.1, 3.0, 0.0] --metric Mattes[ "+self.inputs.fixed_image+", "+self.inputs.moving_image+", 0.5, 64, None ]  --convergence [ 500x400x300x200, 1e-6,10 ] --smoothing-sigmas 4.0x2.0x1.0x0.0vox --shrink-factors 4x2x1x1  --winsorize-image-intensities [ 0.005, 0.995 ]  --write-composite-transform 1 "
        
        output = " --output [ transform, "+self.inputs.warped_image+", "+self.inputs.inverse_warped_image+" ] "
        
        cmdline += output

        return cmdline 

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
            cmdline = "antsApplyTransforms -e 3 -d 3 -n Linear  -i "+self.inputs.moving_image+" -t "+ self.inputs.out_matrix +" -r "+self.inputs.fixed_image+" -o "+self.inputs.warped_image
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

    def _run_interface(self, runtime):
        normalization_type = self.inputs.normalization_type

        #Setup ANTs command line arguments
        if isdefined(self.inputs.user_ants_command):
            cmdline, self.inputs.normalization_type = self.read_user_command_line()
            self._set_outputs()
            cmdline = self.replace_user_command_line(cmdline)
        else :
            self._set_outputs()
            cmdline = self.default_command_line()
        print(self.inputs); 
        #Run antsRegistration on command line
        print("Ants command line:\n", cmdline)
        p = cmd(cmdline)	
         
        if self.inputs.normalization_type in ['rigid', 'affine']:
            #Convert linear transforms from .mat to .txt. antsRegistration produces .mat file based on output
            #prefix, but this format seems to be harder to work with / lead to downstream errors
            #If linear transform, then have to apply transformations to input image
            self.apply_linear_transforms()

        if isdefined( self.inputs.rotation_error) or isdefined( self.inputs.translation_error ) : 
            if self.inputs.rotation_error != [0,0,0] and self.inputs.translation_error != [0,0,0] : 
                print('Warning: Applying misalignment')
                print("\tRotation:",self.inputs.rotation_error)
                print("\tTranslation:",self.inputs.translation_error)
                exit(1)
                self.apply_misalignment()
            

        return runtime

    def _create_output_file(self, fn, space):
        basefn = os.path.basename(fn) 
        if not '_space-' in basefn :
            basefn_split = splitext(basefn)
            return basefn_split[0] + '_space-' + space + basefn_split[1]
        else : 
            return '_'.join( [ f  if not 'space-' in f else 'space-'+space for f in basefn.split('_') ] )

    def _set_outputs(self):
        self.inputs.warped_image=os.getcwd()+os.sep+ self._create_output_file(self.inputs.moving_image,self.inputs.fixed_image_space )
        self.inputs.inverse_warped_image=os.getcwd()+os.sep+self._create_output_file(self.inputs.fixed_image, self.inputs.moving_image_space )
        if self.inputs.normalization_type == 'nl' :
            self.inputs.composite_transform=os.getcwd()+os.sep+'transformComposite.h5'
            self.inputs.inverse_composite_transform=os.getcwd()+os.sep+'transformInverseComposite.h5'
        else :
            self.inputs.out_matrix=os.getcwd()+os.sep+'transform0GenericAffine.mat'
            self.inputs.out_matrix_inverse=os.getcwd()+os.sep+'transform0GenericAffine_inverse.mat'

    def _list_outputs(self):
        outputs = self.output_spec().get()
        self._set_outputs()
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
