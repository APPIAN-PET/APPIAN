#--user-brainmask --user-brainmask  vim: set tabstop=4 expandtab shgftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
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


def set_base(datasourcePET, datasourceT1, task_list, run_list, acq, rec, sourceDir, img_ext ):
    pet_str = sourceDir+os.sep+'sub-%s/*ses-%s/pet/sub-%s_ses-%s'
    pet_list = ['sid', 'ses', 'sid', 'ses']
    t1_list =  [ 'sid', 'ses', 'sid', 'ses']
    t1_str=sourceDir+os.sep+'sub-%s/*ses-%s/anat/sub-%s_ses-%s'
    if len(task_list) != 0: 
        pet_str = pet_str + '*task-%s'
        pet_list += ['task'] 
    if acq != '' :
        pet_str = pet_str + '*acq-%s'
        pet_list += ['acq']  
    if rec != '':
        pet_str = pet_str + '*rec-%s'
        pet_list += ['rec']
    if len(run_list) != 0: 
        pet_str = pet_str + '*run-%s'
        pet_list += ['run']
    pet_str = pet_str + '*_pet.mnc'
    #pet_str = pet_str + '*_pet.mnc%s'
    #pet_list += ['compression']
    t1_str = t1_str + '*_T1w.mnc'
    #Dictionary for basic structural inputs to DataGrabber
    field_template_t1 = dict(
        nativeT1 = t1_str,
    )
    template_args_t1 = dict(
        nativeT1=[t1_list],
    ) 
    
    field_template_pet = dict(
        pet=pet_str
    )
    template_args_pet = dict(
        pet=[pet_list]
    )

    datasourcePET.inputs.field_template.update(field_template_pet)
    datasourcePET.inputs.template_args.update(template_args_pet)

    datasourceT1.inputs.field_template.update(field_template_t1)
    datasourceT1.inputs.template_args.update(template_args_t1)
    return datasourcePET, datasourceT1



def set_label(datasource, img, template, task_list, run_list, label_img, template_img, sourceDir, img_ext):
    '''
    '''
    field_template={}
    template_args={}

    if template == None :
        label_img_template=sourceDir+os.sep+'*sub-%s/*ses-%s/anat/sub-%s_ses-%s'
        template_args[label_img]=[['sid', 'ses', 'sid', 'ses'] ] 
        label_img_template +='*_variant-'+img+'_dtissue.'+img_ext
        field_template[label_img] = label_img_template
    else :
        field_template[label_img] = "%s"
        template_args[label_img] = [[img]]
        field_template[template_img] = "%s"
        template_args[template_img] = [[template]]
        
    datasource.inputs.field_template.update( field_template )
    datasource.inputs.template_args.update( template_args )
    return datasource

def set_json_header(datasource, task_list, run_list, acq, rec, sourceDir):
    field_template={}
    template_args={}
    json_header_list =  [[ 'sid', 'ses', 'sid', 'ses']]
    json_header_str=sourceDir+os.sep+'sub-%s/*ses-%s/pet/sub-%s_ses-%s'
    if len(task_list) != 0: 
        json_header_str = json_header_str + '_task-%s'
        json_header_list[0] += ["task"] #task_list

    if len(run_list) != 0 :
        json_header_str = json_header_str + "_run-%s"
        json_header_list[0] += ["run"]
    
    if acq != '' :
        json_header_str = json_header_str + '*acq-%s'
        json_header_list[0] += ['acq']  
    if rec != '':
        json_header_str = json_header_str + '*rec-%s'
        json_header_list[0] += ['rec']

    json_header_str = json_header_str + '*.json'
    
    field_template["json_header"] = json_header_str
    template_args["json_header"] = json_header_list

    datasource.inputs.field_template.update(field_template)
    datasource.inputs.template_args.update(template_args)
    return datasource

def set_transform(datasource, task_list, set_list, sourceDir):
    field_template={}
    template_args={}
    label_template = sourceDir+os.sep+'sub-%s/*ses-%s/transforms/sub-%s_ses-%s'
    template_args["xfmT1MNI"] = [['sid', 'ses', 'sid', 'ses' ]]
    #if len(task_list) != 0 :
    #    label_template = label_template + "_task-%s"
    #    template_args["xfmT1MNI"][0] += ["task"] #task_list

    label_template = label_template + '*target-MNI_affine.xfm'
    
    field_template["xfmT1MNI"] = label_template

    datasource.inputs.field_template.update(field_template)
    datasource.inputs.template_args.update(template_args)
    return datasource

