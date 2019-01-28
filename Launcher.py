#!/usr/bin/env python
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a hlsearch
import os
import sys
import argparse
import pyminc.volumes.factory as pyminc
import numpy as np
from glob import glob
from re import sub
from Extra.nii2mnc_batch import nii2mnc_batch
from Extra.minc_json_header_batch import create_minc_headers
import re
from optparse import OptionParser
from optparse import OptionGroup
import distutils
from distutils import dir_util

from scanLevel import run_scan_level
from groupLevel import run_group_level

version = "1.0"
global spaces
spaces=['pet', 't1', 'stereo']

def set_labels(opts, roi_label, masks):
    out={}
    labels={"pvc":opts.pvc_labels, "tka":opts.tka_labels, "results":opts.results_labels}
    for name, item in masks.items():
        mask_type  = item[0]
        mask_value = item[1]
        
        if labels[name] != None:
            out[name]=labels[name]
        else: # mask_type == 'other' or mask_type == 'roi-user':
            out[name] = None #label_values
    return out


def get_opt_list(option,opt,value,parser):
    print(value)
    setattr(parser.values,option.dest,value.split(','))

# def printStages(opts,args):

############################################
# Define dictionaries for default settings #
############################################
#Set defaults for label
roi_label={} 
animal_WM=[73, 45, 83, 59, 30, 17, 105, 57]
animal_CER=[67,76]
animal_GM=[218,219,210,211,8,4,2,6]
animal_sGM=[14,16,11,12,53,39,102,203]
animal_labels=animal_WM + animal_CER + animal_GM + animal_sGM 
roi_label["results"]={  
        "roi-user":[],
        "icbm152":[39,53,16,14,25,72],
        "civet":[1,2,3,4],
        "animal":animal_GM+animal_sGM, 
        "atlas":[]}
roi_label["tka"]={  
        "roi-user":[1],
        "icbm152":[39,53,16,14,25,72],
        "civet":[3],
        "atlas":[3],
        "animal":animal_CER}
roi_label["pvc"]={
        "roi-user":[],
        "icbm152":[39,53,16,14,25,72],
        "civet":[2,3,4],
        "animal":animal_labels,
        "atlas":[]}

#Default FWHM for PET scanners
pet_scanners={"HRRT":[2.5,2.5,2.5],"HR+":[6.5,6.5,6.5]} #FIXME should be read from a separate .json file and include lists for non-isotropic fwhm

internal_cls_methods=["antsAtropos"]
def check_masking_options(opts, label_img, label_template, label_space):
    '''
    Inputs:
        opts            user defined inputs to program using configparser
        label_img       the label that describes the type of image we're dealing with
        label-space     the coordinate space of the the image
    Outputs: 
        label_type      label type tells you what kind of labled image we're dealing with. there are several
                        possibilities based on the coordinate space of the image (label_space): roi-user, civet, animal, other.
    '''
    print("Label img:", label_img, "Label template:", label_template)
    print( "Check masking options:",os.path.exists(label_img) ); 
    #if os.path.exists(opts.sourceDir + os.sep + label_img[0]):
    if os.path.exists(label_img):
    # 1) Atlas 
        label_type ="atlas"
        #if os.path.exists(opts.sourceDir + os.sep + label_img[1]) : 
        if label_template != None :
            if os.path.exists(label_template) : 
                label_type="atlas-template"
    elif label_img in internal_cls_methods :
    # 2) Internal classification metion
        label_type = 'internal_cls'
        label_space="stereo"
    elif type(label_img) == str:
    # 3) String that defines user classification
        label_type='user_cls'
    else : 
        print "Label error: ", label_img
        exit(1)

    return label_type, label_space

def split_label_img(label_img_str):
    label_img_list = label_img_str.split(',')
    if len(label_img_list) == 1 : label_img_list += [None]

    return label_img_list

