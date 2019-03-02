import os
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.ants import registration, segmentation
from nipype.interfaces.ants.segmentation import Atropos
from nipype.interfaces.ants import Registration, ApplyTransforms
from MRI.mincbeast import beast, mincbeast_library, create_alt_template
from Extra.conversion import mnc2niiCommand
from Extra.extra import copyCommand
from Registration.ants_mri_normalize import myRegistration
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

icbm_default_csf=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_csf_tal_nlin_asym_09c.nii"
icbm_default_gm=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_gm_tal_nlin_asym_09c.nii"
icbm_default_wm=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_wm_tal_nlin_asym_09c.nii"
icbm_default_brain=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_t1_tal_nlin_asym_09c_mask.nii"

def get_workflow(name, opts):
    workflow = pe.Workflow(name=name)
    in_fields = ['t1']
    if opts.user_brainmask :
        in_fields += ['brain_mask_mni']
    
    if opts.user_t1mni :
        in_fields += ['tfmT1MNI', 'tfmMNIT1']

    label_types = [opts.tka_label_type, opts.pvc_label_type, opts.results_label_type]
    stages = ['tka', 'pvc', 'results']
    label_imgs= [opts.tka_label_img, opts.pvc_label_img, opts.results_label_img  ]

    inputnode = pe.Node(niu.IdentityInterface(fields=in_fields), name="inputnode")

    out_fields=['tfmMNIT1', 'tfmT1MNI',  'tfmT1MNI_invert',  'brain_mask_mni', 'brain_mask_t1', 't1_mni', 't1_nat' ]
    for stage, label_type in zip(stages, label_types):
        if 'internal_cls' == label_type :
            out_fields += [ stage+'_label_img']
    
    outputnode = pe.Node(niu.IdentityInterface(fields=out_fields), name='outputnode')

    #
    # Setup dir for minc beast if not using user provided brain mask
    #
    #if not opts.user_brainmask : 
    #    if opts.beast_library_dir == None :
    #        library_dir = mincbeast_library(opts.template)
    #    else :
    #        library_dir = opts.beast_library_dir
        
        #template_rsl = create_alt_template(opts.template, library_dir)

    ##########################################
    # T1 spatial (+ intensity) normalization #
    ##########################################
    
    if opts.n4_bspline_fitting_distance != 0 :
        n4 =  pe.Node(N4BiasFieldCorrection(), "mri_intensity_normalized" )
        workflow.connect(inputnode, 't1', n4, 'input_image')
        n4.inputs.dimension = 3 
        n4.inputs.bspline_fitting_distance = opts.n4_bspline_fitting_distance 
        n4.inputs.shrink_factor = opts.n4_shrink_factor
        n4.inputs.n_iterations = opts.n4_n_iterations
        n4.inputs.convergence_threshold = opts.n4_convergence_threshold
    else :
        n4 = pe.Node(niu.IdentityInterface(fields=["output_image"]), name='mri_no_intensity_normalization')


    if not opts.user_t1mni:
        mri2template = pe.Node(interface=myRegistration(), name="mri_spatial_normalized")
        mri2template.inputs.fixed_image_mask = icbm_default_brain
        mri2template.inputs.fixed_image = fixed_image=opts.template
        if opts.user_ants_normalization != None :
            mri2template.inputs.user_ants_normalization = opts.user_ants_normalization
        if opts.normalization_type :
            mri2template.inputs.normalization_type = opts.normalization_type
        workflow.connect(n4, 'output_image', mri2template, 'moving_image')
       

        t1_mni_file = 'warped_image'
        t1_mni_node=mri2template
        
        tfm_node= mri2template
        tfm_file='composite_transform'
        tfm_inv_node= mri2template
        tfm_inv_file='inverse_composite_transform'

    else :
        transform_t1 = pe.Node(interface=ApplyTransforms(), name="transform_t1"  )
        transform_t1.inputs.two=True
        workflow.connect(inputnode, 't1', transform_t1, 'input_file')
        workflow.connect(inputnode, 'tfmT1MNI', transform_t1, 'transformation')
        transform_t1.inputs.like = opts.template

        t1_mni_node = transform_t1
        t1_mni_file = 'output_file'
        tfm_node = inputnode
        tfm_file = 'tfmT1MNI'
        tfm_inv_node=inputnode
        tfm_inv_file='tfmMNIT1'
    

    #
    # T1 in native space will be part of the APPIAN target directory
    # and hence it won't be necessary to link to the T1 in the source directory.
    #
    copy_t1_nat = pe.Node(interface=copyCommand(), name="t1_nat"  )
    workflow.connect(inputnode, 't1', copy_t1_nat, 'input_file')
    
