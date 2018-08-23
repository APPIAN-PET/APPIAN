#!/usr/bin/env python
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a hlsearch
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
import nibabel
import nipype

from groupLevel import run_group_level
from scanLevel import run_scan_level

from optparse import OptionParser
from optparse import OptionGroup

from Extra.conversion import  nii2mncCommand

from Masking import masking as masking
import Registration.registration as reg
import Initialization.initialization as init
import Partial_Volume_Correction.pvc as pvc 
import Results_Report.results as results
import Tracer_Kinetic.tka as tka
from Tracer_Kinetic import reference_methods
import Quality_Control.qc as qc
import Test.test_group_qc as tqc
import Quality_Control.dashboard as dash
version = "1.0"


def set_default_atlas_label(opts, roi_label, masks):
    #The default setting for "atlas" ROI needs to be set.
    #This is done by finding the unique values (with get_mask_list)
    #in the atlas volume
    out={}
    labels={"pvc":opts.pvc_labels, "tka":opts.tka_labels, "results":opts.results_labels}
    for name, item in masks.items():
        mask_type  = item[0]
        mask_value = item[1]
        if labels[name] != None:
            out[name]=labels[name]
        elif mask_type == 'other' or mask_type == 'roi-user':
            label_values = get_mask_list(opts.sourceDir, mask_value )
            out[name] = label_values
        else:
            out[name] = roi_label[name][mask_type] 
    return out

def get_mask_list(sourceDir, ROIMask ):
    gen = os.walk(sourceDir)
    for dirName, subdirList, fileList in gen: 
        for f in fileList: 
            if ROIMask[0] in f : 
                #Load in volume and get unique values
                mask= pyminc.volumeFromFile(dirName+os.sep+f)
                mask_flat=mask.data.flatten()
                label=[ str(int(round(i))) for i in np.unique(mask_flat) ]
                if 0 in label :  label.remove(0)
                return(label)
    return([1])

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

# def printScan(opts,args):
def check_masking_options(opts, label_img, label_space):
    '''
    Inputs:
        opts            user defined inputs to program using configparser
        label_img       the label that describes the type of image we're dealing with
        label-space     the coordinate space of the the image
    Outputs: 
        label_type      label type tells you what kind of labled image we're dealing with. there are several
                        possibilities based on the coordinate space of the image (label_space): roi-user, civet, animal, other.
    '''
    d={ "native":{  "string":"roi-user"},
        "icbm152":{ "string":"roi-user",
                    "cls":"civet",
                    "seg":"animal",
                    "icbm152":"other", #FIXME : Does this make sense? Shouldnt the user provide the path to the atlas and nd not just specify icbm152?
		    "atlas":"other"},
        "other":{   "string":"roi-user",
                    "atlas":'other'}
    }
    if os.path.exists(opts.sourceDir + os.sep + label_img[0]):
        var ="atlas"
    elif type(label_img[0]) == str:
        if label_img[0] == "cls":  
            var = "cls"
        elif label_img[0] == "seg":  
            var = "seg"
        else: 
            var ="string"       
    else: 
        print "Label error: ", label_img, label_space
        exit(1)

    try: 
        label_type =  d[label_space][var]
    except KeyError:
        print "Label Error: "+label_space+" is not compatible with "+label_img[0]
        exit(1)
    
    if label_space == "other":
        if not os.path.exists(label_img[0]) or not os.path.exists(label_img[1]) :
            print "Option \"--label_space other\" requires path to labeled atlas and the image template for the atlas."
            exit(1)

    return label_type

def split_label_img(label_img_str):
    label_img_list = label_img_str.split(',')
    if len(label_img_list) == 1 : label_img_list += [None]

    return label_img_list