if __name__ == "__main__":
    usage = "usage: "
    parser = OptionParser(usage=usage,version=version)
    group= OptionGroup(parser,"File options (mandatory)")
    group.add_option("-s","--source","--sourcedir",dest="sourceDir",  help="Absolute path for input file directory")
    group.add_option("-t","--target","--targetdir",dest="targetDir",type='string', help="Absolute path for directory where output data will be saved in")

    group.add_option("--radiotracer","--acq",dest="acq",type='string', default='', help="Radiotracer")
    group.add_option("-r","--rec",dest="rec",type='string', default='', help="Reconstruction algorithm")
    group.add_option("","--sessions",dest="sessionList",help="Comma-separated list of conditions or scans",type='string',action='callback',callback=get_opt_list)
    group.add_option("","--tasks",dest="taskList",help="Comma-separated list of conditions or scans",type='string',action='callback',callback=get_opt_list)
    group.add_option("","--runs",dest="runList",help="Comma-separated list of runs",type='string',action='callback',callback=get_opt_list)
    parser.add_option_group(group)      

    ###############
    # Information #
    ###############
    group= OptionGroup(parser,"Options to supplement PET header information")
    group.add_option("","--halflife",dest="halflife",help="Half-life of radio isotope (in seconds).",type='float', default=0)
    parser.add_option_group(group)      

    #############################
    # MRI Preprocessing Options #
    #############################
    group= OptionGroup(parser,"MRI preprocessing options")
    group.add_option("--user-t1mni", dest="user_t1mni", default=False, action='store_true', help="Use user provided transform from MRI to MNI space" ) 
    group.add_option("--user-brainmask", dest="user_brainmask", default=False, action='store_true', help="Use user provided brain mask" ) 
    group.add_option("","--coregistration-method",dest="mri_coreg_method", help="Method to use to register MRI to stereotaxic template", type='string', default="minctracc")  
    group.add_option("","--brain-extraction-method",dest="mri_brain_extract_method", help="Method to use to extract brain mask from MRI", type='string', default="beast")  
    group.add_option("","--segmentation-method",dest="mri_segmentation_method", help="Method to segment mask from MRI", type='string', default='ANTS' ) 
    group.add_option("--beast-library-dir", dest="beast_library_dir",type='string',help="Directory to Beast library",default="/opt/beast-library-1.0")
    parser.add_option_group(group)      

    ###################
    # Surface Options #
    ###################
    group= OptionGroup(parser,"Surface options")
    group.add_option("--surf",dest="use_surfaces",action='store_true', default=False,help="Uses surfaces")
    group.add_option("--surf-label",dest="surface_label", default='*', help="Label string to identify surface ROI .txt file")
    group.add_option("--surf-space",dest="surface_space",type='string',default="icbm152", help="Set space of surfaces from : \"pet\", \"t1\", \"icbm152\" (default=icbm152)")
    group.add_option("--surf-ext",dest="surf_ext",type='string',help="Extension to use for surfaces",default='obj')
    parser.add_option_group(group)      

    ######################
    # Additional Options #
    ######################
    group= OptionGroup(parser,"File options (Optional)")
    group.add_option("--no-group-level",dest="run_group_level",action='store_false', default=True, help="Run group level analysis")
    group.add_option("--no-scan-level",dest="run_scan_level",action='store_false', default=True, help="Run scan level analysis")

    group.add_option("--img-ext",dest="img_ext",type='string',help="Extension to use for images.",default='mnc')
    group.add_option("--analysis-space",dest="analysis_space",help="Coordinate space in which PET processing will be performed (Default=pet)",default='pet', choices=spaces)
    group.add_option("--threads",dest="num_threads",type='int',help="Number of threads to use. (defult=1)",default=1)
    
    file_dir, fn =os.path.split( os.path.abspath(__file__) )
    group.add_option("--stereotaxic-template", dest="template",type='string',help="Template image in stereotaxic space",default=file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_t1_tal_nlin_asym_09c.mnc")
    group.add_option("","--masking-only",dest="masking_only",help="Stop scan level processing after masking", action='store_true', default=False)
    group.add_option("","--coregistration-only",dest="coregistration_only",help="Stop scan level processing after coregistration", action='store_true', default=False)
    group.add_option("","--initialize-only",dest="initialize_only",help="Stop scan level processing after PET initialization", action='store_true', default=False)
    parser.add_option_group(group)      


    ###################
    # Masking options #
    ###################
    label_space_help="Coordinate space of labeled image to use for TKA. Options: [pet/t1/stereo] "
    label_img_help="Options: 1. ICBM MNI 152 atlas: <path/to/labeled/atlas>, 2. Stereotaxic atlas and template: path/to/labeled/atlas /path/to/atlas/template 3. Internal classification method (" + ', '.join(internal_cls_methods) + ') 4. String that identifies labels in anat/ directory to be used as mask' 
    #PVC
    group= OptionGroup(parser,"Masking options","PVC")
    group.add_option("","--pvc-label-space",dest="pvc_label_space",help=label_space_help,default='stereo', choices=spaces)
    group.add_option("","--pvc-label-img",dest="pvc_label_img",help=label_img_help, type='string', default='antsAtropos')
    group.add_option("","--pvc-label-template",dest="pvc_label_template",help="Absolute path to template for stereotaxic atlas", type='string', default=None)
    group.add_option("","--pvc-label",dest="pvc_labels",help="Label values to use for pvc", type='string',action='callback',callback=get_opt_list,default=[] )
    group.add_option("","--pvc-label-erosion",dest="pvc_erode_times",help="Number of times to erode label", type='int', default=0 )
    group.add_option("","--pvc-labels-brain-only",dest="pvc_labels_brain_only",help="Mask pvc labels with brain mask",action='store_true',default=False)
    group.add_option("","--pvc-labels-ones-only",dest="pvc_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    group.add_option("","--pvc-labels-per-pet",dest="pvc_labels_per_pet",help="Mask pvc labels with brain mask",action='store_true',default=False)
    parser.add_option_group(group)

    # Quantification
    group= OptionGroup(parser,"Masking options","Quantification")
    group.add_option("","--tka-label-space",dest="tka_label_space",help=label_space_help,default='stereo', choices=spaces)
    group.add_option("","--tka-label-img",dest="tka_label_img", help=label_img_help, type='string',default='antsAtropos')
    group.add_option("","--tka-label-template",dest="tka_label_template",help="Absolute path to template for stereotaxic atlas", type='string', default=None)
    group.add_option("","--tka-label",dest="tka_labels",help="Label values to use for TKA", type='string',action='callback',callback=get_opt_list,default=[] )
    group.add_option("","--tka-label-erosion",dest="tka_erode_times",help="Number of times to erode label", type='int', default=0 )
    group.add_option("","--tka-labels-brain-only",dest="tka_labels_brain_only",help="Mask tka labels with brain mask",action='store_true',default=False)
    group.add_option("","--tka-labels-ones-only",dest="tka_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    parser.add_option_group(group)

    #Results
    group= OptionGroup(parser,"Masking options","Results")
    group.add_option("","--no-results-report",dest="no_results_report",help="Don't calculate descriptive stats for results ROI.",action='store_true',default=False)
    group.add_option("","--results-label-space", dest="results_label_space",help=label_space_help,default='stereo', choices=spaces)
    group.add_option("","--results-label-img", dest="results_label_img",help=label_img_help, type='string',default='antsAtropos')
    group.add_option("","--results-label-template",dest="results_label_template",help="Absolute path to template for stereotaxic atlas", type='string', default=None)
    group.add_option("","--results-label",dest="results_labels",help="Label values to use for results", type='string',action='callback',callback=get_opt_list,default=[] )
    group.add_option("","--results-label-erosion",dest="results_erode_times",help="Number of times to erode label", type='int',default=0 )
    group.add_option("","--results-labels-brain-only",dest="results_labels_brain_only",help="Mask results labels with brain mask",action='store_true',default=False)
    group.add_option("","--results-labels-ones-only",dest="results_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    parser.add_option_group(group)

    ##########################
    # Coregistration Options #
    ##########################
    group= OptionGroup(parser,"Coregistation options")
    group.add_option("--coreg-method", dest="coreg_method",type='string',help="Coregistration method: minctracc, ants (default=minctracc)", default="minctracc")
    group.add_option("","--coregistration-brain-mask",dest="coregistration_brain_mask",help="Target T1 mask for coregistration", action='store_false', default=True)
    group.add_option("","--second-pass-no-mask",dest="no_mask",help="Do a second pass of coregistration without masks.", action='store_false', default=True)
    group.add_option("","--slice-factor",dest="slice_factor",help="Value (between 0. to 1.) that is multiplied by the maximum of the slices of the PET image. Used to threshold slices. Lower value means larger mask.", type='float', default=0.25)
    group.add_option("","--total-factor",dest="total_factor",help="Value (between 0. to 1.) that is multiplied by the thresholded means of each slice.",type='float', default=0.333)
    parser.add_option_group(group)

    ###############
    # PVC options #
    ###############
    group= OptionGroup(parser,"PVC Options")
    group.add_option("","--no-pvc",dest="nopvc",help="Don't run PVC.",action='store_true',default=False)
    group.add_option("","--pvc-method",dest="pvc_method",help="Method for PVC.",type='string', default=None)
    group.add_option("","--pet-scanner",dest="pet_scanner",help="FWHM of PET scanner.",type='str', default=None)
    group.add_option("","--fwhm","--pvc-fwhm",dest="scanner_fwhm",help="FWHM of PET scanner (z,y,x).",type='float', nargs=3, default=None)
    group.add_option("","--pvc-max-iterations",dest="max_iterations",help="Maximum iterations for PVC method.",type='int', default=10)
    group.add_option("","--pvc-tolerance",dest="tolerance",help="Tolerance for PVC algorithm.",type='float', default=0.001)
    group.add_option("","--pvc-denoise-fwhm",dest="denoise_fwhm",help="FWHM of smoothing filter (for IdSURF).",type='float', default=1)
    group.add_option("","--pvc-nvoxel-to-average",dest="nvoxel_to_average",help="Number of voxels to average over (for IdSURF).",type='int', default=64)
    parser.add_option_group(group)

    #TKA Options
    group= OptionGroup(parser,"Quantification options")
    group.add_option("","--tka-method",dest="tka_method",help="Method for performing tracer kinetic analysis (TKA): lp, pp, srtm.",type='string', default=None)
    group.add_option("","--k2",dest="tka_k2",help="With reference region input it may be necessary to specify also the population average for regerence region k2",type='float', default=None)
    group.add_option("","--thr",dest="tka_thr",help="Pixels with AUC less than (threshold/100 x max AUC) are set to zero. Default is 0%",type='float', default=None)
    group.add_option("","--max",dest="tka_max",help="Upper limit for Vt or DVR values; by default max is set pixel-wise to 10 times the AUC ratio.",type='float', default=None)
    group.add_option("","--min",dest="tka_min",help="Lower limit for Vt or DVR values, 0 by default",type='float', default=None)
    group.add_option("","--t3max",dest="tka_t3max",help="Upper limit for theta3, 0.01 by default",type='float', default=0.01)
    group.add_option("","--t3min",dest="tka_t3min",help="Lower limit for theta3, 0.001 by default",type='float', default=0.001)
    group.add_option("","--nBF",dest="tka_nBF",help="Number of basis functions.",type='int', default=100)
    group.add_option("","--filter",dest="tka_filter",help="Remove parametric pixel values that over 4x higher than their closest neighbours.",action='store_const',const=True, default=None)
    group.add_option("","--reg-end",dest="tka_end",help="By default line is fit to the end of data. Use this option to enter the fit end time (in min).",type='float', default=None)
    group.add_option("","--y-int",dest="tka_v",help="Y-axis intercepts time -1 are written as an image to specified file.",type='string', default=None)
    group.add_option("","--num",dest="tka_n",help="Numbers of selected plot data points are written as an image.",type='string', default=None)
    group.add_option("","--Ca",dest="tka_Ca",help="Concentration of native substrate in arterial plasma (mM).",type='float', default=None)
    group.add_option("","--LC",dest="tka_LC",help="Lumped constant in MR calculation; default is 1.0.",type='float', default=None)
    group.add_option("","--density",dest="tka_density",help="Tissue density in MR calculation; default is 1.0 g/ml.",type='float', default=None)
    group.add_option("","--arterial",dest="arterial",help="Use arterial input input.", action='store_true', default=False)
    group.add_option("","--start-time",dest="tka_start_time",help="Start time of either regression in MTGA or averaging time for SUV.",type='float', default=None)
    group.add_option("","--end-time",dest="tka_end_time",help="End time for SUV average.",type='float', default=None)
    group.add_option("","--tka-type",dest="tka_type",help="Type of tka analysis: voxel or roi.",type='string', default="voxel")
    parser.add_option_group(group)

    #Quality Control 
    qc_opts = OptionGroup(parser,"Quality control options")
    qc_opts.add_option("","--dashboard",dest="dashboard",help="Generate a dashboard.", action='store_const', const=True, default=False)
    qc_opts.add_option("","--no-group-qc",dest="group_qc",help="Don't perform quantitative group-wise quality control.", action='store_const', const=False, default=True)  #FIXME Add to options
    qc_opts.add_option("","--test-group-qc",dest="test_group_qc",help="Perform simulations to test quantitative group-wise quality control.", action='store_const', const=True, default=False)
    parser.add_option_group(qc_opts)

    #Results reporting
    qc_opts = OptionGroup(parser,"Results reporting options")
    qc_opts.add_option("","--no-group-stats",dest="group_stats",help="Don't calculate quantitative group-wise descriptive statistics.", action='store_const', const=False, default=True)  #FIXME Add to options
    parser.add_option_group(qc_opts)

    #
    group= OptionGroup(parser,"Command control")
    group.add_option("-v","--verbose",dest="verbose",help="Write messages indicating progress.",action='store_true',default=False)
    parser.add_option_group(group)
    group= OptionGroup(parser,"Pipeline control")
    group.add_option("","--print-scan",dest="pscan",help="Print the pipeline parameters for the scan.",action='store_true',default=False)
    group.add_option("","--print-stages",dest="pstages",help="Print the pipeline stages.",action='store_true',default=False)
    parser.add_option_group(group)

    (opts, args) = parser.parse_args()
   
   
    ############################
    #Automatically set sessions#
    ############################ 
    if args == [] :
        args = [ sub('sub-', '',os.path.basename(f)) for f in glob(opts.sourceDir+os.sep+"sub-*") ]
        print("Warning : No subject arguments passed. Will run all subjects found in source directory "+ opts.sourceDir)
        print("Subjects:", ' '.join( args))
    
    if opts.sessionList == None :
        opts.sessionList =np.unique( [ sub('_','',sub('ses-', '',os.path.basename(f))) for f in glob(opts.sourceDir+os.sep+"**/*ses-*") ])
        print("Warning : No session variables. Will run all sessions found in source directory "+ opts.sourceDir)
        print("Sessions:", ' '.join( opts.sessionList))

    #########################
    #Automatically set tasks#
    #########################
    if opts.taskList == None :
        for f in glob(opts.sourceDir+os.sep+"**/**/pet/*task-*") :
            g=os.path.splitext(os.path.basename(f))[0]
            task_list = [ i  for i in   g.split('_') if 'task-' in i ]
            if task_list == [] : continue

            if opts.taskList == None : opts.taskList = []
            task = re.sub('task-', '', task_list[0])
            opts.taskList.append(task)

        if opts.taskList != None : 
            opts.taskList = np.unique(opts.taskList)
        else : 
            opts.taskList =[]
        
        print("Warning : No task variables. Will run all sessions found in source directory "+ opts.sourceDir)
        print("Task:", ' '.join( opts.taskList))
    
    ########################
    #Automatically set runs#
    ########################
    if opts.runList == None :
        for f in glob(opts.sourceDir+os.sep+"**/**/pet/*run-*") :
            g=os.path.splitext(os.path.basename(f))[0]
            task_list = [ i  for i in   g.split('_') if 'run-' in i ]
            if task_list == [] : continue

            if opts.runList == None : opts.runList = []
            run = re.sub('run-', '', task_list[0])
            opts.runList.append(run)

        if opts.runList != None : 
            opts.runList = np.unique(opts.runList)
        else : 
            opts.runList =[]
        
        print("Warning : No run variables. Will process all runs found in source directory "+ opts.sourceDir)
        print("Runs:", ' '.join( opts.runList))
    opts.extension='mnc'

##########################################################
# Check inputs to make sure there are no inconsistencies #
##########################################################
    if not opts.sourceDir or not opts.targetDir: 
        print "\n\n*******ERROR******** \n     You must specify --sourcedir, --targetdir \n********************\n"
        parser.print_help()
        sys.exit(1)

    #If necessary, correct MNI space names
    #Change label space to icbm152 if it was specified as some variant of MNI and 152
    #mni_space_names =  ["MNI", "mni", "MNI152", "mni152"]
    #if opts.pvc_label_space in mni_space_names: opts.pvc_label_space = "icbm152"
    #if opts.tka_label_space in mni_space_names: opts.tka_label_space = "icbm152"
    #if opts.results_label_space in mni_space_names: opts.results_label_space = "icbm152"

    #Check inputs for PVC masking 
    #opts.pvc_label_img = split_label_img(opts.pvc_label_img)
    opts.pvc_label_type, opts.pvc_label_space = check_masking_options(opts, opts.pvc_label_img, opts.pvc_label_template, opts.pvc_label_space)
    #Check inputs for TKA masking
    #opts.tka_label_img = split_label_img(opts.tka_label_img)
    opts.tka_label_type, opts.tka_label_space = check_masking_options(opts, opts.tka_label_img, opts.tka_label_template, opts.tka_label_space)
    #Check inputs for results masking
    #opts.results_label_img = split_label_img(opts.results_label_img)
    opts.results_label_type, opts.results_label_space = check_masking_options(opts, opts.results_label_img, opts.results_label_template, opts.results_label_space)
    #Set default label for atlas ROI
    masks={ "tka":[opts.tka_label_type, opts.tka_label_img], "pvc":[opts.pvc_label_type, opts.pvc_label_img], "results": [opts.results_label_type, opts.results_label_img] }

    roi_label = set_labels(opts,roi_label, masks)  
    #If no label given by user, set default label for PVC mask
    if(opts.pvc_labels ==None): opts.pvc_labels = roi_label["pvc"]
    #If no label given by user, set default label for TKA mask
    if(opts.tka_labels ==None): opts.tka_labels = roi_label["tka"]
    #Set default label for results mask
    if(opts.results_labels ==None): opts.results_labels = roi_label["results"]
    
    ###Check PVC options and set defaults if necessary
    if opts.pvc_method != None : 
        if  opts.scanner_fwhm == None and opts.pet_scanner == None :
            print "Error: You must either\n\t1) set the desired FWHM of the PET scanner using the \"--pvc-fwhm <float>\" option, or"
            print "\t2) set the PET scanner type using the \"--pet-scanner <string>\" option."
            print "\tSupported PET scanners to date are the " + ', '.join(pet_scanners.keys())
            exit(1)
       
        if not opts.pet_scanner == None:
            if opts.pet_scanner in pet_scanners.keys():
                opts.scanner_fwhm = pet_scanners[opts.pet_scanner]
            else:
                print "Error: The PET scanner \"" + opts.pet_scanner + "\"is not supported. You can"
                print "\t1) add this PET scanner to the \"PET_scanner.json\" file, or"
                print "\t2) set the FWHM of the scanner manually using the \"--scanner_fwhm <z fwhm> <y fwhm> <x fwhm>\" option."
                exit(1)

    opts.targetDir = os.path.normpath(opts.targetDir)
    opts.sourceDir = os.path.normpath(opts.sourceDir)
    opts.preproc_dir='preproc'
    
    ############################################
    # Create BIDS-style header for MINC inputs #
    ############################################
    create_minc_headers( opts.sourceDir )
    
    #######################################
    ### Convert NII to MINC if necessary. # 
    #######################################
    opts.json = nii2mnc_batch(opts.sourceDir)	
    
    #################
    # Launch APPIAN #
    #################
    if opts.pscan:
        printScan(opts,args)
    elif opts.pstages:
        printStages(opts,args)
    else :
        if opts.run_scan_level:
            run_scan_level(opts,args)
        if opts.run_group_level:
            run_group_level(opts,args)

