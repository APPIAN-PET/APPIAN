#--user-brainmask --user-brainmask  vim: set tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
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
from MRI import normalize
"""
.. module:: scanLevel
    :platform: Unix
    :synopsis: Module to launch scan level analysis.
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""


def set_base(datasource,  task_list, acq, rec, sourceDir, img_ext ):
    pet_str = sourceDir+os.sep+'sub-%s/*ses-%s/pet/sub-%s_ses-%s'
    pet_list = ['sid', 'ses', 'sid', 'ses']
    t1_list =  [ 'sid', 'ses', 'sid', 'ses']
    t1_str=sourceDir+os.sep+'sub-%s/*ses-%s/anat/sub-%s_ses-%s'
    if task_list != ['']: 
        pet_str = pet_str + '_task-%s'
        t1_str = t1_str + '_task-%s'
        pet_list += task_list
        t1_list += task_list
    if acq != '' :
        pet_str = pet_str + '_acq-%s'
        pet_list += ['acq']  
        infields_list += [ 'acq' ] 
    if rec != '':
        pet_str = pet_str + '_rec-%s'
        pet_list += ['rec']
        infields_list += ['rec']
    pet_str = pet_str + '*_pet.'+img_ext
    
    #Dictionary for basic structural inputs to DataGrabber
    field_template = dict(
        nativeT1 = t1_str + '_*T1w.'+img_ext,
        pet=pet_str
    )

    template_args = dict(
        nativeT1=[t1_list],
        pet=[pet_list]
    )

    datasource.inputs.field_template.update(field_template)
    datasource.inputs.template_args.update(template_args)

    return datasource



def set_label(datasource, img, template, task_list, label_img, template_img, sourceDir, img_ext):
    '''
    set_labels(datasource, opts.pvc_label_img[0],  opts.pvc_label_img[1], [],  )
    '''
    field_template={}
    template_args={}

    if template == None :
        label_img_template=sourceDir+os.sep+'*sub-%s/*ses-%s/anat/sub-%s_ses-%s'

        template_args[label_img]=[['sid', 'ses'] ] 
        if task_list != [''] :
            label_img_template += '_task-%s'
            template_args[label_img][0] +=  task_list  
        label_img_template +='_*'+img+'T1w.'+img_ext
        field_template[label_img] = label_img_template

    else :
        field_template[label_img] = "*"
        field_template[template_img] = img
        field_template[template_img] = "*"
        field_template[template_img] = template
        
        template_args[label_img]=['']  
        template_args[template_img]=['']  
        datasource.inputs.out_fields += [template_img]

    datasource.inputs.field_template.update( field_template  )
    datasource.inputs.template_args.update( template_args )
    return datasource




def set_transform(datasource, task_list, sourceDir):
    field_template={}
    template_args={}
    label_template = sourceDir+os.sep+'sub-%s/*ses-%s/transforms/sub-%s_ses-%s'
    template_args["xfmT1MNI"] = [['sid', 'ses', 'sid', 'ses' ]]
    if task_list != [''] :
        label_template = label_template + "_task-%s"
        template_args["xfmT1MNI"][0] += task_list
    label_template = label_template + '*target-MNI_affine.xfm'
    
    field_template["xfmT1MNI"] = label_template

    #template_args["xfmT1MNI"][0] = template_args
    
    datasource.inputs.field_template.update(field_template)
    datasource.inputs.template_args.update(template_args)

    return datasource

def set_brain_mask(datasource, task_list, coregistration_brain_mask, sourceDir, img_ext) :
    field_template={}
    template_args={}

    brain_mask_template = sourceDir+os.sep+'sub-%s/*ses-%s/anat/sub-%s_ses-%s*'
    template_args["brain_mask_mni"]=[['sid' ,'ses','sid', 'ses']]

    if task_list != [''] :
        brain_mask_template = brain_mask_template + "_task-%s"
        template_args["brain_mask_mni"][0] += task_list

    brain_mask_template = brain_mask_template + "_T1w_space-mni"

    if not coregistration_brain_mask : 
       brain_mask_template = brain_mask_template + '_skullmask.*'+img_ext
    else :
        brain_mask_template = brain_mask_template + '_brainmask.*'+img_ext

    field_template["brain_mask_mni"] = brain_mask_template
    
    datasource.inputs.field_template.update(field_template)
    datasource.inputs.template_args.update(template_args)


    return datasource


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


def printOptions(opts,subject_ids,session_ids,task_list):
    """
    Print basic options input by user

    :param opts: User-defined options.
    :param subject_ids: Subject IDs
    :param session_ids: Session variable IDs
    :param task_list: Task variable IDs

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
    print "* Tasks : " , task_list , "\n"

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
        label_string = 'sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s*%s*' + ext
        label_variables = [['sid', 'ses', 'sid', 'ses', 'task', var] ]
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
         |I| |I| |I| = "PET Initialization"
         +++ +++ +++
          |   |   |
         +++ +++ +++
         |C| |C| |C| = "Coregistration"
         +++ +++ +++
          |   |   |
         +++ +++ +++
         |M| |M| |M| = "Masking"
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
    task_list=opts.taskList

    ###Define args with exiting subject and condition combinations
    valid_args=init.gen_args(opts, session_ids, task_list, opts.acq, opts.rec, args)
    
    #####################
    ### Preinfosource ###
    #####################
    preinfosource = pe.Node(interface=util.IdentityInterface(fields=['args','results_labels','tka_labels','pvc_labels', 'pvc_erode_times', 'tka_erode_times', 'results_erode_times']), name="preinfosource")
    preinfosource.iterables = ( 'args', valid_args )
    preinfosource.inputs.results_labels = opts.results_labels
    preinfosource.inputs.tka_labels = opts.tka_labels
    preinfosource.inputs.pvc_labels = opts.pvc_labels 
    preinfosource.inputs.results_erode_times = opts.results_erode_times
    preinfosource.inputs.tka_erode_times = opts.tka_erode_times
    preinfosource.inputs.pvc_erode_times = opts.pvc_erode_times

    ##################
    ### Infosource ###
    ##################
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
    
    ### Use DataGrabber to get key input files
    infields_list = []
    base_outputs  = ['nativeT1',  'pet','xfmT1MNI','brain_mask_mni', "pvc_label_img", "tka_label_img", "results_label_img", "pvc_template_img", "tka_template_img", "results_template_img" ]

    datasource = pe.Node( interface=nio.DataGrabber(infields=infields_list, outfields=base_outputs, raise_on_empty=True, sort_filelist=False), name="datasource")
    datasource.inputs.template = '*'
    datasource.inputs.base_directory = '/' # opts.sourceDir
    datasource.inputs.acq=opts.acq
    datasource.inputs.rec=opts.rec   

    # Set label datasource
    datasource.inputs.field_template = {}
    datasource.inputs.template_args = {}
    
    datasource = set_base(datasource,  opts.taskList, opts.acq, opts.rec, opts.sourceDir, opts.img_ext )
    if opts.pvc_label_type != "internal_cls" :
        datasource = set_label(datasource, opts.pvc_label_img[0], opts.pvc_label_img[1], opts.taskList, 'pvc_label_img', 'pvc_label_template', opts.sourceDir, opts.img_ext )
    
    if opts.tka_label_type != "internal_cls" :
        datasource = set_label(datasource, opts.tka_label_img[0], opts.tka_label_img[1], opts.taskList, 'tka_label_img', 'tka_label_template', opts.sourceDir, opts.img_ext )

    if opts.results_label_type != "internal_cls" :
        datasource = set_label(datasource, opts.results_label_img[0], opts.results_label_img[1], opts.taskList, 'results_label_img', 'results_label_template', opts.sourceDir, opts.img_ext)

    if opts.user_t1mni :
        datasource = set_transform(datasource, task_list, opts.sourceDir)

    if opts.user_brainmask :
        datasource = set_brain_mask(datasource, task_list, opts.coregistration_brain_mask, opts.sourceDir, opts.img_ext)
        
    ### Use DataGrabber to get sufraces
    if opts.use_surfaces:
        datasourceSurf = pe.Node( interface=nio.DataGrabber(infields=['sid', 'ses', 'task', 'acq', 'rec'], outfields=[ 'gm_surf', 'wm_surf', 'mid_surf'], raise_on_empty=True, sort_filelist=False), name="datasourceSurf")
        datasourceSurf.inputs.base_directory = opts.sourceDir
        datasourceSurf.inputs.template = '*'
        datasourceSurf.inputs.acq=opts.acq
        datasourceSurf.inputs.rec=opts.rec
        datasourceSurf.inputs.field_template =dict(
            mid_surf="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_midthickness."+opts.surf_ext,
            #FIXME Not sure what BIDS spec is for a surface mask
            surf_mask="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_midthickness_mask.txt" 
        )
        datasourceSurf.inputs.template_args = dict(
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
    
    ##############
    ###Datasink###
    ##############
    datasink=pe.Node(interface=nio.DataSink(), name="output")
    datasink.inputs.base_directory= opts.targetDir + '/' 
    datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]

    ###Create list variables in which to store output
    out_img_list=[]
    out_img_dim=[]
    out_node_list=[]
    

    ###################
    # PET prelimaries #
    ###################
    wf_init_pet=init.get_workflow("prelimaries", infosource, datasink, opts)
    workflow.connect(datasource, 'pet', wf_init_pet, "inputnode.pet")

    #####################
    # MRI Preprocessing # 
    #####################
    wf_mri_preprocess = normalize.get_workflow("mri_normalize", valid_args, opts)
     
    #If user wants to input their own brain mask with the option --user-brainmask,
    #then the source node for the brain mask is datasource. Otherwise it is derived in 
    #stereotaxic space in wf_mri_preprocess
    if opts.user_brainmask : 
        brain_mask_mni_node = datasource
        brain_mask_mni_file = 'brain_mask_mni'
        workflow.connect(datasource, 'brain_mask_mni', wf_mri_preprocess, 'inputnode.brain_mask_mni')    
    else : 
        brain_mask_mni_node = wf_mri_preprocess
        brain_mask_mni_file='outputnode.brain_mask_mni'
        workflow.connect(brain_mask_mni_node, brain_mask_mni_file, datasink, 'wf_mri_preprocess/brain_mask')

    #If user wants to input their own t1 space to mni space transform with the option --user-t1mni,
    #then the source node for the brain mask is datasource. Otherwise it is derived in 
    #stereotaxic space in wf_mri_preprocess
    if opts.user_t1mni : 
        t1mni_node = datasource
        t1mni_file = 'xfmT1MNI'
        workflow.connect(datasource, 'xfmT1MNI', wf_mri_preprocess, 'inputnode.xfmT1MNI')    
    else : 
        t1mni_node = wf_mri_preprocess
        t1mni_file='outputnode.xfmT1MNI'       
        workflow.connect(t1mni_node, t1mni_file, datasink, 'wf_mri_preprocess/t1_mni')
    
    workflow.connect(datasource, 'nativeT1', wf_mri_preprocess, 'inputnode.t1')    

    #####################################################################   
    # Set the appropriate nodes and inputs for desired "analysis_level" #
    # and for the source for the labels                                 #
    #####################################################################
    wf_pet2mri=reg.get_workflow("pet-coregistration", infosource, opts)
    wf_masking=masking.get_workflow("masking", infosource, datasink, opts)
    
    if opts.analysis_space == 'stereo':
        pet_input_node=wf_pet2mri
        pet_input_file='outputnode.petmni_img_4d'
    elif opts.analysis_space == 'pet':
        pet_input_node=wf_init_pet
        pet_input_file='outputnode.pet_center'
    elif opts.analysis_space == 't1':
        pet_input_node=wf_pet2mri
        pet_input_file='outputnode.petmri_img_4d'

    #################################################
    # Combine possible label source into one source #
    #################################################
    if opts.tka_label_type == 'atlas' or opts.tka_label_type == 'user_cls' :
        tka_label_node = datasource
        tka_label_file = 'tka_label_img'
    elif opts.tka_label_type == 'internal_cls' :
        tka_label_node = wf_mri_preprocess
        tka_label_file = 'outputnode.tka_label_img'

    if opts.pvc_label_type == 'atlas' or opts.pvc_label_type == 'user_cls' :
        pvc_label_node = datasource
        pvc_label_file = 'pvc_label_img'
    elif opts.pvc_label_type == 'internal_cls' :
        pvc_label_node = wf_mri_preprocess
        pvc_label_file = 'outputnode.pvc_label_img'

    if opts.results_label_type == 'atlas' or opts.results_label_type == 'user_cls' :
        results_label_node = datasource
        results_label_file = 'results_label_img'
    elif opts.results_label_type == 'internal_cls' :
        results_label_node = wf_mri_preprocess
        results_label_file = 'outputnode.results_label_img'

   
    ##################
    # Coregistration #
    ##################
    workflow.connect(wf_init_pet, 'outputnode.pet_volume', wf_pet2mri, "inputnode.pet_volume")
    workflow.connect(wf_init_pet, 'outputnode.pet_center', wf_pet2mri, "inputnode.pet_volume_4d")
    workflow.connect(wf_mri_preprocess, 'outputnode.brain_mask_t1', wf_pet2mri, 'inputnode.t1_brain_mask')
    workflow.connect(datasource, 'nativeT1' , wf_pet2mri,"inputnode.nativeT1nuc")
    workflow.connect(wf_mri_preprocess, 'outputnode.t1_mni', wf_pet2mri,"inputnode.T1Tal")
    workflow.connect(t1mni_node, t1mni_file, wf_pet2mri,"inputnode.xfmT1MNI")
    
    if opts.test_group_qc :
        misregistration = pe.Node(interface=util.IdentityInterface(fields=['error']), name="misregistration")
        misregistration.iterables = ('error',tqc.errors)
        workflow.connect(misregistration, 'error', wf_pet2mri, "inputnode.error")

    out_node_list += [pet_input_node] 
    out_img_list += [pet_input_file]
    out_img_dim += ['4']
    
    ###########
    # Masking #
    ###########
    workflow.connect(datasource, 'nativeT1', wf_masking, "inputnode.nativeT1")
    workflow.connect(t1mni_node, t1mni_file, wf_masking, "inputnode.LinT1MNIXfm")
    workflow.connect(wf_init_pet, 'outputnode.pet_header_json', wf_pet2mri, 'inputnode.header')
    workflow.connect(wf_pet2mri, "outputnode.LinPETT1Xfm", wf_masking, "inputnode.LinPETT1Xfm")
    workflow.connect(wf_pet2mri, "outputnode.LinT1PETXfm", wf_masking, "inputnode.LinT1PETXfm")
    workflow.connect(wf_pet2mri, "outputnode.LinPETMNIXfm", wf_masking, "inputnode.LinPETMNIXfm")
    workflow.connect(wf_pet2mri, "outputnode.LinMNIPETXfm", wf_masking, "inputnode.LinMNIPETXfm")
    workflow.connect(wf_mri_preprocess, 'outputnode.t1_mni', wf_masking, "inputnode.mniT1")
    workflow.connect(brain_mask_mni_node, brain_mask_mni_file, wf_masking, "inputnode.brainmask")
    if not opts.nopvc:
        workflow.connect(preinfosource, 'pvc_labels', wf_masking, "inputnode.pvc_labels")
        workflow.connect(pvc_label_node, pvc_label_file, wf_masking, "inputnode.pvc_label_img")
    if opts.tka_method != None :
        workflow.connect(preinfosource, 'tka_labels', wf_masking, "inputnode.tka_labels")
        workflow.connect(tka_label_node, tka_label_file, wf_masking, "inputnode.tka_label_img")
    workflow.connect(preinfosource, 'results_labels', wf_masking, "inputnode.results_labels")
    workflow.connect(preinfosource, 'pvc_erode_times', wf_masking, "inputnode.pvc_erode_times")
    workflow.connect(preinfosource, 'tka_erode_times', wf_masking, "inputnode.tka_erode_times")
    workflow.connect(preinfosource, 'results_erode_times', wf_masking, "inputnode.results_erode_times")
    workflow.connect(results_label_node, results_label_file, wf_masking, "inputnode.results_label_img")
    workflow.connect(wf_init_pet, 'outputnode.pet_volume', wf_masking, "inputnode.pet_volume")

    if not opts.pvc_label_img[1] == None: 
        workflow.connect(datasource, "pvc_label_template", wf_masking, "inputnode.pvc_label_template")
    if not opts.tka_label_img[1] == None: 
        workflow.connect(datasource, "tka_label_template", wf_masking, "inputnode.tka_label_template")
    if not opts.results_label_img[1] == None: 
        workflow.connect(datasource, "results_label_template", wf_masking, "inputnode.results_label_template")

    ######################
    # Transform Surfaces #
    ######################
    if opts.use_surfaces:
        surf_wf = surf_masking.get_surf_workflow('surface_transform', infosource, datasink, opts)
        workflow.connect(t1mni_node, t1mni_file, surf_wf, 'inputnode.T1MNI')
        workflow.connect(wf_masking, 'invert_MNI2T1.output_file',  surf_wf, 'inputnode.MNIT1')
        workflow.connect(wf_pet2mri, "outputnode.petmri_xfm",  surf_wf, 'inputnode.PETT1')
        workflow.connect(wf_pet2mri, "outputnode.petmri_xfm_invert", surf_wf, 'inputnode.T1PET')
        workflow.connect(datasourceSurf, 'mid_surf', surf_wf, 'inputnode.obj_file')
        workflow.connect(wf_masking, 'resultsLabels.out_file', surf_wf, 'inputnode.vol_file')

    #############################
    # Partial-volume correction #
    #############################
    if not opts.nopvc :
        pvc_wf = pvc.get_pvc_workflow("pvc", infosource, datasink, opts) 
        workflow.connect(pet_input_node, pet_input_file, pvc_wf, "inputnode.in_file") #CHANGE
        workflow.connect(wf_masking, "pvcLabels.out_file", pvc_wf, "inputnode.mask_file") #CHANGE
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
           workflow.connect(wf_masking, "resultsLabels.out_file", tka_wf, 'inputnode.like_file')
        workflow.connect(infosource, 'sid', tka_wf, "inputnode.sid")
        #if opts.tka_method in reference_methods:
        workflow.connect(wf_masking, "resultsLabels.out_file", tka_wf, "inputnode.mask") 
        workflow.connect(tka_target_wf, tka_target_img, tka_wf, "inputnode.in_file")
        if opts.arterial :
            workflow.connect(datasourceArterial, 'arterial_file', tka_wf, "inputnode.reference")
        elif opts.tka_method in reference_methods + ['suvr']: #FIXME should not just add suvr like this 
            workflow.connect(wf_masking, 'tkaLabels.out_file', tka_wf, "inputnode.reference")
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
            workflow.connect(wf_masking, 'resultsLabels.out_file', resultsReport, 'mask')
            workflow.connect(node, img, resultsReport, 'in_file')
            workflow.connect(node, img, datasink, node.name)

            if opts.use_surfaces :
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
        workflow.connect(datasource, 'nativeT1',  distance_metricNode, 't1')
        workflow.connect(wf_masking, 'brain_mask_node.output_file', distance_metricNode, 't1_brain_mask')
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

    printOptions(opts,subjects_ids,session_ids,task_list)
    #run the work flow
    if opts.num_threads > 1 :
        plugin_args = {'n_procs' : opts.num_threads,
                   #'memory_gb' : num_gb, 'status_callback' : log_nodes_cb
                      }
        workflow.run(plugin='MultiProc', plugin_args=plugin_args)
    else : 
        workflow.run()

    return 0