if __name__ == "__main__":
    usage = "usage: "
    parser = OptionParser(usage=usage,version=version)
    group= OptionGroup(parser,"File options (mandatory)")
    group.add_option("-s","--source","--sourcedir",dest="sourceDir",  help="Input file directory")
    group.add_option("-t","--target","--targetdir",dest="targetDir",type='string', help="Directory where output data will be saved in")
    
    group.add_option("--scan-level",dest="run_scan_level",action='store_true', default=False, help="Run scan level analysis")

    group.add_option("--group-level",dest="run_group_level",action='store_true', default=False, help="Run group level analysis")
    group.add_option("--radiotracer","--acq",dest="acq",type='string',help="Radiotracer")
    group.add_option("-r","--rec",dest="rec",type='string',help="Reconstruction algorithm")
    group.add_option("--surf",dest="use_surfaces",action='store_true', default=False,help="Uses surfaces")
    group.add_option("--surf-space",dest="surface_space",type='string',default="icbm152", help="Set space of surfaces from : \"pet\", \"t1\", \"icbm152\" (default=icbm152)")
    group.add_option("--img-ext",dest="img_ext",type='string',help="Extension to use for images.",default='mnc')
    group.add_option("--surf-ext",dest="surf_ext",type='string',help="Extension to use for surfaces",default='obj')
    group.add_option("--threads",dest="num_threads",type='int',help="Number of threads to use. (defult=1)",default=1)

    #group.add_option("-c","--civetdir",dest="civetDir",  help="Civet directory")
    parser.add_option_group(group)      

    group= OptionGroup(parser,"Scan options","***if not, only baseline condition***")
    group.add_option("","--sessions",dest="sessionList",help="comma-separated list of conditions or scans",type='string',action='callback',callback=get_opt_list,default='baseline')
    group.add_option("","--tasks",dest="taskList",help="comma-separated list of conditions or scans",type='string',action='callback',callback=get_opt_list,default='')
    parser.add_option_group(group)      

 
    # Parse user options
    # Label options
    #
    #   Type:               PVC, TKA, Results
    #   Labeled Image:      CIVET Classify, Animal, ICBM152, Stereotaxic Atlas, Manual 
    #   Template:           None,           None,   ICBM152, User Selected,     None
    #   Labels:             
    #   --[type]-label-space [CIVET/ANIMAL/ICBM152/Stereotaxic/Manual]
    #   1) T1 Native:  --[type]-label-img "classify" / "animal" / "roi string" 
    #   2) ICBM152: --[type]-label-img  path/to/labeled/atlas
    #   2) Other:   --[type]-label-img  path/to/labeled/atlas path/to/labeled/template
    #   --[type]-label

    group= OptionGroup(parser,"Masking options","Tracer Kinetic Analysis")
    label_space_help="Coordinate space of labeled image to use for TKA. Options: [native/icbm152/other] "
    label_img_help="Options: 1. Labeled image from CIVET: \'civet\'/\'animal\'/\'label string\', 2. ICBM MNI 152 atlas: <path/to/labeled/atlas>, 3. Stereotaxic atlas and template: path/to/labeled/atlas /path/to/atlas/template"

    #PVC
    parser.add_option_group(group)
    group= OptionGroup(parser,"Masking options","PVC")
    group.add_option("","--pvc-label-space",dest="pvc_label_space",help=label_space_help,default='icbm152')
    group.add_option("","--pvc-label-img",dest="pvc_label_img",help=label_img_help, nargs=1, type='string', default='cls')
    group.add_option("","--pvc-label",dest="pvc_labels",help="Label values to use for pvc", type='string',action='callback',callback=get_opt_list,default=None )
    group.add_option("","--pvc-label-erosion",dest="pvc_erode_times",help="Number of times to erode label", type='int', default=0 )
    group.add_option("","--pvc-labels-brain-only",dest="pvc_labels_brain_only",help="Mask pvc labels with brain mask",action='store_true',default=False)
    group.add_option("","--pvc-labels-ones-only",dest="pvc_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    parser.add_option_group(group)

    # Tracer Kinetic Analysis
    group= OptionGroup(parser,"Masking options","TKA")
    group.add_option("","--tka-label-space",dest="tka_label_space",help=label_space_help,default='icbm152')
    group.add_option("","--tka-label-img",dest="tka_label_img",help=label_img_help, type='string',nargs=1,default='cls')
    group.add_option("","--tka-label",dest="tka_labels",help="Label values to use for TKA", type='string',action='callback',callback=get_opt_list,default=None )
    group.add_option("","--tka-label-erosion",dest="tka_erode_times",help="Number of times to erode label", type='int', default=0 )
    group.add_option("","--tka-labels-brain-only",dest="tka_labels_brain_only",help="Mask tka labels with brain mask",action='store_true',default=False)
    group.add_option("","--tka-labels-ones-only",dest="tka_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    parser.add_option_group(group)
    
    #Results
    group= OptionGroup(parser,"Masking options","Results")
    group.add_option("","--no-results-report",dest="no_results_report",help="Don't calculate descriptive stats for results ROI.",action='store_true',default=False)
    group.add_option("","--results-label-space", dest="results_label_space",help=label_space_help,default='icbm152')
    group.add_option("","--results-label-img", dest="results_label_img",help=label_img_help, type='string',nargs=1,default='cls')
    group.add_option("","--results-label",dest="results_labels",help="Label values to use for results", type='string',action='callback',callback=get_opt_list,default=None )
    group.add_option("","--results-label-erosion",dest="results_erode_times",help="Number of times to erode label", type='int',default=0 )
    group.add_option("","--results-labels-brain-only",dest="results_labels_brain_only",help="Mask results labels with brain mask",action='store_true',default=False)
    group.add_option("","--results-labels-ones-only",dest="results_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    parser.add_option_group(group)
    
    ##########################
    # Coregistration Options #
    ##########################
    group= OptionGroup(parser,"Coregistation options")
    group.add_option("","--coregistration-target-mask",dest="coregistration_target_mask",help="Target T1 mask for coregistration: \'skull\' or \'mask\'",type='string', default='skull')
    group.add_option("","--coregistration-target-image",dest="coregistration_target_image",help="Target T1 for coregistration: \'raw\' or \'nuc\'",type='string', default='nuc')
    group.add_option("","--second-pass-no-mask",dest="no_mask",help="Do a second pass of coregistration without masks.", action='store_false', default=True)
    group.add_option("","--slice-factor",dest="slice_factor",help="Value (between 0. to 1.) that is multiplied by the maximum of the slices of the PET image. Used to threshold slices. Lower value means larger mask.", type='float', default=0.25)
    group.add_option("","--total-factor",dest="total_factor",help="Value (between 0. to 1.) that is multiplied by the thresholded means of each slice.",type='float', default=0.333)
    parser.add_option_group(group)

    ###############
    # PVC options #
    ###############
    group= OptionGroup(parser,"PVC Options")
    group.add_option("","--no-pvc",dest="nopvc",help="Don't run PVC.",action='store_true',default=False)
    group.add_option("","--pvc-method",dest="pvc_method",help="Method for PVC.",type='string', default="GTM")
    group.add_option("","--pet-scanner",dest="pet_scanner",help="FWHM of PET scanner.",type='str', default=None)
    group.add_option("","--fwhm","--pvc-fwhm",dest="scanner_fwhm",help="FWHM of PET scanner (z,y,x).",type='float', default=None)
    group.add_option("","--pvc-max-iterations",dest="max_iterations",help="Maximum iterations for PVC method.",type='int', default=10)
    group.add_option("","--pvc-tolerance",dest="tolerance",help="Tolerance for PVC algorithm.",type='float', default=0.001)
    group.add_option("","--pvc-lambda",dest="lambda_var",help="Lambda for PVC algorithm (smoothing parameter for anisotropic diffusion)",type='float', default=1)
    group.add_option("","--pvc-denoise-fwhm",dest="denoise_fwhm",help="FWHM of smoothing filter.",type='float', default=1)
    group.add_option("","--pvc-nvoxel-to-average",dest="nvoxel_to_average",help="Number of voxels to average over.",type='int', default=64)
    parser.add_option_group(group)

    #TKA Options
    group= OptionGroup(parser,"Tracer Kinetic analysis options")
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
    group.add_option("","--start-time",dest="tka_start_time",help="Start time of either regression in MTGA or averaging time for SUV.",type='float', default=0)
    group.add_option("","--end-time",dest="tka_end_time",help="End time for SUV average.",type='float', default=0)
    group.add_option("","--body-weight",dest="body_weight",help="Either name of subject body weight (kg) in header or path to .csv file containing subject names and body weight (separated by comma).",type='string', default="Patient_Weight")
    group.add_option("","--radiotracer-dose",dest="radiotracer_dose",help="Either name of subject's injected radiotracer dose (MBq) in header or path to .csv file containing subject names and injected radiotracer dose (MBq).",type='string', default="injection_dose")
    group.add_option("","--tka-type",dest="tka_type",help="Type of tka analysis: voxel or roi.",type='string', default="voxel")
    parser.add_option_group(group)

    #Quality Control 
    qc_opts = OptionGroup(parser,"Quality control options")
    qc_opts.add_option("","--group-qc",dest="group_qc",help="Perform quantitative group-wise quality control.", action='store_const', const=True, default=False)  #FIXME Add to options
    qc_opts.add_option("","--test-group-qc",dest="test_group_qc",help="Perform simulations to test quantitative group-wise quality control.", action='store_const', const=True, default=False)
    parser.add_option_group(qc_opts)

    #Results reporting
    qc_opts.add_option("","--group-stats",dest="group_stats",help="Calculate quantitative group-wise descriptive statistics.", action='store_const', const=True, default=True)  #FIXME Add to options
    qc_opts.add_option("","--dashboard",dest="dashboard",help="Generate a dashboard.", action='store_const', const=True, default=True)


    #
    group= OptionGroup(parser,"Command control")
    group.add_option("-v","--verbose",dest="verbose",help="Write messages indicating progress.",action='store_true',default=False)
    parser.add_option_group(group)
    group= OptionGroup(parser,"Pipeline control")
    group.add_option("","--run",dest="prun",help="Run the pipeline.",action='store_true',default=True)
    group.add_option("","--fake",dest="prun",help="do a dry run, (echo cmds only).",action='store_false',default=True)
    group.add_option("","--print-scan",dest="pscan",help="Print the pipeline parameters for the scan.",action='store_true',default=False)
    group.add_option("","--print-stages",dest="pstages",help="Print the pipeline stages.",action='store_true',default=False)
    parser.add_option_group(group)

    (opts, args) = parser.parse_args()

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
    mni_space_names =  ["MNI", "mni", "MNI152", "mni152"]
    if opts.pvc_label_space in mni_space_names: opts.pvc_label_space = "icbm152"
    if opts.tka_label_space in mni_space_names: opts.tka_label_space = "icbm152"
    if opts.results_label_space in mni_space_names: opts.results_label_space = "icbm152"
    
    #Check inputs for PVC masking 
    opts.pvc_label_img = split_label_img(opts.pvc_label_img)

    pvc_label_type= check_masking_options(opts, opts.pvc_label_img, opts.pvc_label_space)
    print pvc_label_type
    #Check inputs for TKA masking
    opts.tka_label_img = split_label_img(opts.tka_label_img)
    tka_label_type = check_masking_options(opts, opts.tka_label_img, opts.tka_label_space)

    print tka_label_type
    #Check inputs for results masking
    opts.results_label_img = split_label_img(opts.results_label_img)
    results_label_type = check_masking_options(opts, opts.results_label_img, opts.results_label_space)
    print results_label_type, opts.results_label_space
    
    #Set default label for atlas ROI
    masks={ "tka":[tka_label_type, opts.tka_label_img], "pvc":[pvc_label_type, opts.pvc_label_img], "results": [results_label_type, opts.results_label_img] }
    #Determine the level at which the labeled image is defined (scan- or atlas-level) 
    if os.path.exists(opts.sourceDir + os.sep + opts.tka_label_img[0]): opts.pvc_label_level = 'atlas' 
    else: opts.pvc_label_level = 'scan'
    if os.path.exists(opts.sourceDir + os.sep + opts.pvc_label_img[0]): opts.tka_label_level = 'atlas'
    else: opts.tka_label_level = 'scan'
    if os.path.exists(opts.sourceDir + os.sep + opts.results_label_img[0]): opts.results_label_level = 'atlas'
    else: opts.results_label_level = 'scan'
    
    # Set the analysis space based on the label space
    opts.analysis_space = opts.results_label_space

    roi_label = set_default_atlas_label(opts,roi_label, masks)  
    #If no label given by user, set default label for PVC mask
    if(opts.pvc_labels ==None): opts.pvc_labels = roi_label["pvc"]
      #If no label given by user, set default label for TKA mask
    if(opts.tka_labels ==None): opts.tka_labels = roi_label["tka"]
    #Set default label for results mask
    if(opts.results_labels ==None): opts.results_labels = roi_label["results"]
    ###Check PVC options and set defaults if necessary
    if opts.scanner_fwhm == None and opts.pet_scanner == None:
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
            print "\t2) set the FWHM of the scanner manually using the \"--scanner_fwhm <float>\" option."
            exit(1)

    opts.targetDir = os.path.normpath(opts.targetDir)
    opts.sourceDir = os.path.normpath(opts.sourceDir)
    opts.preproc_dir='preproc'
    
    if opts.pscan:
        printScan(opts,args)
    elif opts.pstages:
        printStages(opts,args)
    else:
        if opts.run_scan_level:
            run_scan_level(opts,args)
            dash.generate_dashboard(opts,args)
        if opts.run_group_level:
            run_group_level(opts,args)
            dash.link_stats(opts,args)

