# vim: set tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
# vim: filetype plugin indent on

import os
import sys
import argparse
import commands
import shutil
import tempfile
import time
import pyminc.volumes.factory as pyminc
import numpy as np
import pdb

from optparse import OptionParser
from optparse import OptionGroup
import nipype.interfaces.minc as minc
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.utility as niu
from nipype.interfaces.utility import Rename

from Extra.conversion import  nii2mncCommand

from Masking import masking as masking
import Registration.registration as reg
import Initialization.initialization as init
import Partial_Volume_Correction.pvc as pvc 
import Results_Report.results as results
import Tracer_Kinetic.tka as tka
from Tracer_Kinetic import reference_methods, ecat_methods
import Quality_Control.qc as qc
import Test.test_group_qc as tqc
from Masking import surf_masking
"""
.. module:: scanLevel
    :platform: Unix
    :synopsis: Module to launch scan level analysis.
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""

def set_datasource_inputs(opts):
    """Setup data source based on user-options.

    :param opts: User-defined options
        :type opts: argparser
    :returns:  
        infields_list, base_outputs, base_label, base_transforms, base_images, template_args_dict, field_template_dict, pvc_template_string, tka_template_string, results_template_string 
    """

    # Set the inputs for the labeled image for datasource.
    # This is a bit complicated because there are many possible ways in which the 
    # user can define these labeled images. The simplest approach is to use a 
    # labeled image in T1 native space. A more complicated approach is to to use an
    # atlas defined in some other space, in which case we need both the labeled image
    # and the template image on which the labeled image is defined. 

    # Set PVC label DataGrabber inputs:
    [ pvc_label_img_string, pvc_label_img_variables  ] = set_label_parameters(opts.pvc_label_level, 'pvc_img_string', opts.img_ext )
    # Set quantification label DataGrabber inputs
    [ tka_label_img_string, tka_label_img_variables  ] = set_label_parameters(opts.tka_label_level,  'tka_img_string', opts.img_ext )
    # Set results label DataGrabber inputs
    [ results_label_img_string, results_label_img_variables  ] = set_label_parameters(opts.results_label_level,  'results_img_string', opts.img_ext )

    # Set the inputs for the template image for DataGrabber
    # Set the inputs for the PVC template image
    [ pvc_label_template_string, pvc_label_template_variables  ] = set_label_parameters(opts.pvc_label_level,  'pvc_template_string',opts.img_ext )
    # Set the inputs for the quantification template image
    [ tka_label_template_string, tka_label_template_variables  ] = set_label_parameters(opts.tka_label_level,  'tka_template_string', opts.img_ext )
    # Set the inputs for the results template image
    [ results_label_template_string, results_label_template_variables  ] = set_label_parameters(opts.results_label_level,  'results_template_string', opts.img_ext )

    
    if opts.pvc_label_img[1] == None: pvc_label_img_string = opts.sourceDir + os.sep + pvc_label_img_string 
    if opts.tka_label_img[1] == None: tka_label_img_string = opts.sourceDir + os.sep + tka_label_img_string 
    if opts.results_label_img[1] == None: results_label_img_string = opts.sourceDir + os.sep + results_label_img_string 

    #List of variables used to identify PET image
    infields_list=['sid', 'ses', 'task', 'acq', 'rec']
    #List of strings that define the variable names for label images
    base_label=['pvc_label_img','tka_label_img', 'results_label_img' ] 
    #List of structural images that are used by APPIAN
    base_images=['nativeT1',  'nativeT1nuc',  'T1Tal',  'brainmaskTal',  'headmaskTal',  'clsmask', 'segmentation', 'pet']
    #List of transformation files from T1 native space to MNI152 space. 
    #First is a linear transform, second is a non-linear transform.
    base_transforms=[ 'xfmT1MNI' ,'xfmT1MNInl']
    base_outputs = base_images + base_transforms  + base_label 
    
    #Dictionary for basic structural inputs to DataGrabber
    field_template_dict =dict(
        nativeT1=opts.sourceDir+os.sep+'sub-%s/_ses-%s/anat/sub-%s_ses-%s*T1w.'+opts.img_ext,
        nativeT1nuc=opts.sourceDir+os.sep+'sub-%s/_ses-%s/anat/sub-%s_ses-%s*T1w_nuc.*'+opts.img_ext, 
        T1Tal=opts.sourceDir+os.sep+'sub-%s/_ses-%s/anat/sub-%s_ses-%s*_T1w_space-mni.*'+opts.img_ext,
        xfmT1MNI=opts.sourceDir+os.sep+'sub-%s/_ses-%s/transforms/sub-%s_ses-%s*target-MNI_affine.xfm',
        xfmT1MNInl=opts.sourceDir+os.sep+'sub-%s/_ses-%s/transforms/sub-%s_ses-%s*target-MNI_warp.xfm',
        brainmaskTal=opts.sourceDir+os.sep+'sub-%s/_ses-%s/anat/sub-%s_ses-%s*_space-mni_brainmask.*'+opts.img_ext,
        headmaskTal=opts.sourceDir+os.sep+'sub-%s/_ses-%s/anat/sub-%s_ses-%s*_space-mni_skullmask.*'+opts.img_ext,
        clsmask=opts.sourceDir+os.sep+'sub-%s/_ses-%s/anat/sub-%s_ses-%s*space-mni_variant-cls_dtissue.*'+opts.img_ext,
        segmentation=opts.sourceDir+os.sep+'sub-%s/_ses-%s/anat/sub-%s_ses-%s*_space-mni_variant-seg_dtissue.*'+opts.img_ext,
        pet=opts.sourceDir+os.sep+'sub-%s/_ses-%s/pet/sub-%s_ses-%s_task-%s_acq-%s_rec-%s_pet.*'+opts.img_ext,
        #PVC label string 
        pvc_label_img = pvc_label_img_string,
        #TKA label string
        tka_label_img = tka_label_img_string,
        #Results label string
        results_label_img = results_label_img_string,
    )

    template_args_dict = dict(
        nativeT1=[[ 'sid', 'ses', 'sid', 'ses']],
        nativeT1nuc=[[ 'sid', 'ses', 'sid', 'ses']],
        T1Tal=[[ 'sid', 'ses', 'sid', 'ses']],
        xfmT1MNI=[[ 'sid', 'ses', 'sid', 'ses']],
        xfmT1MNInl=[[ 'sid', 'ses', 'sid', 'ses']],
        brainmaskTal=[[ 'sid', 'ses', 'sid', 'ses']],
        headmaskTal=[[ 'sid', 'ses', 'sid', 'ses']],
        clsmask=[[ 'sid', 'ses', 'sid', 'ses']],
        segmentation=[[ 'sid', 'ses', 'sid', 'ses']],
        pet = [['sid', 'ses', 'sid', 'ses', 'task', 'acq', 'rec']],
        pvc_label_img = pvc_label_img_variables,
        tka_label_img = tka_label_img_variables,
        results_label_img = results_label_img_variables,
    )

    # If not pvc_label_img[1] == None then that means we are using a labeled image 
    # requires a corresponding template. Otherwise, the image is defined in T1 native or
    # MNI 152. The same applies for PVC and quantification stage
    if not opts.pvc_label_img[1] == None: 
        #Assign pvc input to datasource
        pvc_template_string, field_template_dict, template_args_dict, base_label, infields_list = assign_datasource_values(opts.pvc_label_img, field_template_dict, template_args_dict, base_label, infields_list, pvc_label_template_string, pvc_label_template_variables, 'pvc_label_template' , 'pvc_template_string'  )
        base_outputs.append('pvc_label_template')
    else : pvc_template_string = ''
    
    if not opts.tka_label_img[1] == None: 
        #Assign tka input to datasource
        tka_template_string, field_template_dict, template_args_dict, base_label, infields_list = assign_datasource_values(opts.tka_label_img, field_template_dict, template_args_dict, base_label, infields_list, tka_label_template_string, tka_label_template_variables, 'tka_label_template' , 'tka_template_string'  )
        base_outputs.append('tka_label_template')
    else : tka_template_string = ''

    if not opts.results_label_img[1] == None: 
        #Assign results input to datasource
        results_template_string, field_template_dict, template_args_dict, base_label, infields_list = assign_datasource_values(opts.results_label_img, field_template_dict, template_args_dict, base_label, infields_list, results_label_template_string, results_label_template_variables, 'results_label_template' , 'results_template_string'  )
        base_outputs.append('results_label_template')
    else : results_template_string = ''

    return infields_list, base_outputs, base_label, base_transforms, base_images, template_args_dict, field_template_dict, pvc_template_string, tka_template_string, results_template_string 
 

def assign_datasource_values(label_img, field_template_dict, template_args_dict, base_label, infields_list, label_template_string, label_template_variables, str1, str2 ):
    """
    This function sets up the strings and dictionaries that are then used to create the appropriate Nipype DataGrabber. 

    :param label_img: label_img
    :param field_template_dict: Dictionary of strings for template 
    :param template_args_dict: Dictionary of variable arguments for templates
    :param base_label: base_label 
    :param infields_list: infields_list
    :param label_template_string: label_template_string
    :param label_template_variables: label_template_variables
    :param str1: str1
    :param str2: str2
    """
    template_string = label_img[1]
    field_template_dict= dict(field_template_dict.items() + [[str1, label_template_string]] )
    template_args_dict = dict( template_args_dict.items() + [[str1, label_template_variables]] )
    base_label.append(str1)
    infields_list.append(str2)
    return template_string, field_template_dict, template_args_dict, base_label, infields_list 


def printOptions(opts,subject_ids,session_ids,task_ids):
    """
    Print basic options input by user

    :param opts: User-defined options.
    :param subject_ids: Subject IDs
    :param session_ids: Session variable IDs
    :param task_ids: Task variable IDs

    """
    uname = os.popen('uname -s -n -r').read()
    print "\n"
    print "* Pipeline started at "+time.strftime("%c")+"on "+uname
    print "* Command line is : \n "+str(sys.argv)+"\n"
    print "* The source directory is : "+opts.sourceDir
    print "* The target directory is : "+opts.targetDir+"\n"
    print "* Data-set Subject ID(s) is/are : "+str(', '.join(subject_ids))+"\n"
    #   print "* PET conditions : "+ ','.join(opts.condiList)+"\n"
    print "* Sessions : ", session_ids, "\n"
    print "* Tasks : " , task_ids , "\n"

def set_label_parameters(level, var , ext ):
    """
    Set the label_string and label_variables for the datasource
    
    :param level: <level> equals "atlas" if a filepath is given, otherwise uses BIDS label-string
    :param var: String variable name for image type
    :param ext: File Extension
    :type level: String
    :type var: String
    :type ext: String

    :returns [label_string, label_variables]: List with two elements: string used to identify image, a list of variables that are used to "fill-in" label_string
    """
    if level  == "atlas": 
        label_string = "%s"
        label_variables = [[ var ]]
    else: 
        label_string = 'sub-%s/_ses-%s/anat/sub-%s_ses-%s*%s*' + ext
        label_variables = [['sid', 'ses', 'sid', 'ses', var] ]
    return [ label_string, label_variables ]


def run_scan_level(opts,args): 
    """
    This is the main function for setting up and then running the scanLevel analysis. It first uses <preinfosource> to identify which scans exist for the which combination of  task, session, and subject IDs. This is stored in <valid_args>, which is then passed to inforsource. Infosource iterates over the valid subjects and uses DataGrabber to find the input files for each of these subjects. Depdning on the user-options defined in <opts>, for each scan PET-T1 co-registration, partial-volume correction, tracer kinetic analysis and results reporting are performed. 

    .. aafig::
        
       +-------------+
       |Preinfosource| 
       +-----+-------+
             |
             |
        +----+-----+
        |Infosource|
        +-+---+---++
          |   |   |
          |   |   |
          |   |   |
         +++ +++ +++
         |D| |D| |D| = "DataGrabber"
         +++ +++ +++
          |   |   |
         +++ +++ +++
         |I| |I| |I| = "Initialization"
         +++ +++ +++
          |   |   |
         +++ +++ +++
         |M| |M| |M| = "Masking"
         +++ +++ +++
          |   |   |
         +++ +++ +++
         |C| |C| |C| = "Coregistration"
         +++ +++ +++
          |   |   |
         +++ +++ +++
         |P| |P| |P| = "Partial volume correction"
         +++ +++ +++
          |   |   |
         +++ +++ +++
         |T| |T| |T| = "Tracer kinetic analysis"
         +++ +++ +++
          |   |   |
         +++ +++ +++
         |R| |R| |R| = "Results report"
         +++ +++ +++

    :param opts: User-defined options
    :type opts: argparser
    :param args: List of subjects
    :type args: list

    :returns int: Return code 0 == success
    """

    if args:
        subjects_ids = args
    else:
        print "\n\n*******ERROR********: \n     The subject IDs are not listed in the command-line \n********************\n\n"
        sys.exit(1)
    #If the sessionList has been defined as a "," separated list, split it into list
    if isinstance(opts.sessionList, str):
        opts.sessionList=opts.sessionList.split(',')
    session_ids=opts.sessionList
    #If the taskList has been defined as a "," separated list, split it into list
    if isinstance(opts.taskList, str):
        opts.taskList=opts.taskList.split(',')
    task_ids=opts.taskList

    ###Define args with exiting subject and condition combinations
    valid_args=init.gen_args(opts, session_ids, task_ids, opts.acq, opts.rec, args)
    preinfosource = pe.Node(interface=util.IdentityInterface(fields=['args','results_labels','tka_labels','pvc_labels', 'pvc_erode_times', 'tka_erode_times', 'results_erode_times']), name="preinfosource")
    preinfosource.iterables = ( 'args', valid_args )
    preinfosource.inputs.results_labels = opts.results_labels
    preinfosource.inputs.tka_labels = opts.tka_labels
    preinfosource.inputs.pvc_labels = opts.pvc_labels 
    preinfosource.inputs.results_erode_times = opts.results_erode_times
    preinfosource.inputs.tka_erode_times = opts.tka_erode_times
    preinfosource.inputs.pvc_erode_times = opts.pvc_erode_times
    ###Infosource###
    infosource = pe.Node(interface=init.SplitArgsRunning(), name="infosource")

    workflow = pe.Workflow(name=opts.preproc_dir)
    workflow.base_dir = opts.targetDir

    #################
    ###Datasources###
    #################
    #Subject ROI datasource
    if opts.arterial:
        datasourceArterial = pe.Node( interface=nio.DataGrabber(infields=['sid', 'ses', 'task', 'acq' ],  outfields=['arterial_file'], raise_on_empty = True, sort_filelist=False), name="datasourceArterial")
        datasourceArterial.inputs.base_directory = opts.sourceDir
        datasourceArterial.inputs.template = '*'
        datasourceArterial.inputs.acq=opts.acq
        datasourceArterial.inputs.field_template = dict(arterial_file='sub-%s/_ses-%s/pet/sub-%s_ses-%s_task-%s_acq-%s_*.dft')
        datasourceArterial.inputs.template_args = dict(arterial_file=[['sid','ses', 'sid', 'ses', 'task', 'acq']])
        workflow.connect([  (infosource, datasourceArterial, [('sid', 'sid')]), 
                            (infosource, datasourceArterial, [('task', 'task')]),
                            (infosource, datasourceArterial, [('ses', 'ses')])
                            ])
    
    infields_list, base_outputs, base_label, base_transforms, base_images, template_args_dict, field_template_dict, pvc_template_string, tka_template_string, results_template_string = set_datasource_inputs(opts)

    datasource = pe.Node( interface=nio.DataGrabber(infields=infields_list, outfields=base_outputs, raise_on_empty=True, sort_filelist=False), name="datasource")
    
    if not opts.pvc_label_img[1] == None: 
        datasource.inputs.pvc_template_string=pvc_template_string 
    if not opts.tka_label_img[1] == None: 
        datasource.inputs.tka_template_string=tka_template_string 
    if not opts.results_label_img[1] == None: 
        datasource.inputs.results_template_string=results_template_string
    
    datasource.inputs.tka_img_string = opts.tka_label_img[0]
    datasource.inputs.results_img_string = opts.results_label_img[0]
    datasource.inputs.pvc_img_string = opts.pvc_label_img[0]
    datasource.inputs.base_directory = '/' # opts.sourceDir
    datasource.inputs.template = '*'
    ### Variables to use from template
    datasource.inputs.acq=opts.acq
    datasource.inputs.rec=opts.rec
    ### Templates for input
    datasource.inputs.field_template = field_template_dict
    ### Templates for template args
    datasource.inputs.template_args = template_args_dict 

    if opts.use_surfaces:
        datasourceSurf = pe.Node( interface=nio.DataGrabber(infields=['sid', 'ses', 'task', 'acq', 'rec'], outfields=[ 'gm_surf', 'wm_surf', 'mid_surf'], raise_on_empty=True, sort_filelist=False), name="datasourceSurf")
        datasourceSurf.inputs.base_directory = opts.sourceDir
        datasourceSurf.inputs.template = '*'
        datasourceSurf.inputs.acq=opts.acq
        datasourceSurf.inputs.rec=opts.rec
        datasourceSurf.inputs.field_template =dict(
            #gm_surf="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_pial."+opts.surf_ext,
            #wm_surf="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_smoothwm."+opts.surf_ext,
            mid_surf="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_midthickness."+opts.surf_ext,
            #FIXME Not sure what BIDS spec is for a surface mask
            #surf_mask="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_midthickness_mask.txt" 
        )
        datasourceSurf.inputs.template_args = dict(
            #gm_surf = [['sid', 'ses', 'sid', 'ses', 'task']],
            #wm_surf = [['sid', 'ses', 'sid', 'ses', 'task']],
            mid_surf = [['sid', 'ses', 'sid', 'ses', 'task']]
        )
        workflow.connect([
                (infosource, datasourceSurf, [('sid', 'sid')]),
                (infosource, datasourceSurf, [('cid', 'cid')]),
                (infosource, datasourceSurf, [('task', 'task')]),
                (infosource, datasourceSurf, [('ses', 'ses')]),
                 ])

    #############################################
    ### Define Workflow and basic connections ###
    #############################################
    workflow.connect(preinfosource, 'args', infosource, "args")
    workflow.connect([
                    (infosource, datasource, [('sid', 'sid')]),
                    (infosource, datasource, [('cid', 'cid')]),
                    (infosource, datasource, [('task', 'task')]),
                    (infosource, datasource, [('ses', 'ses')]),
                     ])

    ############################################################
    ### Convert NII to MINC if necessary.                      # 
    ### Pass to identity node that serves as pseudo-datasource #
    ############################################################
    datasourceMINC = pe.Node(niu.IdentityInterface(fields=base_outputs), name='datasourceMINC')
    for i in range(len(base_transforms)):
        print base_transforms[i]
        workflow.connect(datasource, base_transforms[i] , datasourceMINC, base_transforms[i] )

    for i in range(len(base_images)):
        if opts.img_ext == 'nii':
            nii2mncNode = pe.Node(interface=nii2mncCommand(), name=base_images[i]+'_nii2mncNode')
            workflow.connect(datasource, base_images[i], nii2mncNode, "in_file")
            workflow.connect(nii2mncNode, 'out_file', datasourceMINC, base_images[i])
        else:
            workflow.connect(datasource, base_images[i], datasourceMINC, base_images[i])
        i += 1
    t1_type='nativeT1nuc'
    if opts.coregistration_target_image == 'raw':
        t1_type='nativeT1'
    
    ##############
    ###Datasink###
    ##############
    datasink=pe.Node(interface=nio.DataSink(), name="output")
    datasink.inputs.base_directory= opts.targetDir + '/' 
    datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]

    ###Set the appropriate nodes and inputs for desired "analysis_level"
    wf_pet2mri=reg.get_workflow("pet-coregistration", infosource, opts)
    wf_masking=masking.get_workflow("masking", infosource, datasink, opts)
    if opts.analysis_space == 'icbm152':
        labelSpace='MNI'
        pet_input_node=wf_pet2mri
        pet_input_file='outputnode.petmni_img_4d'
        pet_mask_node=wf_masking
        pet_results_mask_file='resultsLabels.LabelsMNI'
        pet_pvc_mask_file='pvcLabels.LabelsMNI'
        t1="T1Tal"
    elif opts.analysis_space == 'pet':
        labelSpace='PET'
        pet_input_node=wf_init_pet
        pet_input_file='outputnode.pet_center'
        pet_mask_node=wf_pet2mri
        pet_results_mask_file="outputnode.results_label_img_pet"
        pet_pvc_mask_file="outputnode.pvc_label_img_pet"
        t1=t1_type
    elif opts.analysis_space == 't1':
        labelSpace='T1'
        pet_input_node=wf_pet2mri
        pet_input_file='outputnode.petmri_img_4d'
        pet_mask_node=wf_masking
        pet_results_mask_file='resultsLabels.LabelsT1'
        pet_pvc_mask_file='pvcLabels.LabelsT1'
        t1=t1_type

    ###################
    # PET prelimaries #
    ###################
    wf_init_pet=init.get_workflow("prelimaries", infosource, datasink, opts)
    workflow.connect(datasourceMINC, 'pet', wf_init_pet, "inputnode.pet")
        
    ###########
    # Masking #
    ###########
    workflow.connect(datasourceMINC, t1_type, wf_masking, "inputnode.nativeT1")
    workflow.connect(datasourceMINC, 'xfmT1MNI', wf_masking, "inputnode.LinT1MNIXfm")
    workflow.connect(datasourceMINC, 'T1Tal', wf_masking, "inputnode.mniT1")
    workflow.connect(datasourceMINC, 'brainmaskTal', wf_masking, "inputnode.brainmask")
    if not opts.nopvc:
        workflow.connect(preinfosource, 'pvc_labels', wf_masking, "inputnode.pvc_labels")
        workflow.connect(datasource, "pvc_label_img", wf_masking, "inputnode.pvc_label_img")
    if opts.tka_method != None :
        workflow.connect(preinfosource, 'tka_labels', wf_masking, "inputnode.tka_labels")
        workflow.connect(datasource, "tka_label_img", wf_masking, "inputnode.tka_label_img")
    workflow.connect(preinfosource, 'results_labels', wf_masking, "inputnode.results_labels")
    workflow.connect(preinfosource, 'pvc_erode_times', wf_masking, "inputnode.pvc_erode_times")
    workflow.connect(preinfosource, 'tka_erode_times', wf_masking, "inputnode.tka_erode_times")
    workflow.connect(preinfosource, 'results_erode_times', wf_masking, "inputnode.results_erode_times")
    workflow.connect(datasource, "headmaskTal", wf_masking, "inputnode.headmask")
    workflow.connect(datasource, "results_label_img", wf_masking, "inputnode.results_label_img")
    workflow.connect(wf_init_pet, 'outputnode.pet_volume', wf_masking, "inputnode.pet_volume")
    workflow.connect(wf_init_pet, 'outputnode.pet_header_json', wf_masking, "inputnode.pet_header_json")

    if not opts.pvc_label_img[1] == None: 
        workflow.connect(datasource, "pvc_label_template", wf_masking, "inputnode.pvc_label_template")
    if not opts.tka_label_img[1] == None: 
        workflow.connect(datasource, "tka_label_template", wf_masking, "inputnode.tka_label_template")
    if not opts.results_label_img[1] == None: 
        workflow.connect(datasource, "results_label_template", wf_masking, "inputnode.results_label_template")
    
    ##################
    # Coregistration #
    ##################
    workflow.connect(wf_init_pet, 'outputnode.pet_volume', wf_pet2mri, "inputnode.pet_volume")
    workflow.connect(wf_init_pet, 'outputnode.pet_center', wf_pet2mri, "inputnode.pet_volume_4d")
    workflow.connect(wf_masking, 'brainmask.LabelsT1', wf_pet2mri, "inputnode.t1_brain_mask")
    workflow.connect(datasourceMINC, t1_type , wf_pet2mri,"inputnode.nativeT1nuc")
    workflow.connect(datasourceMINC, 'T1Tal', wf_pet2mri,"inputnode.T1Tal")
    workflow.connect(datasourceMINC, "xfmT1MNI", wf_pet2mri,"inputnode.xfmT1MNI")
    workflow.connect(wf_masking,'pet_brainmask.out_file',wf_pet2mri, "inputnode.pet_headMask")
    workflow.connect(wf_masking, 'headmask.LabelsT1', wf_pet2mri, "inputnode.t1_headMask")
    workflow.connect(wf_masking, 'resultsLabels.LabelsT1', wf_pet2mri, "inputnode.results_label_img_t1")  
    workflow.connect(wf_init_pet, 'outputnode.pet_header_json', wf_pet2mri, 'inputnode.header')
    if opts.tka_method != None :
        workflow.connect(wf_masking, 'tkaLabels.LabelsT1', wf_pet2mri, "inputnode.tka_label_img_t1")
    if not opts.nopvc:
        workflow.connect(wf_masking, 'pvcLabels.LabelsT1', wf_pet2mri, "inputnode.pvc_label_img_t1")
    if opts.test_group_qc :
        misregistration = pe.Node(interface=util.IdentityInterface(fields=['error']), name="misregistration")
        misregistration.iterables = ('error',tqc.errors)
        workflow.connect(misregistration, 'error', wf_pet2mri, "inputnode.error")

    out_node_list = [wf_pet2mri] 
    out_img_list = [pet_input_file]
    out_img_dim = ['4']
    
    if opts.use_surfaces:
        ######################
        # Transform Surfaces #
        ######################
        surf_wf = surf_masking.get_surf_workflow('surface_transform', infosource, datasink, opts)
        workflow.connect(datasourceMINC, 'xfmT1MNI', surf_wf, 'inputnode.T1MNI')
        workflow.connect(wf_masking, 'invert_MNI2T1.output_file',  surf_wf, 'inputnode.MNIT1')
        workflow.connect(wf_pet2mri, "outputnode.petmri_xfm",  surf_wf, 'inputnode.PETT1')
        workflow.connect(wf_pet2mri, "outputnode.petmri_xfm_invert", surf_wf, 'inputnode.T1PET')
        workflow.connect(datasourceSurf, 'mid_surf', surf_wf, 'inputnode.obj_file')
        workflow.connect(wf_masking, 'resultsLabels.Labels'+labelSpace, surf_wf, 'inputnode.vol_file')

    #############################
    # Partial-volume correction #
    #############################
    if not opts.nopvc :
        pvc_wf = pvc.get_pvc_workflow("pvc", infosource, datasink, opts) 
        workflow.connect(pet_input_node, pet_input_file, pvc_wf, "inputnode.in_file") #CHANGE
        workflow.connect(pet_mask_node, pet_pvc_mask_file, pvc_wf, "inputnode.mask_file") #CHANGE
        workflow.connect(wf_init_pet, 'outputnode.pet_header_json', pvc_wf, "inputnode.header") #CHANGE

        out_node_list += [pvc_wf]
        out_img_list += ['outputnode.out_file']
        out_img_dim += ['4']

    ###########################
    # Tracer kinetic analysis #
    ###########################
    if not opts.tka_method == None:
        if not opts.nopvc: 
            tka_target_wf = pvc_wf
            tka_target_img='outputnode.out_file'
        else : 
            tka_target_wf = pet_input_node # #CHANGE
            tka_target_img= pet_input_file # ##CHANGE
                
        tka_wf=tka.get_tka_workflow("tka", opts)
        header_type='outputnode.pet_header_json'
        if opts.tka_method in ["suvr"] : header_type = 'outputnode.pet_header_dict'
        workflow.connect(wf_init_pet, header_type, tka_wf, "inputnode.header")
        if opts.tka_method in ecat_methods : 
           workflow.connect(pet_mask_node, pet_pvc_mask_file, tka_wf, 'inputnode.like_file')
        workflow.connect(infosource, 'sid', tka_wf, "inputnode.sid")
        #if opts.tka_method in reference_methods:
        workflow.connect(pet_mask_node, pet_results_mask_file, tka_wf, "inputnode.mask") 
        workflow.connect(tka_target_wf, tka_target_img, tka_wf, "inputnode.in_file")
        if opts.arterial :
            workflow.connect(datasourceArterial, 'arterial_file', tka_wf, "inputnode.reference")
        elif opts.tka_method in reference_methods + ['suvr']: #FIXME should not just add suvr like this 
            workflow.connect(wf_masking, 'tkaLabels.LabelsMNI', tka_wf, "inputnode.reference")
        if opts.tka_type=="ROI":
            workflow.connect(tka_wf, "outputnode.out_fit_file", datasink, 'tka')
        
        out_node_list += [tka_wf]
        out_img_list += ['outputnode.out_file']
        out_img_dim += ['3']
    
    #######################################
    # Connect nodes for reporting results #
    #######################################
    #Results report for PET
    if not opts.no_results_report:
        for node, img, dim in zip(out_node_list, out_img_list, out_img_dim):
            print "outputnode", node.name, "image name", img
            node_name="results_" + node.name 
            resultsReport = pe.Node(interface=results.resultsCommand(), name=node_name)
            resultsReport.inputs.dim = dim
            resultsReport.inputs.node = node.name
            workflow.connect(infosource, 'sid', resultsReport, "sub")
            workflow.connect(infosource, 'ses', resultsReport, "ses")
            workflow.connect(infosource, 'task', resultsReport, "task")
            workflow.connect(wf_init_pet, 'outputnode.pet_header_dict', resultsReport, "header")
            workflow.connect(wf_masking, 'resultsLabels.Labels'+labelSpace, resultsReport, 'mask')
            workflow.connect(node, img, resultsReport, 'in_file')
            workflow.connect(node, img, datasink, node.name)

            if opts.use_surfaces:
                node_name="results_surf_" + node.name 
                resultsReportSurf = pe.Node(interface=results.resultsCommand(), name=node_name)
                resultsReportSurf.inputs.dim = dim
                resultsReportSurf.inputs.node = node.name
                workflow.connect(infosource, 'sid', resultsReportSurf, "sub")
                workflow.connect(infosource, 'ses', resultsReportSurf, "ses")
                workflow.connect(infosource, 'task', resultsReportSurf, "task")
                workflow.connect(wf_init_pet, 'outputnode.pet_header_dict', resultsReportSurf, "header")
                workflow.connect(node, img, resultsReportSurf, 'in_file')
                workflow.connect(surf_wf, 'outputnode.surface', resultsReportSurf, "surf_mesh")
                workflow.connect(surf_wf, 'outputnode.mask', resultsReportSurf, 'surf_mask')
    
    ############################
    # Subject-level QC Metrics #
    ############################
    if opts.group_qc or opts.test_group_qc :
        #Automated QC: PET to MRI linear coregistration 
        distance_metricNode=pe.Node(interface=qc.coreg_qc_metricsCommand(),name="coreg_qc_metrics")
        workflow.connect(wf_pet2mri, 'outputnode.petmri_img',  distance_metricNode, 'pet')
        workflow.connect(wf_pet2mri, 'outputnode.pet_brain_mask', distance_metricNode, 'pet_brain_mask')
        workflow.connect(datasourceMINC, t1_type,  distance_metricNode, 't1')
        workflow.connect(wf_masking, 'brainmask.LabelsT1', distance_metricNode, 't1_brain_mask')
        workflow.connect(infosource, 'ses', distance_metricNode, 'ses')
        workflow.connect(infosource, 'task', distance_metricNode, 'task')
        workflow.connect(infosource, 'sid', distance_metricNode, 'sid')

        if not opts.nopvc:
            #Automated QC: PVC 
            pvc_qc_metricsNode=pe.Node(interface=qc.pvc_qc_metrics(),name="pvc_qc_metrics")
            pvc_qc_metricsNode.inputs.fwhm = opts.scanner_fwhm
            workflow.connect(pet_input_node, pet_input_file, pvc_qc_metricsNode, 'pve') ##CHANGE
            workflow.connect(tka_target_wf, tka_target_img, pvc_qc_metricsNode, 'pvc'  )
            workflow.connect(infosource, 'sid', pvc_qc_metricsNode, "sub")
            workflow.connect(infosource, 'ses', pvc_qc_metricsNode, "ses")
            workflow.connect(infosource, 'task', pvc_qc_metricsNode, "task")

    #vizualization graph of the workflow
    #workflow.write_graph(opts.targetDir+os.sep+"workflow_graph.dot", graph2use = 'exec')

    printOptions(opts,subjects_ids,session_ids,task_ids)
    #run the work flow
    if opts.num_threads > 1 :
        plugin_args = {'n_procs' : opts.num_threads,
                   #'memory_gb' : num_gb, 'status_callback' : log_nodes_cb
                      }
        workflow.run(plugin='MultiProc', plugin_args=plugin_args)
    else : 
        workflow.run()

    return 0


