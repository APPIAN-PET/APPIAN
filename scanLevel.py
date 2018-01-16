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
from Tracer_Kinetic import tka_methods
import Quality_Control.qc as qc
import Test.test_group_qc as tqc


def set_datasource_inputs(opts):
    ### Set the inputs for the labeled image for datasource
    [ pvc_label_img_string, pvc_label_img_variables  ] = set_label_parameters(opts.pvc_label_level, 'pvc_label_img', 'pvc_img_string', opts.img_ext )
    [ tka_label_img_string, tka_label_img_variables  ] = set_label_parameters(opts.tka_label_level, 'tka_label_img', 'tka_img_string', opts.img_ext )
    [ results_label_img_string, results_label_img_variables  ] = set_label_parameters(opts.results_label_level, 'results_label_img', 'results_img_string', opts.img_ext )

    ### Set the inputs for the template image for datasource
    [ pvc_label_template_string, pvc_label_template_variables  ] = set_label_parameters(opts.pvc_label_level, 'pvc_label_template', 'pvc_template_string',opts.img_ext )
    [ tka_label_template_string, tka_label_template_variables  ] = set_label_parameters(opts.tka_label_level, 'tka_label_template', 'tka_template_string', opts.img_ext )
    [ results_label_template_string, results_label_template_variables  ] = set_label_parameters(opts.results_label_level, 'results_label_template', 'results_template_string', opts.img_ext )


    if opts.pvc_label_img[1] == None: pvc_label_img_string = opts.sourceDir + os.sep + pvc_label_img_string 
    if opts.tka_label_img[1] == None: tka_label_img_string = opts.sourceDir + os.sep + tka_label_img_string 
    if opts.results_label_img[1] == None: results_label_img_string = opts.sourceDir + os.sep + results_label_img_string 

    ### 
    infields_list=['sid', 'ses', 'task', 'acq', 'rec'] 
    base_label=['pvc_label_img','tka_label_img', 'results_label_img' ] 
    base_images=['nativeT1',  'nativeT1nuc',  'T1Tal',  'brainmaskTal',  'headmaskTal',  'clsmask', 'segmentation', 'pet']
    base_transforms=[ 'xfmT1MNI' ,'xfmT1MNInl']
    base_outputs = base_images + base_transforms  + base_label 
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
        pvc_label_img = pvc_label_img_string,
        tka_label_img = tka_label_img_string,
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

    #infields_list += ['pvc_img_string','tka_img_string','results_img_string' ] 
    if not opts.pvc_label_img[1] == None: 
        #assign pvc input to datasource
        pvc_template_string, field_template_dict, template_args_dict, base_label, infields_list = assign_datasource_values(opts.pvc_label_img, field_template_dict, template_args_dict, base_label, infields_list, pvc_label_template_string, pvc_label_template_variables, 'pvc_label_template' , 'pvc_template_string'  )
        base_outputs.append('pvc_label_template')
    else : pvc_template_string = ''
    
    if not opts.tka_label_img[1] == None: 
        #assign tka input to datasource
        tka_template_string, field_template_dict, template_args_dict, base_label, infields_list = assign_datasource_values(opts.tka_label_img, field_template_dict, template_args_dict, base_label, infields_list, tka_label_template_string, tka_label_template_variables, 'tka_label_template' , 'tka_template_string'  )
        base_outputs.append('tka_label_template')
    else : tka_template_string = ''

    if not opts.results_label_img[1] == None: 
        #assign results input to datasource
        results_template_string, field_template_dict, template_args_dict, base_label, infields_list = assign_datasource_values(opts.results_label_img, field_template_dict, template_args_dict, base_label, infields_list, results_label_template_string, results_label_template_variables, 'results_label_template' , 'results_template_string'  )
        base_outputs.append('results_label_template')
    else : results_template_string = ''

    return infields_list, base_outputs, base_label, base_transforms, base_images, template_args_dict, field_template_dict, pvc_template_string, tka_template_string, results_template_string 
 

def assign_datasource_values(label_img, field_template_dict, template_args_dict, base_label, infields_list, label_template_string, label_template_variables, str1, str2 ):
    template_string = label_img[1]
    field_template_dict= dict(field_template_dict.items() + [[str1, label_template_string]] )
    template_args_dict = dict( template_args_dict.items() + [[str1, label_template_variables]] )
    base_label.append(str1)
    infields_list.append(str2)
    return template_string, field_template_dict, template_args_dict, base_label, infields_list 