#    ####################
#    # T1 Brain masking #
#    ####################
#    if not opts.user_brainmask :
#        if opts.brain_extraction_method == 'beast':
#            #Brain Mask MNI-Space
#            t1MNI_brain_mask = pe.Node(interface=beast(), name="t1_mni_brain_mask")
#            t1MNI_brain_mask.inputs.library_dir  = library_dir
#            t1MNI_brain_mask.inputs.template  = library_dir+"/margin_mask.mnc"
#            t1MNI_brain_mask.inputs.configuration = t1MNI_brain_mask.inputs.library_dir+os.sep+"default.2mm.conf"
#            t1MNI_brain_mask.inputs.same_resolution = True
#            t1MNI_brain_mask.inputs.median = True
#            t1MNI_brain_mask.inputs.fill = True
#            t1MNI_brain_mask.inputs.median = True
#
#            workflow.connect(t1_mni_node, t1_mni_file, t1MNI_brain_mask, "in_file" )
#
#            brain_mask_node = t1MNI_brain_mask
#            brain_mask_file = 'out_file'
#        else : 
#            t1MNI_brain_mask = pe.Node(interface=BrainExtraction(), name="t1_mni_brain_mask")
#            
#            t1MNI_brain_mask.inputs.dimension = 3
#            t1MNI_brain_mask.inputs.brain_template = opts.template
#            template_base, template_ext = splitext(opts.template)
#            t1MNI_brain_mask.inputs.brain_probability_mask =template_base+'_variant-brain_pseg'+template_ext
#
#            workflow.connect(t1_mni_node, t1_mni_file, t1MNI_brain_mask, "anatomical_image" )
#
#            brain_mask_node = t1MNI_brain_mask
#            brain_mask_file = 'output_image'
#
#    else :			
#        brain_mask_node = inputnode
#        brain_mask_file = 'brain_mask_mni'
#    
#    #
#    # Transform brain mask from stereotaxic to T1 native space
#    #
#    transform_brain_mask = pe.Node(interface=ApplyTransforms(), name="transform_brain_mask"  )
#    transform_brain_mask.inputs.interpolation = 'NearestNeighbor'
#    workflow.connect(brain_mask_node, brain_mask_file, transform_brain_mask, 'input_image')
#    workflow.connect(inputnode, 't1', transform_brain_mask, 'reference_image')
#    workflow.connect(tfm_node, tfm_inv_file, transform_brain_mask, 'transforms')


    ###################################
    # Segment T1 in Stereotaxic space #
    ###################################
    seg=None

    if opts.ants_atropos_priors == [] and opts.template == icbm_default_template :
        opts.ants_atropos_priors = [ icbm_default_csf, icbm_default_gm, icbm_default_wm ]
    if opts.ants_atropos_priors == [] :
        print("Warning : user did not provide alternative priors for template. This will affect your T1 MRI segmentation. Check this segmentation visually to make sure it is what you want ")

    for stage, label_type, img in zip(stages, label_types, label_imgs) :
        if 'antsAtropos' == img and seg == None :
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
            workflow.connect(t1_mni_node, t1_mni_file,  seg, 'intensity_images' )
            seg.inputs.mask_image = icbm_default_brain
            #workflow.connect(brain_mask_node, brain_mask_file,  seg, 'mask_image' )
        print(stage, img) 
        if 'antsAtropos' == img :
           workflow.connect(seg, 'classified_image', outputnode, stage+'_label_img')
    return workflow 
    ###############################
    # Pass results to output node #
    ###############################
    workflow.connect(brain_mask_node, brain_mask_file, outputnode, 'brain_mask_mni')
    workflow.connect(tfm_node, tfm_file, outputnode, 'tfmT1MNI' )
    workflow.connect(tfm_node, '', outputnode, 'tfmMNIT1' )
    workflow.connect(transform_brain_mask, 'output_image', outputnode, 'brain_mask_t1')
    workflow.connect(t1_mni_node, t1_mni_file, outputnode, 't1_mni')
    workflow.connect(copy_t1_nat, 'output_file', outputnode, 't1_nat')
    return(workflow)


