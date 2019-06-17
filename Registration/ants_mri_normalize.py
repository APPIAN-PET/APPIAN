from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.ants import registration, segmentation
from nipype.interfaces.ants.segmentation import Atropos
from nipype.interfaces.ants import Registration, ApplyTransforms
from MRI.mincbeast import beast, mincbeast_library, create_alt_template
from Extra.extra import copyCommand
from nipype.interfaces.utility import Rename
from nipype.interfaces.ants import Registration, ApplyTransforms
from nipype.interfaces.ants.registration import CompositeTransformUtil, CompositeTransformUtilInputSpec
from nipype.interfaces.ants.resampling import ApplyTransformsInputSpec
from nipype.interfaces.base import InputMultiPath
from Extra.utils import splitext, cmd
from scipy.io import loadmat
import nipype.pipeline.engine as pe
import SimpleITK as sitk
import os
import re


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
    reference_image=traits.File()
    input_image=traits.File()
    output_image = traits.File()
    interpolation = traits.Str(usedefault=True, default_value='Linear')

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
        
        cmd = ApplyTransforms()
        cmd.inputs.transforms=transforms
        cmd.inputs.invert_transform_flags = invert_transform_flags
        cmd.inputs.reference_image = self.inputs.reference_image
        cmd.inputs.input_image = self.inputs.input_image
        cmd.inputs.interpolation = self.inputs.interpolation
        cmd.run()
        split =splitext(os.path.basename( self.inputs.input_image))
        self.inputs.output_image =os.getcwd() + os.sep + split[0] + '_trans' + split[1] 
        print(os.listdir(os.getcwd()))
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_image"] =  self.inputs.output_image
        #print "\n\nCHECK"
        #print os.path.exists(self.inputs.output_image)
        #print "\n"
        
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
    user_ants_normalization = traits.File(desc="User provided normalization file")
    normalization_type = traits.Str(desc="Type of registration: rigid, affine, nl", usedefault=True, default_value="nl")
    moving_image_space = traits.Str(desc="Name of coordinate space for moving image", usedefault=True, default_value="source")
    fixed_image_space = traits.Str(desc="Name of coordinate space for fixed image", usedefault=True, default_value="target")
    interpolation = traits.Str(desc="Type of registration: Linear, NearestNeighbor, MultiLabel[<sigma=imageSpacing>,<alpha=4.0>], Gaussian[<sigma=imageSpacing>,<alpha=1.0>], BSpline[<order=3>], CosineWindowedSinc, WelchWindowedSinc, HammingWindowedSinc, LanczosWindowedSinc, GenericLabel", usedefault=True, default_value="Linear")
    
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

    def user_command_line(self) :
        cmdline=''
        if not os.path.exists(self.inputs.user_ants_normalization) :
            print("Error : could not read --user-ants-normalization file specified by user ", self.inputs.user_ants_normalization)
            exit(1)
        else :
            with open(self.inputs.user_ants_normalization) as f:
                for l in f.readlines():
                    print('read', l)
                    cmdline += ' ' + l.rstrip("\n")  

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

        ### Base Options
        cmdline="antsRegistration --verbose 1 --float --collapse-output-transforms 1 --dimensionality 3 --initial-moving-transform [ "+self.inputs.fixed_image+", "+self.inputs.moving_image+", 1 ] --initialize-transforms-per-stage 0 --interpolation "+self.inputs.interpolation+' '

        ### Rigid
        cmdline+=" --transform Rigid[ 0.1 ] --metric Mattes[ "+self.inputs.fixed_image+", "+self.inputs.moving_image+", 1, 32, Regular, 0.3 ] --convergence [ 500x250x200, 1e-08, 20 ] --smoothing-sigmas 8.0x4.0x2.0vox --shrink-factors 8x4x2 --use-estimate-learning-rate-once 1 --use-histogram-matching 0 " 
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


    def apply_linear_transforms(self):
        #Command line to 
        cmdline = "antsApplyTransforms -e 3 -d 3 -n Linear  -i "+self.inputs.moving_image+" -t "+ self.inputs.out_matrix +" -r "+self.inputs.fixed_image+" -o "+self.inputs.warped_image
        print(cmdline)
        cmd( cmdline  )

        cmdline = "antsApplyTransforms -e 3 -d 3 -n Linear  -i "+self.inputs.moving_image+" -t "+ self.inputs.out_matrix +" -r "+self.inputs.fixed_image+" -o Linear["+self.inputs.out_matrix_inverse+",1]"
        
        print(cmdline)
        cmd( cmdline  )

    def mat2txt(self, ii_fn, oo_fn):
        print(ii_fn, oo_fn)
        tfm=sitk.ReadTransform(ii_fn)
        sitk.WriteTransform( tfm, oo_fn  )
        return 0 

    def _run_interface(self, runtime):
        self._set_outputs()
        #Setup ANTs command line arguments
        if isdefined(self.inputs.user_ants_normalization):
            cmdline = self.user_command_line()
        else :
            cmdline = self.default_command_line()
        #Run antsRegistration on command line
        print("Ants command line:\n", cmdline)
        p = cmd(cmdline)	
         
        if self.inputs.normalization_type in ['rigid', 'affine']:
            #Convet linear transforms from .mat to .txt. antsRegistration produces .mat file based on output
            #prefix, but this format seems to be harder to work with / lead to downstream errors
            #self.mat2txt(os.getcwd()+os.sep+'transform0GenericAffine.mat', self.inputs.out_matrix)
            #self.mat2txt(os.getcwd()+os.sep+'transform0GenericAffine_inverse.mat', self.inputs.out_matrix_inverse)
            #If linear transform, then have to apply transformations to input image
            self.apply_linear_transforms()

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
