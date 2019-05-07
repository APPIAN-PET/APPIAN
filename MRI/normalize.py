import os
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.ants import registration, segmentation
from nipype.interfaces.ants.segmentation import Atropos
from nipype.interfaces.ants import Registration, ApplyTransforms
from MRI.mincbeast import SegmentationToBrainMask, beast, mincbeast_library, create_alt_template
from Extra.extra import copyCommand
from Registration.ants_mri_normalize import APPIANRegistration, APPIANApplyTransforms
from nipype.interfaces.utility import Rename
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
import nipype.interfaces.utility as util
import Initialization.initialization as init
import nipype.interfaces.io as nio
import nipype.interfaces.minc as minc
from nipype.interfaces.ants import N4BiasFieldCorrection
from Extra.utils import splitext 
from nipype.interfaces.ants.segmentation import BrainExtraction
from arg_parser import icbm_default_template, file_dir

global icbm_default_csf  
global icbm_default_gm
global icbm_default_wm 

icbm_default_csf=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_csf_tal_nlin_asym_09c.nii.gz"
icbm_default_gm=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_gm_tal_nlin_asym_09c.nii.gz"
icbm_default_wm=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_wm_tal_nlin_asym_09c.nii.gz"
icbm_default_brain=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_t1_tal_nlin_asym_09c_mask.nii.gz"