def set_brain_mask(datasource, task_list, run_list, coregistration_brain_mask, sourceDir, img_ext) :
    field_template={}
    template_args={}

    brain_mask_template = sourceDir+os.sep+'sub-%s/*ses-%s/anat/sub-%s_ses-%s*'
    template_args["brain_mask_mni"]=[['sid' ,'ses','sid', 'ses']]

    brain_mask_template = brain_mask_template + "_T1w_space-mni"

    if not coregistration_brain_mask : 
       brain_mask_template = brain_mask_template + '_skullmask.*'+img_ext
    else :
        brain_mask_template = brain_mask_template + '_brainmask.*'+img_ext

    field_template["brain_mask_mni"] = brain_mask_template
    
    datasource.inputs.field_template.update(field_template)
    datasource.inputs.template_args.update(template_args)
    return datasource



def printOptions(opts,subject_ids,session_ids,task_list, run_list, acq, rec):
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
    print "* Runs : " , run_list , "\n"
    print "* Acquisition : " , acq , "\n"
    print "* Reconstruction : " , rec , "\n"


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

    opts.calculate_t1_pet_space = False
    if opts.group_qc or opts.test_group_qc :
        opts.calculate_t1_pet_space = True


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
    sub_valid_args, task_valid_args=init.gen_args(opts, session_ids, task_list, opts.runList, opts.acq, opts.rec, args)
    ### Create workflow
    workflow = pe.Workflow(name=opts.preproc_dir)
    workflow.base_dir = opts.targetDir

    #####################
    ### Preinfosource ###
    #####################
    preinfosource = pe.Node(interface=util.IdentityInterface(fields=['args','ses','results_labels','tka_labels','pvc_labels', 'pvc_erode_times', 'tka_erode_times', 'results_erode_times']), name="preinfosource")
    preinfosource.iterables = ( 'args', task_valid_args )
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
    workflow.connect(preinfosource, 'args', infosource, "args")
    
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
    base_t1_outputs  = ['nativeT1', 'xfmT1MNI','brain_mask_mni', "pvc_label_img", "tka_label_img", "results_label_img", "pvc_label_template", "tka_label_template", "results_label_template" ]
    base_pet_outputs  = [ 'pet', "json_header" ]


    datasourcePET = pe.Node( interface=nio.DataGrabber(infields=[], outfields=base_pet_outputs, raise_on_empty=True, sort_filelist=False), name="datasourcePET")
    datasourcePET.inputs.template = '*'
    datasourcePET.inputs.base_directory = '/' # opts.sourceDir
    datasourcePET.inputs.acq=opts.acq
    datasourcePET.inputs.rec=opts.rec  
    
    datasourceT1 = pe.Node( interface=nio.DataGrabber(infields=[], outfields=base_t1_outputs, raise_on_empty=True, sort_filelist=False), name="datasourceT1")
    datasourceT1.inputs.template = '*'
    datasourceT1.inputs.base_directory = '/' # opts.sourceDir

    datasource = pe.Node(util.IdentityInterface(fields=base_t1_outputs+base_pet_outputs), name="datasource") 
    
    # Set label datasource
    datasourcePET.inputs.field_template = {}
    datasourcePET.inputs.template_args = {}

    datasourceT1.inputs.field_template = {}
    datasourceT1.inputs.template_args = {}

    datasourcePET, datasourceT1 = set_base(datasourcePET,datasourceT1,opts.taskList,opts.runList,opts.acq, opts.rec, opts.sourceDir, opts.img_ext)
    if opts.pvc_label_type != "internal_cls" :
        datasourceT1 = set_label(datasourceT1, opts.pvc_label_img, opts.pvc_label_template, opts.taskList, opts.runList, 'pvc_label_img', 'pvc_label_template', opts.sourceDir, opts.img_ext )
        workflow.connect(datasourceT1, 'pvc_label_img', datasource, 'pvc_label_img' )
        if opts.pvc_label_template != None :
            workflow.connect(datasourceT1, 'pvc_template_img', datasource, 'pvc_template_img')

    if opts.tka_label_type != "internal_cls" :
        datasourceT1 = set_label(datasourceT1, opts.tka_label_img, opts.tka_label_template, opts.taskList, opts.runList, 'tka_label_img', 'tka_label_template', opts.sourceDir, opts.img_ext )
        workflow.connect(datasourceT1, 'tka_label_img', datasource, 'tka_label_img' )
        if opts.tka_label_template != None :
            workflow.connect(datasourceT1,'tka_label_template',datasource,'tka_label_template')

    if opts.results_label_type != "internal_cls" :
        datasourceT1 = set_label(datasourceT1, opts.results_label_img, opts.results_label_template, opts.taskList, opts.runList, 'results_label_img', 'results_label_template', opts.sourceDir, opts.img_ext)
        workflow.connect(datasourceT1, 'results_label_img', datasource, 'results_label_img' )
        if opts.results_label_template != None :
            workflow.connect(datasourceT1, 'results_template_img', datasource, 'results_template_img' )

    if opts.user_t1mni :
        datasourceT1 = set_transform(datasourceT1, task_list, opts.runList, opts.sourceDir)
        workflow.connect(datasourceT1, 'xfmT1MNI', datasource, 'xfmT1MNI' )

    if opts.user_brainmask :
        datasourceT1 = set_brain_mask(datasourceT1, task_list, opts.runList, opts.coregistration_brain_mask, opts.sourceDir, opts.img_ext)
        workflow.connect(datasourceT1, 'brain_mask_mni', datasource, 'brain_mask_mni' )

    #if opts.json :
    datasourcePET = set_json_header(datasourcePET, task_list, opts.runList, opts.acq, opts.rec, opts.sourceDir)   
    
    ### Use DataGrabber to get sufraces
    if opts.use_surfaces:
        datasourceSurf = pe.Node( interface=nio.DataGrabber(infields=['sid', 'ses', 'task', 'acq', 'rec', 'label'], outfields=['surf_left','mask_left', 'surf_right', 'mask_right'], raise_on_empty=True, sort_filelist=False), name="datasourceSurf")
        datasourceSurf.inputs.base_directory = opts.sourceDir
        datasourceSurf.inputs.template = '*'
        datasourceSurf.inputs.acq=opts.acq
        datasourceSurf.inputs.rec=opts.rec
        datasourceSurf.inputs.label=opts.surface_label
        datasourceSurf.inputs.field_template =dict(
            surf_left="sub-%s/_ses-%s/anat/sub-%s_ses-%s_*T1w_hemi-L_space-stereo_midthickness.surf.obj",
            surf_right="sub-%s/_ses-%s/anat/sub-%s_ses-%s_*T1w_hemi-R_space-stereo_midthickness.surf.obj",
            #FIXME Not sure what BIDS spec is for a surface mask
            mask_left="sub-%s/_ses-%s/anat/sub-%s_ses-%s_*T1w_hemi-L_space-stereo_%s.txt",
            mask_right="sub-%s/_ses-%s/anat/sub-%s_ses-%s_*T1w_hemi-R_space-stereo_%s.txt",
        )
        datasourceSurf.inputs.template_args = dict(
            surf_left = [['sid', 'ses', 'sid', 'ses']],
            surf_right = [['sid', 'ses', 'sid', 'ses']],
            mask_left = [['sid', 'ses', 'sid', 'ses', 'label']],
            mask_right = [['sid', 'ses', 'sid', 'ses','label']]
        )
        workflow.connect([
                (infosource, datasourceSurf, [('sid', 'sid')]),
                (infosource, datasourceSurf, [('cid', 'cid')]),
                (infosource, datasourceSurf, [('task', 'task')]),
                (infosource, datasourceSurf, [('ses', 'ses')]),
                (infosource, datasourceSurf, [('run', 'run')]),
                 ])

    #############################################
    ### Define Workflow and basic connections ###
    #############################################
    workflow.connect([
                    (infosource, datasourcePET, [('sid', 'sid')]),
                    (infosource, datasourcePET, [('ses', 'ses')]),
                    (infosource, datasourcePET, [('cid', 'cid')]),
                    (infosource, datasourcePET, [('task', 'task')]),
                    (infosource, datasourcePET, [('run', 'run')]),
                    #(infosource, datasourcePET, [('compression', 'compression')]),
                     ])
    workflow.connect([
                    (infosource, datasourceT1, [('sid', 'sid')]),
                    (infosource, datasourceT1, [('ses', 'ses')]),
                     ])
    
    workflow.connect(datasourcePET, 'json_header', datasource, 'json_header' )
    workflow.connect(datasourceT1, 'nativeT1', datasource, 'nativeT1' )
    workflow.connect(datasourcePET, 'pet', datasource, 'pet' )

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
    wf_init_pet=init.get_workflow("prelimaries", infosource, opts)
    workflow.connect(datasource, 'pet', wf_init_pet, "inputnode.pet")
    #if opts.json :
    workflow.connect(datasource, 'json_header', wf_init_pet, "inputnode.json_header")
    
    if opts.initialize_only :
        workflow.run(); 
        return(0)


    #####################
    # MRI Preprocessing # 
    #####################
    wf_mri_preprocess = normalize.get_workflow("mri_normalize", sub_valid_args, opts)
     
    #If user wants to input their own brain mask with the option --user-brainmask,
    #then the source node for the brain mask is datasource. Otherwise it is derived in 
    #stereotaxic space in wf_mri_preprocess
    if opts.user_brainmask : 
        brain_mask_mni_node = datasourceT1
        brain_mask_mni_file = 'brain_mask_mni'
        workflow.connect(datasource, 'brain_mask_mni', wf_mri_preprocess, 'inputnode.brain_mask_mni')    
    else : 
        brain_mask_mni_node = wf_mri_preprocess
        brain_mask_mni_file='outputnode.brain_mask_mni'
        workflow.connect(brain_mask_mni_node, brain_mask_mni_file, datasink, 't1/brain_mask')

    #If user wants to input their own t1 space to mni space transform with the option --user-t1mni,
    #then the source node for the brain mask is datasource. Otherwise it is derived in 
    #stereotaxic space in wf_mri_preprocess
    if opts.user_t1mni : 
        t1mni_node = datasource
        t1mni_file = 'xfmT1MNI'
        workflow.connect(datasourceT1, 'xfmT1MNI', wf_mri_preprocess, 'inputnode.xfmT1MNI')    
    else : 
        t1mni_node = wf_mri_preprocess
        t1mni_file='outputnode.xfmT1MNI'       
        workflow.connect(t1mni_node, t1mni_file, datasink, 't1/stereotaxic')
    
    workflow.connect(datasourceT1, 'nativeT1', wf_mri_preprocess, 'inputnode.t1')    
    
    #####################################################################   
    # Set the appropriate nodes and inputs for desired "analysis_level" #
    # and for the source for the labels                                 #
    #####################################################################
    wf_pet2mri=reg.get_workflow("pet-coregistration", infosource, opts)
    wf_masking=masking.get_workflow("masking", infosource, opts)
    
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
    if opts.tka_label_type in ['atlas', 'atlas-template', 'user_cls'] :
        tka_label_node = datasource
        tka_label_file = 'tka_label_img'
    else : # opts.tka_label_type == 'internal_cls' :
        tka_label_node = wf_mri_preprocess
        tka_label_file = 'outputnode.tka_label_img'

    if opts.pvc_label_type in ['atlas', 'atlas-template', 'user_cls'] :
        pvc_label_node = datasource
        pvc_label_file = 'pvc_label_img'
    elif opts.pvc_label_type == 'internal_cls' :
        pvc_label_node = wf_mri_preprocess
        pvc_label_file = 'outputnode.pvc_label_img'

    if opts.results_label_type in [ 'atlas', 'atlas-template', 'user_cls'] :
        results_label_node = datasource
        results_label_file = 'results_label_img'
    elif opts.results_label_type == 'internal_cls' :
        results_label_node = wf_mri_preprocess
        results_label_file = 'outputnode.results_label_img'

    #############################
    # PET-to-MRI Coregistration #
    #############################
    workflow.connect(wf_init_pet, 'outputnode.pet_volume', wf_pet2mri, "inputnode.pet_volume")
    workflow.connect(wf_init_pet, 'outputnode.pet_center', wf_pet2mri, "inputnode.pet_volume_4d")
    workflow.connect(wf_mri_preprocess, 'outputnode.brain_mask_t1', wf_pet2mri, 'inputnode.t1_brain_mask')

    workflow.connect(wf_init_pet, 'outputnode.pet_header_json', wf_pet2mri, 'inputnode.header')
    workflow.connect(datasource, 'nativeT1' , wf_pet2mri,"inputnode.nativeT1nuc")
    workflow.connect(wf_mri_preprocess, 'outputnode.t1_mni', wf_pet2mri,"inputnode.T1Tal")
    workflow.connect(t1mni_node, t1mni_file, wf_pet2mri,"inputnode.xfmT1MNI")
    
    if opts.test_group_qc :
        misregistration = pe.Node(interface=util.IdentityInterface(fields=['error']), name="misregistration")
        misregistration.iterables = ('error',tqc.errors)
        workflow.connect(misregistration, 'error', wf_pet2mri, "inputnode.error")

    workflow.connect(wf_pet2mri, 'outputnode.petmri_img_4d', datasink,'pet_coregistration' )
    out_node_list += [pet_input_node] 
    out_img_list += [pet_input_file]
    out_img_dim += ['4']
    #Add the outputs of Coregistration to list that keeps track of the outputnodes, images, 
    # and the number of dimensions of these images       
    if opts.coregistration_only :
        workflow.run(); 
        return(0)

    ###########
    # Masking #
    ###########
    workflow.connect(datasource, 'nativeT1', wf_masking, "inputnode.nativeT1")
    workflow.connect(t1mni_node, t1mni_file, wf_masking, "inputnode.LinT1MNIXfm")
    workflow.connect(wf_init_pet, 'outputnode.pet_header_json', wf_masking, 'inputnode.pet_header_json')
    workflow.connect(wf_pet2mri, "outputnode.petmri_xfm", wf_masking, "inputnode.LinPETT1Xfm")
    workflow.connect(wf_pet2mri, "outputnode.mripet_xfm", wf_masking, "inputnode.LinT1PETXfm")
    workflow.connect(wf_pet2mri, "outputnode.petmni_xfm", wf_masking, "inputnode.LinPETMNIXfm")
    workflow.connect(wf_pet2mri, "outputnode.mnipet_xfm", wf_masking, "inputnode.LinMNIPETXfm")
    workflow.connect(wf_mri_preprocess, 'outputnode.t1_mni', wf_masking, "inputnode.mniT1")
    workflow.connect(brain_mask_mni_node, brain_mask_mni_file, wf_masking, "inputnode.brainmask")
    if not opts.nopvc:
        #If PVC method has been set, define binary masks to contrain PVC
        workflow.connect(preinfosource, 'pvc_labels', wf_masking, "inputnode.pvc_labels")
        workflow.connect(pvc_label_node, pvc_label_file, wf_masking, "inputnode.pvc_label_img")
    if opts.tka_method != None :
        #If TKA method has been set, define binary masks for reference region
        workflow.connect(preinfosource, 'tka_labels', wf_masking, "inputnode.tka_labels")
        workflow.connect(tka_label_node, tka_label_file, wf_masking, "inputnode.tka_label_img")
    #Results labels are always set
    workflow.connect(preinfosource, 'results_labels', wf_masking, "inputnode.results_labels")
    workflow.connect(results_label_node, results_label_file, wf_masking, "inputnode.results_label_img")
    workflow.connect(wf_init_pet, 'outputnode.pet_volume', wf_masking, "inputnode.pet_volume")

    # If <pvc/tka/results>_label_template has been set, this means that label_img[0] contains the file path
    # to stereotaxic atlas and label_template contains the file path to the template image for the atlas
    if not opts.pvc_label_template == None: 
        workflow.connect(datasource, "pvc_label_template", wf_masking, "inputnode.pvc_label_template")
    if not opts.tka_label_template == None: 
        workflow.connect(datasource, "tka_label_template", wf_masking, "inputnode.tka_label_template")
    if not opts.results_label_template == None: 
        workflow.connect(datasource, "results_label_template", wf_masking, "inputnode.results_label_template")

    ######################
    # Transform Surfaces #
    ######################
    if opts.use_surfaces:
        workflow.connect(datasourceSurf, 'surf_left', wf_masking, 'inputnode.surf_left')
        workflow.connect(datasourceSurf, 'surf_right', wf_masking, 'inputnode.surf_right')

    if opts.masking_only:
        workflow.run();
        return(0)



    #############################
    # Partial-volume correction #
    #############################
    if opts.pvc_method != None :
        pvc_wf = pvc.get_pvc_workflow("pvc", infosource, opts) 
        workflow.connect(pet_input_node, pet_input_file, pvc_wf, "inputnode.in_file") #CHANGE
        workflow.connect(wf_masking, "pvcLabels.out_file", pvc_wf, "inputnode.mask_file") #CHANGE
        workflow.connect(wf_init_pet, 'outputnode.pet_header_json', pvc_wf, "inputnode.header") #CHANGE
        #Add the outputs of PVC to list that keeps track of the outputnodes, images, and the number 
        #of dimensions of these images
        out_node_list += [pvc_wf]
        out_img_list += ['outputnode.out_file']
        out_img_dim += ['4']
    
        workflow.connect(pvc_wf, 'outputnode.out_file', datasink,'pvc' )

    ###########################
    # Tracer kinetic analysis #
    ###########################
    if not opts.tka_method == None:
        if opts.pvc_method != None : 
            tka_target_wf = pvc_wf
            tka_target_img='outputnode.out_file'
        else : 
            tka_target_wf = pet_input_node # #CHANGE
            tka_target_img= pet_input_file # ##CHANGE
        tka_wf=tka.get_tka_workflow("tka", opts)
        workflow.connect(wf_init_pet, 'outputnode.pet_header_json', tka_wf, "inputnode.header")
        workflow.connect(wf_masking, "resultsLabels.out_file", tka_wf, "inputnode.mask") 
        workflow.connect(tka_target_wf, tka_target_img, tka_wf, "inputnode.in_file")
        if opts.arterial :
            workflow.connect(datasourceArterial, 'arterial_file', tka_wf, "inputnode.reference")
        else :     
            workflow.connect(wf_masking, 'tkaLabels.out_file', tka_wf, "inputnode.reference")
        
        #Add the outputs of TKA (Quuantification) to list that keeps track of the outputnodes, images, 
        # and the number of dimensions of these images       
        out_node_list += [tka_wf]
        out_img_list += ['outputnode.out_file']
        out_img_dim += ['3']

        workflow.connect(tka_wf, 'outputnode.out_file', datasink,'quantification' )
    
    #######################################
    # Connect nodes for reporting results #
    #######################################
    # For each of the nodes in the outputnode list pass the output image to mincgroupstats.
    # This will print out descriptive statistics for the labelled regions in the mask image
    # for the output image. 
    #print( opts.no_results_report ) ; 
    if not opts.no_results_report:
        for node, img, dim in zip(out_node_list, out_img_list, out_img_dim):
            print "outputnode", node.name, "image name", img
            
            node_name="results_" + node.name 
            resultsReport = pe.Node(interface=results.resultsCommand(), name=node_name)
            resultsReport.inputs.dim = dim
            resultsReport.inputs.node = node.name
            resultsReport.inputs.acq = opts.acq
            resultsReport.inputs.rec = opts.rec
            workflow.connect(infosource, 'sid', resultsReport, "sub")
            workflow.connect(infosource, 'ses', resultsReport, "ses")
            workflow.connect(infosource, 'task', resultsReport, "task")
            workflow.connect(infosource, 'run', resultsReport, "run")
            workflow.connect(wf_init_pet, 'outputnode.pet_header_json', resultsReport, "header")
            workflow.connect(wf_masking, 'resultsLabels.out_file', resultsReport, 'mask')
            workflow.connect(node, img, resultsReport, 'in_file')
           
            if int(dim) == 3 :
                workflow.connect( resultsReport, 'out_file_3d', datasink, "results"+os.sep+node_name )
            elif int(dim) == 4:
                workflow.connect( resultsReport, 'out_file_4d', datasink, "results"+os.sep+node_name )   
            
            if opts.use_surfaces :
                node_name="results_surf_" + node.name 
                resultsReportSurf = pe.Node(interface=results.resultsCommand(), name=node_name)
                resultsReportSurf.inputs.dim = dim
                resultsReportSurf.inputs.node = node.name
                resultsReportSurf.inputs.acq = opts.acq
                resultsReportSurf.inputs.rec = opts.rec
                workflow.connect(infosource, 'sid', resultsReportSurf, "sub")
                workflow.connect(infosource, 'ses', resultsReportSurf, "ses")
                workflow.connect(infosource, 'task', resultsReportSurf, "task")
                workflow.connect(wf_init_pet, 'outputnode.pet_header_json', resultsReportSurf, "header")
                workflow.connect(node, img, resultsReportSurf, 'in_file')
                workflow.connect(wf_masking, 'surface_left_node.out_file', resultsReportSurf, "surf_left")
                workflow.connect(datasourceSurf, 'mask_left', resultsReportSurf, 'mask_left')
                workflow.connect(wf_masking, 'surface_right_node.out_file', resultsReportSurf, "surf_right")
                workflow.connect(datasourceSurf, 'mask_right', resultsReportSurf, 'mask_right')   
                if int(dim) == 4 :
                    workflow.connect( resultsReportSurf, 'out_file_3d', datasink, "results"+os.sep+node_name )
                elif int(dim) == 4:
                    workflow.connect( resultsReportSurf, 'out_file_4d', datasink, "results"+os.sep+node_name )    
    ############################
    # Subject-level QC Metrics #
    ############################
    if opts.group_qc or opts.test_group_qc :
        #Automated QC: PET to MRI linear coregistration 
        distance_metricNode=pe.Node(interface=qc.coreg_qc_metricsCommand(),name="coreg_qc_metrics")
        workflow.connect(wf_init_pet, 'outputnode.pet_volume',  distance_metricNode, 'pet')
        workflow.connect(wf_pet2mri,'t1_brain_mask_pet-space.output_file',distance_metricNode,'pet_brain_mask')
        workflow.connect(wf_pet2mri, 't1_pet_space.output_file',  distance_metricNode, 't1')
        workflow.connect(wf_masking, 'brain_mask.output_file', distance_metricNode, 't1_brain_mask')
        #workflow.connect(wf_masking, 'output_node.brain_mask', distance_metricNode, 't1_brain_mask')
        #workflow.connect(wf_masking, 'outputnode.brain_mask', distance_metricNode, 't1_brain_mask')
        workflow.connect(infosource, 'ses', distance_metricNode, 'ses')
        workflow.connect(infosource, 'task', distance_metricNode, 'task')
        workflow.connect(infosource, 'sid', distance_metricNode, 'sid')

        if  opts.pvc_method != None :
            #Automated QC: PVC 
            pvc_qc_metricsNode=pe.Node(interface=qc.pvc_qc_metrics(),name="pvc_qc_metrics")
            pvc_qc_metricsNode.inputs.fwhm = list(opts.scanner_fwhm)
            workflow.connect(pet_input_node, pet_input_file, pvc_qc_metricsNode, 'pve') ##CHANGE
            #workflow.connect(tka_target_wf, tka_target_img, pvc_qc_metricsNode, 'pvc'  )
            workflow.connect(pvc_wf, "outputnode.out_file", pvc_qc_metricsNode, 'pvc'  )
            workflow.connect(infosource, 'sid', pvc_qc_metricsNode, "sub")
            workflow.connect(infosource, 'ses', pvc_qc_metricsNode, "ses")
            workflow.connect(infosource, 'task', pvc_qc_metricsNode, "task")

    #vizualization graph of the workflow
    #workflow.write_graph(opts.targetDir+os.sep+"workflow_graph.dot", graph2use = 'exec')

    printOptions(opts,subjects_ids,session_ids,task_list,opts.runList, opts.acq, opts.rec)
    #run the work flow
    if opts.num_threads > 1 :
        plugin_args = {'n_procs' : opts.num_threads,
                   #'memory_gb' : num_gb, 'status_callback' : log_nodes_cb
                      }
        workflow.run(plugin='MultiProc', plugin_args=plugin_args)
    else : 
        workflow.run()

    return 0