def printOptions(opts,subject_ids,session_ids,task_ids):
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
    #print "* PVC labels : ", opts.ROIAtlasLabels, "\n"
    #print "* TKA labels : ", opts.ROIAtlasLabels, "\n"
    #print "* Results labels : ", opts.ROIAtlasLabels, "\n"

def set_label_parameters(level, label_img, var , ext ):
    '''Set the label_string and label_variables for the datasource '''
    if level  == "atlas": 
        label_string = "%s"
        label_variables = [[ var ]]
    else: 
        label_string = 'sub-%s/_ses-%s/anat/sub-%s_ses-%s*%s*' + ext
        label_variables = [['sid', 'ses', 'sid', 'ses', var] ]
    return [ label_string, label_variables ]



def run_scan_level(opts,args):  
    if args:
        subjects_ids = args
    else:
        print "\n\n*******ERROR********: \n     The subject IDs are not listed in the command-line \n********************\n\n"
        sys.exit(1)

    if isinstance(opts.sessionList, str):
        opts.sessionList=opts.sessionList.split(',')
    session_ids=opts.sessionList
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
            gm_surf="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_pial."+opts.surf_ext,
            wm_surf="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_smoothwm."+opts.surf_ext,
            mid_surf="sub-%s/_ses-%s/anat/sub-%s_ses-%s_task-%s_midthickness."+opts.surf_ext
        )
        datasourceSurf.inputs.template_args = dict(
            gm_surf = [['sid', 'ses', 'sid', 'ses', 'task']],
            wm_surf = [['sid', 'ses', 'sid', 'ses', 'task']],
            mid_surf = [['sid', 'ses', 'sid', 'ses', 'task']]
        )

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
    wf_pet2mri=reg.get_workflow("to_pet_space", infosource, datasink, opts)
    wf_masking=masking.get_workflow("masking", infosource, datasink, opts)
    if opts.analysis_space == 'mni':
        labelSpace='MNI'
        pet_input_node=wf_pet2mri
        pet_input_file='outputnode.petmni_img_4d'
        pet_mask_node=wf_masking
        pet_mask_file='pvcLabels.LabelsMNI'
        t1="T1Tal"
    elif opts.analysis_space == 'pet':
        labelSpace='PET'
        pet_input_node=wf_init_pet
        pet_input_file='outputnode.pet_center'
        pet_mask_node=wf_pet2mri
        pet_mask_file="outputnode.pvc_label_img_pet"
        t1=t1_type
    elif opts.analysis_space == 't1':
        labelSpace='T1'
        pet_input_node=wf_pet2mri
        pet_input_file='outputnode.petmri_img_4d'
        pet_mask_node=wf_masking
        pet_mask_file='pvcLabels.LabelsT1'
        t1=t1_type
    ###################
    # PET prelimaries #
    ###################
    wf_init_pet=init.get_workflow("pet_prelimaries", infosource, datasink, opts)
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
    workflow.connect(wf_init_pet, 'outputnode.pet_json', wf_masking, "inputnode.pet_json")

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
    if opts.tka_method != None :
        workflow.connect(wf_masking, 'tkaLabels.LabelsT1', wf_pet2mri, "inputnode.tka_label_img_t1")
    if not opts.nopvc:
        workflow.connect(wf_masking, 'pvcLabels.LabelsT1', wf_pet2mri, "inputnode.pvc_label_img_t1")
    out_node_list = [wf_pet2mri] 
    out_img_list = ['outputnode.petmri_img_4d']
    out_img_dim = ['4']

    #############################
    # Partial-volume correction #
    #############################
    if not opts.nopvc :
        pvcNode = pe.Node(interface=pvc.PVCCommand(), name="PVC")
        pvcNode.inputs.fwhm = opts.scanner_fwhm[0]
        pvcNode.inputs.max_iterations = opts.max_iterations
        pvcNode.inputs.tolerance = opts.tolerance
        pvcNode.inputs.nvoxel_to_average=opts.nvoxel_to_average
        pvcNode.inputs.z_fwhm = opts.scanner_fwhm[0]
        pvcNode.inputs.y_fwhm = opts.scanner_fwhm[1]
        pvcNode.inputs.x_fwhm = opts.scanner_fwhm[2]
        pvcNode.inputs.pvc_method = opts.pvc_method
        workflow.connect(pet_input_node, pet_input_file, pvcNode, "input_file") #CHANGE
        workflow.connect(pet_mask_node, pet_mask_file, pvcNode, "mask") #CHANGE

        out_node_list += [pvcNode]
        out_img_list += ['out_file']
        out_img_dim += ['4']

 
    ###########################
    # Tracer kinetic analysis #
    ###########################
    if not opts.tka_method == None:
        if not opts.nopvc: 
            tka_target_wf = pvcNode
            tka_target_img='out_file'
        else : 
            tka_target_wf = pet_input_node # #CHANGE
            tka_target_img= pet_input_file # ##CHANGE
                
        tka_wf=tka.get_tka_workflow("tka", opts)
        workflow.connect(wf_init_pet, 'outputnode.pet_json', tka_wf, "inputnode.header")
        workflow.connect(infosource, 'sid', tka_wf, "inputnode.sid")
        if opts.tka_method in tka_methods:
            workflow.connect(wf_masking, 'resultsLabels.LabelsMNI', tka_wf, "inputnode.mask") #FIXME shouldnt space of labels depend on space of PET image?
        workflow.connect(tka_target_wf, tka_target_img, tka_wf, "inputnode.in_file")
        workflow.connect(tka_wf, "outputnode.out_file", datasink, 'tka')

        if opts.arterial :
            workflow.connect(datasourceArterial, 'arterial_file', tka_wf, "inputnode.reference")
        elif opts.tka_method in tka_methods: 
            workflow.connect(wf_masking, 'tkaLabels.LabelsMNI', tka_wf, "inputnode.reference")
        

        #if opts.tka_type=="voxel" and opts.tka_method == 'srtm':
            #workflow.connect(tka_wf, "outputnode.out_file_t3map", datasink, tka_wf.name+"T3")
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
            print node.name, img
            node_name="results_" + node.name #+ "_" + opts.tka_method
            resultsReport = pe.Node(interface=results.resultsCommand(), name=node_name)
            resultsReport.inputs.dim = dim
            resultsReport.inputs.node = node.name
            workflow.connect(infosource, 'sid', resultsReport, "sub")
            workflow.connect(infosource, 'ses', resultsReport, "ses")
            workflow.connect(infosource, 'task', resultsReport, "task")
            workflow.connect(wf_init_pet, 'outputnode.pet_header', resultsReport, "header")
            workflow.connect(wf_masking, 'brainmask.Labels'+labelSpace, resultsReport, 'mask')
            workflow.connect(node, img, resultsReport, 'in_file')
            workflow.connect(node, img, datasink, node.name)

    ############################
    # Subject-level QC Metrics #
    ############################
    if opts.group_qc :
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
            workflow.connect(pvcNode, "out_file", pvc_qc_metricsNode, 'pvc'  )
            workflow.connect(infosource, 'sid', pvc_qc_metricsNode, "sub")
            workflow.connect(infosource, 'ses', pvc_qc_metricsNode, "ses")
            workflow.connect(infosource, 'task', pvc_qc_metricsNode, "task")

    if opts.test_group_qc:
        tqc_wf = tqc.test_group_qc_scanLevel("scanLevelQC", opts )
        workflow.connect(wf_pet2mri, 'outputnode.petmri_img', tqc_wf, 'inputnode.petmri_img')
        workflow.connect(wf_masking,'brainmask.LabelsT1',tqc_wf,'inputnode.brainmask_t1')
        workflow.connect(infosource, 'cid', tqc_wf, 'inputnode.cid')
        workflow.connect(infosource, 'sid', tqc_wf, 'inputnode.sid')
        workflow.connect(datasourceMINC, t1_type,  tqc_wf, 'inputnode.t1')
        workflow.connect(wf_pet2mri, pet_input_file, tqc_wf, 'inputnode.pet_4d')
        if not ops.tka_methods == None: 
            workflow.connect(wf_masking, 'tkaLabels.Labels'+labelSpace, tqc_wf , 'inputnode.reference_vol')
        workflow.connect(wf_masking, 'resultsLabels.Labels'+labelSpace, tqc_wf, 'inputnode.results_vol')
        workflow.connect(wf_init_pet, 'outputnode.pet_header', tqc_wf, "inputnode.header")
    # #vizualization graph of the workflow
    #workflow.write_graph(opts.targetDir+os.sep+"workflow_graph.dot", graph2use = 'exec')

    printOptions(opts,subjects_ids,session_ids,task_ids)
    #run the work flow
    num_threads=15
    if num_threads > 1 :
        plugin_args = {'n_procs' : num_threads,
                   #'memory_gb' : num_gb, 'status_callback' : log_nodes_cb
                      }
        workflow.run(plugin='MultiProc', plugin_args=plugin_args)
    else : 
        workflow.run()