def get_workflow(name, opts):
    workflow = pe.Workflow(name=name)
    in_fields = ['mri']
    if opts.user_brainmask :
        in_fields += ['brain_mask_space_stx']
    
    if opts.user_mri_stx :
        in_fields += ['tfm_mri_stx', 'tfm_stx_mri']

    label_types = [opts.tka_label_type, opts.pvc_label_type, opts.results_label_type]
    stages = ['tka', 'pvc', 'results']
    label_imgs= [opts.tka_label_img, opts.pvc_label_img, opts.results_label_img  ]

    inputnode = pe.Node(niu.IdentityInterface(fields=in_fields), name="inputnode")

    out_fields=['tfm_stx_mri', 'tfm_mri_stx', 'brain_mask_space_stx', 'brain_mask_space_mri', 'mri_space_stx', 'mri_space_nat' ]
    for stage, label_type in zip(stages, label_types):
        if 'internal_cls' == label_type :
            out_fields += [ stage+'_label_img']
    
    outputnode = pe.Node(niu.IdentityInterface(fields=out_fields), name='outputnode')

    ##########################################
    # T1 spatial (+ intensity) normalization #
    ##########################################
    if opts.n4_bspline_fitting_distance != 0 :
        n4 =  pe.Node(N4BiasFieldCorrection(), "mri_intensity_normalized" )
        workflow.connect(inputnode, 'mri', n4, 'input_image')
        n4.inputs.dimension = 3 
        n4.inputs.bspline_fitting_distance = opts.n4_bspline_fitting_distance 
        n4.inputs.shrink_factor = opts.n4_shrink_factor
        n4.inputs.n_iterations = opts.n4_n_iterations
        n4.inputs.convergence_threshold = opts.n4_convergence_threshold
    else :
        n4 = pe.Node(niu.IdentityInterface(fields=["output_image"]), name='mri_no_intensity_normalization')
        workflow.connect(inputnode, 'mri', n4, 'output_image')

    if opts.user_mri_stx != '':
        mri2template = pe.Node(interface=APPIANRegistration(), name="mri_spatial_normalized")
        mri2template.inputs.fixed_image_mask = icbm_default_brain
        mri2template.inputs.fixed_image = opts.template
        workflow.connect(n4, 'output_image', mri2template, 'moving_image')
        if opts.user_ants_normalization != None :
            mri2template.inputs.user_ants_normalization = opts.user_ants_normalization
        if opts.normalization_type :
            mri2template.inputs.normalization_type = opts.normalization_type

        mri_stx_file = 'warped_image'
        mri_stx_node = mri2template
        
        tfm_node= mri2template
        tfm_inv_node= mri2template
        if opts.normalization_type == 'nl' :
            tfm_file='composite_transform'
            tfm_inv_file='inverse_composite_transform'
        elif opts.normalization_type == 'affine' :
            tfm_file='out_matrix'
            tfm_inv_file='out_matrix_inverse'
        else :
            print("Error: --normalization-type should be either rigid, lin, or nl")
            exit(1)
    else :
        transform_mri = pe.Node(interface=APPIANApplyTransforms(), name="transform_mri"  )
        workflow.connect(inputnode, 'mri', transform_mri, 'input_image')
        workflow.connect(inputnode, 'tfm_mri_stx', transform_mri, 'transform_1')
        transform_mri.inputs.reference_image = opts.template

        mri_stx_node = transform_mri
        mri_stx_file = 'output_image'
        tfm_node = inputnode
        tfm_file = 'tfm_mri_stx'
        tfm_inv_node=inputnode
        tfm_inv_file='tfm_stx_mri'
    
    #
    # T1 in native space will be part of the APPIAN target directory
    # and hence it won't be necessary to link to the T1 in the source directory.
    #
    copy_mri_nat = pe.Node(interface=copyCommand(), name="mri_nat"  )
    workflow.connect(inputnode, 'mri', copy_mri_nat, 'input_file')
    
    ###################################
    # Segment T1 in Stereotaxic space #
    ###################################
    seg=None

    if opts.ants_atropos_priors == [] and opts.template == icbm_default_template :
        opts.ants_atropos_priors = [ icbm_default_csf, icbm_default_gm, icbm_default_wm ]
    if opts.ants_atropos_priors == [] :
        print("Warning : user did not provide alternative priors for template. This will affect your T1 MRI segmentation. Check this segmentation visually to make sure it is what you want ")

    for stage, label_type, img in zip(stages, label_types, label_imgs) :
        if  seg == None :
            seg = pe.Node(interface=Atropos(), name="segmentation_ants")
            seg.inputs.dimension=3
            seg.inputs.number_of_tissue_classes=len(opts.ants_atropos_priors)
            seg.inputs.initialization = 'PriorProbabilityImages'
            seg.inputs.prior_weighting = opts.ants_atropos_prior_weighting
            seg.inputs.prior_probability_images = opts.ants_atropos_priors
            seg.inputs.likelihood_model = 'Gaussian'
            seg.inputs.posterior_formulation = 'Socrates'
            seg.inputs.use_mixture_model_proportions = True
            seg.inputs.args="-v 1"
            workflow.connect(mri_stx_node, mri_stx_file,  seg, 'intensity_images' )
            seg.inputs.mask_image = icbm_default_brain
            #workflow.connect(brain_mask_node, brain_mask_file,  seg, 'mask_image' )
        print(stage, img) 
        if 'antsAtropos' == img :
           workflow.connect(seg, 'classified_image', outputnode, stage+'_label_img')
    
    ####################
    # T1 Brain masking #
    ####################
    if not opts.user_brainmask :
       #  if opts.brain_extraction_method == 'beast':
       #      #Brain Mask MNI-Space
       #      mriMNI_brain_mask = pe.Node(interface=beast(), name="mri_stx_brain_mask")
       #      mriMNI_brain_mask.inputs.library_dir  = library_dir
       #      mriMNI_brain_mask.inputs.template  = library_dir+"/margin_mask.mnc"
       #      mriMNI_brain_mask.inputs.configuration = mriMNI_brain_mask.inputs.library_dir+os.sep+"default.2mm.conf"
       #      mriMNI_brain_mask.inputs.same_resolution = True
       #      mriMNI_brain_mask.inputs.median = True
       #      mriMNI_brain_mask.inputs.fill = True
       #      mriMNI_brain_mask.inputs.median = True

       #      workflow.connect(mri_stx_node, mri_stx_file, mriMNI_brain_mask, "in_file" )

       #      brain_mask_node = mriMNI_brain_mask
       #      brain_mask_file = 'out_file'
       #  else : 
            #mriMNI_brain_mask = pe.Node(interface=BrainExtraction(), name="mri_stx_brain_mask")
            #mriMNI_brain_mask.inputs.dimension = 3
            #mriMNI_brain_mask.inputs.brain_template = opts.template
            #template_base, template_ext = splitext(opts.template)
            #mriMNI_brain_mask.inputs.brain_probability_mask =template_base+'_variant-brain_pseg'+template_ext

        mriMNI_brain_mask = pe.Node(interface=SegmentationToBrainMask(), name="mri_stx_brain_mask")
        #workflow.connect(mri_stx_node, mri_stx_file, mriMNI_brain_mask, "anatomical_image" )
        workflow.connect(seg, 'classified_image', mriMNI_brain_mask, "seg_file" )

        brain_mask_node = mriMNI_brain_mask
        brain_mask_file = 'output_image'

    else :			
        brain_mask_node = inputnode
        brain_mask_file = 'brain_mask_space_stx'
    
    #
    # Transform brain mask from stereotaxic to T1 native space
    #
    transform_brain_mask = pe.Node(interface=APPIANApplyTransforms(),name="transform_brain_mask")
    transform_brain_mask.inputs.interpolation = 'NearestNeighbor'
    workflow.connect(brain_mask_node, brain_mask_file, transform_brain_mask, 'input_image')
    workflow.connect(tfm_node, tfm_inv_file, transform_brain_mask, 'transform_1')
    workflow.connect(copy_mri_nat,'output_file', transform_brain_mask,'reference_image') 
    ###############################
    # Pass results to output node #
    ###############################
    workflow.connect(brain_mask_node, brain_mask_file, outputnode, 'brain_mask_space_stx')
    workflow.connect(tfm_node, tfm_file, outputnode, 'tfm_mri_stx' )
    workflow.connect(tfm_node, tfm_inv_file, outputnode, 'tfm_stx_mri' )
    workflow.connect(transform_brain_mask, 'output_image', outputnode, 'brain_mask_space_mri')
    #workflow.connect(mri_stx_node, mri_stx_file, outputnode, 'mri_space_stx')
    workflow.connect(copy_mri_nat, 'output_file', outputnode, 'mri_space_nat')
    return(workflow)


