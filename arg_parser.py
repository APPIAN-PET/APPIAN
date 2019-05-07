import argparse
import os
import numpy as np
from argparse import ArgumentParser
from glob import glob
from re import sub
import time
import sys
 
global spaces
global file_dir
global icbm_default_template

spaces=['pet', 't1', 'stereo']
internal_cls_methods=["antsAtropos"]

file_dir, fn =os.path.split( os.path.abspath(__file__) )

icbm_default_template = file_dir+os.sep+"/Atlas/MNI152/mni_icbm152_t1_tal_nlin_asym_09c.nii"

#Default FWHM for PET scanners
pet_scanners={"HRRT":[2.5,2.5,2.5],"HR+":[6.5,6.5,6.5]} #FIXME should be read from a separate .json file and include lists for non-isotropic fwhm

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
    print "* Sessions : ", session_ids, "\n"
    print "* Tasks : " , task_list , "\n"
    print "* Runs : " , run_list , "\n"
    print "* Acquisition : " , acq , "\n"
    print "* Reconstruction : " , rec , "\n"

def get_parser():
    parser = ArgumentParser(usage="useage: ")
    parser.add_argument("-s","--source","--sourcedir",dest="sourceDir",  help="Absolute path for input file directory", required=True)
    parser.add_argument("-t","--target","--targetdir",dest="targetDir",type=str, help="Absolute path for directory where output data will be saved in", required=True)
    parser.add_argument("--preprocdir",dest="preproc_dir",type=str, default='preproc', help="Relative path (relative to targetDir) to preprocessing directory for intermediate files")

    parser.add_argument("--radiotracer","--acq",dest="acq",type=str, default='', help="Radiotracer")
    parser.add_argument("-r","--rec",dest="rec",type=str, default='', help="Reconstruction algorithm")
    parser.add_argument("--sessions",dest="sessionList",default=[],help="List of conditions or scans",nargs='+')
    parser.add_argument("--subjects",dest="args",default=[], help="List of subjects",nargs='+')
    parser.add_argument("--tasks",dest="taskList",default=[],help="List of conditions or scans",nargs='+')
    parser.add_argument("--runs",dest="runList",default=[],help="List of runs",nargs='+')
    parser.add_argument("--output-format",dest="output_format",type=str, default='nifti', help="Output file format for APPIAN (default=nifti, options=nifti,minc)")

    #############################
    # MRI Preprocessing Options #
    #############################
    #MRI N4 Correction
    parser.add_argument("--n4-bspline-fitting-distance", dest="n4_bspline_fitting_distance",type=float,help="Distances for T1 MRI intensity non-uniformity correction with N4 (1.5T ~ 200, 3T ~ ). (Default=0, skip this step)", default=200)
    parser.add_argument("--n4-bspline-order", dest="n4_bspline_order",type=int,help="Order of BSpline interpolation for N4 correction", default=None)
    parser.add_argument("--n4-n-iterations", dest="n4_n_iterations",type=int,help="List with number of iterations to perform. Default=50 50 30 20 ", default=[50, 50, 30, 20], nargs='+')
    parser.add_argument("--n4-shrink-factor", dest="n4_shrink_factor",type=int,help="Order of BSpline interpolation for N4 correction", default=2)
    parser.add_argument("--n4-convergence-threshold", dest="n4_convergence_threshold",type=float,help="Convergence threshold for N4 correction", default=1e-6)

    parser.add_argument("--normalization-type", dest="normalization_type",type=str,help="Type of registration to use for T1 MRI normalization, rigid, linear, non-linear: rigid, affine, nl. (Default=nl)", default='nl')
    parser.add_argument("--user-ants-normalization", dest="user_ants_normalization",type=str,help="User specified command for normalization. See \"Registration/user_ants_example.txt\" for an example", default=None)
    parser.add_argument("--user-t1mni","--user-mri-to-stereo", dest="user_mri_stx", default='lin', type=str, help="User provided transform from to and from MRI & MNI space. Options: lin, nl. If 'lin' transformation files must end with '_affine.h5'. If 'nl', files must be a compressed nifti file that ends with '_warp.nii.gz'. Transformation files must indicate the target coordinate space of the transform: '_target-<T1/MNI>_<affine/warp>.<h5/nii.gz>' " ) 
    parser.add_argument("--user-brainmask", dest="user_brainmask", default=False, action='store_true', help="Use user provided brain mask" ) 
    
    parser.add_argument("--segmentation-method",dest="mri_segmentation_method", help="Method to segment mask from MRI", type=str, default='ANTS') 
    parser.add_argument("--ants-atropos-priors",dest="ants_atropos_priors", help="Anatomics label images to use as priors for Atropos segmentation. By default, if not set by user and template is the default ICBM152c, then APPIAN uses the GM/WM/CSF probabilistic segmentations of ICBM152c template. Users providing their own templates can specify their own priors", type=str, default=[] ) 
    parser.add_argument("--ants-atropos-prior-weighting",dest="ants_atropos_prior_weighting", help="Weight to give to priors in Atropos segmentation", type=float, default=0.5 ) 
          
    ###################
    # Surface Options #
    ###################
    parser.add_argument("--surf",dest="use_surfaces",action='store_true', default=False,help="Flag that signals APPIAN to find surfaces")
    parser.add_argument("--surf-label",dest="surface_label", default='*', help="Label string to identify surface ROI .txt file")
    parser.add_argument("--surf-space",dest="surface_space",type=str,default="icbm152", help="Set space of surfaces from : \"pet\", \"t1\", \"icbm152\" (default=icbm152)")
    parser.add_argument("--surf-ext",dest="surf_ext",type=str,help="Extension to use for surfaces",default='obj')
          

    ######################
    # Additional Options #
    ######################
    parser.add_argument("--test",dest="test",action='store_true', default=False, help="Run tests on APPIAN")
    parser.add_argument("--no-group-level",dest="run_group_level",action='store_false', default=True, help="Do not run group level analysis")
    parser.add_argument("--no-scan-level",dest="run_scan_level",action='store_false', default=True, help="Do not run scan level analysis")

    parser.add_argument("--img-ext",dest="img_ext",type=str,help="Extension to use for images.",default='nii')
    parser.add_argument("--analysis-space",dest="analysis_space",help="Coordinate space in which PET processing will be performed (Default=pet)",default='pet', choices=spaces)
    parser.add_argument("--threads",dest="num_threads",type=int,help="Number of threads to use. (defult=1)",default=1)
    
    parser.add_argument("--stereotaxic-template", dest="template",type=str,help="Template image in stereotaxic space",default=icbm_default_template)
    parser.add_argument("--datasource-exit",dest="datasource_exit",help="Stop scan level processing after initialization of datasources", action='store_true', default=False)
    parser.add_argument("--initialize-exit",dest="initialize_exit",help="Stop scan level processing after PET initialization", action='store_true', default=False)
    parser.add_argument("--coregistration-exit",dest="coregistration_exit",help="Stop scan level processing after coregistration", action='store_true', default=False)
    parser.add_argument("--masking-exit",dest="masking_exit",help="Stop scan level processing after masking", action='store_true', default=False)
    parser.add_argument("--mri-preprocess-exit",dest="mri_preprocess_exit",help="Stop scan level processing after MRI preprocessing", action='store_true', default=False)
    parser.add_argument("--pvc-exit",dest="pvc_exit",help="Stop scan level processing after PVC", action='store_true', default=False)
          


    ###################
    # Masking options #
    ###################
    label_space_help="Coordinate space of labeled image to use for TKA. Options: [pet/t1/stereo] "
    label_img_help="Options: 1. ICBM MNI 152 atlas: <path/to/labeled/atlas>, 2. Stereotaxic atlas and template: path/to/labeled/atlas /path/to/atlas/template 3. Internal classification method (" + ', '.join(internal_cls_methods) + ') 4. String that identifies labels in anat/ directory to be used as mask' 
    #PVC
    #group= OptionGroup(parser,"Masking options","PVC")
    parser.add_argument("--pvc-label-space",dest="pvc_label_space",help=label_space_help,default='stereo', choices=spaces)
    parser.add_argument("--pvc-label-img",dest="pvc_label_img",help=label_img_help, type=str, default='antsAtropos')
    parser.add_argument("--pvc-label-template",dest="pvc_label_template",help="Absolute path to template for stereotaxic atlas", type=str, default=None)
    parser.add_argument("--pvc-label",dest="pvc_labels",help="Label values to use for pvc",default=[], nargs='+')
    parser.add_argument("--pvc-label-erosion",dest="pvc_erode_times",help="Number of times to erode label", type=int, default=0 )
    parser.add_argument("--pvc-labels-brain-only","--pvc-label-brain-only", dest="pvc_labels_brain_only",help="Mask pvc labels with brain mask",action='store_true',default=False)
    parser.add_argument("--pvc-labels-ones-only",dest="pvc_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    parser.add_argument("--pvc-labels-per-pet",dest="pvc_labels_per_pet",help="Mask pvc labels with brain mask",action='store_true',default=False)
    

    # Quantification
    #group= OptionGroup(parser,"Masking options","Quantification")
    parser.add_argument("--tka-label-space","--quant-label-space", dest="tka_label_space",help=label_space_help,default='stereo', choices=spaces)
    parser.add_argument("--tka-label-img","--quant-label-img",dest="tka_label_img", help=label_img_help, type=str,default='antsAtropos')
    parser.add_argument("--tka-label-template","--quant-label-template",dest="tka_label_template",help="Absolute path to template for stereotaxic atlas", type=str, default=None)
    parser.add_argument("--tka-label","--quant-label",dest="tka_labels",help="Label values to use for TKA", default=[3], nargs='+' )
    parser.add_argument("--tka-label-erosion","--quant-label-erosion",dest="tka_erode_times",help="Number of times to erode label", type=int, default=0 )
    parser.add_argument("--tka-labels-brain-only","--quant-label-brain-only",dest="tka_labels_brain_only",help="Mask tka labels with brain mask",action='store_true',default=False)
    parser.add_argument("--tka-labels-ones-only","--quant-labels-ones-only",dest="tka_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    

    #Results
    #group= OptionGroup(parser,"Masking options","Results")
    parser.add_argument("--no-results-report",dest="no_results_report",help="Don't calculate descriptive stats for results ROI.",action='store_true',default=False)
    parser.add_argument("--results-label-name",dest="results_label_name",help="Extra label string that is used to create the directory with results: /<results_method>_<results_label>. Allows you to run same results node multiple times without overwriting previous results.",type=str, default=None)
    parser.add_argument("--results-label-space", dest="results_label_space",help=label_space_help,default='stereo', choices=spaces)
    parser.add_argument("--results-label-img", dest="results_label_img",help=label_img_help, type=str,default='antsAtropos')
    parser.add_argument("--results-label-template",dest="results_label_template",help="Absolute path to template for stereotaxic atlas", type=str, default=None)
    parser.add_argument("--results-label",dest="results_labels",help="Label values to use for results",default=[], nargs='+' )
    parser.add_argument("--results-label-erosion",dest="results_erode_times",help="Number of times to erode label", type=int,default=0 )
    parser.add_argument("--results-labels-brain-only","--results-label-brain-only",dest="results_labels_brain_only",help="Mask results labels with brain mask",action='store_true',default=False)
    parser.add_argument("--results-labels-ones-only",dest="results_labels_ones_only",help="Flag to signal threshold so that label image is only 1s and 0s",action='store_true',default=False)
    

    ##########################
    # Coregistration Options #
    ##########################
    #group= OptionGroup(parser,"Coregistation options")
    parser.add_argument("--coreg-method", dest="coreg_method",type=str,help="Coregistration method: minctracc, ants (default=minctracc)", default="minctracc")
    parser.add_argument("--coregistration-brain-mask",dest="coregistration_brain_mask",help="Target T1 mask for coregistration", action='store_false', default=True)
    parser.add_argument("--pet-brain-mask",dest="pet_brain_mask",help="Create PET mask for coregistration", action='store_true', default=False)
    parser.add_argument("--second-pass-no-mask",dest="no_mask",help="Do a second pass of coregistration without masks.", action='store_false', default=True)
    parser.add_argument("--slice-factor",dest="slice_factor",help="Value (between 0. to 1.) that is multiplied by the maximum of the slices of the PET image. Used to threshold slices. Lower value means larger mask.", type=float, default=0.25)
    parser.add_argument("--total-factor",dest="total_factor",help="Value (between 0. to 1.) that is multiplied by the thresholded means of each slice.",type=float, default=0.333)
    

    ###############
    # PVC options #
    ###############
    #group= OptionGroup(parser,"PVC Options")
    parser.add_argument("--pvc-method",dest="pvc_method",help="Method for PVC.",type=str, default=None)
    parser.add_argument("--pvc-label-name",dest="pvc_label_name",help="Extra label string that is used to create the directory with PVC results: /<pvc_method>_<pvc_label>. Allows you to run same PVC node multiple times without overwriting previous results.",type=str, default=None)
    parser.add_argument("--pet-scanner",dest="pet_scanner",help="FWHM of PET scanner.",type=str, default=None)
    parser.add_argument("--fwhm","--pvc-fwhm",dest="scanner_fwhm",help="FWHM of PET scanner (z,y,x).",type=float, nargs=3, default=None)
    parser.add_argument("--pvc-max-iterations",dest="max_iterations",help="Maximum iterations for PVC method.",type=int, default=None)
    parser.add_argument("--k",dest="k",help="Number of deconvolution iterations.",type=int, default=None)
    parser.add_argument("--pvc-tolerance",dest="tolerance",help="Tolerance for PVC algorithm.",type=float, default=0.001)
    parser.add_argument("--pvc-denoise-fwhm",dest="denoise_fwhm",help="FWHM of smoothing filter (for IdSURF).",type=float, default=1)
    parser.add_argument("--pvc-nvoxel-to-average",dest="nvoxel_to_average",help="Number of voxels to average over (for IdSURF).",type=int, default=64)
    

    #TKA Options
    #group= OptionGroup(parser,"Quantification options")
    parser.add_argument("--tka-method","--quant-method",dest="tka_method",help="Method for performing tracer kinetic analysis (TKA): lp, pp, srtm.",type=str, default=None)
    parser.add_argument("--tka-label-name","-quant-label-name",dest="quant_label_name",help="Extra label string that is used to create the directory with quantification results: /<quant_method>_<quant_label>. Allows you to run same quantification node multiple times without overwriting previous results.",type=str, default=None)
    parser.add_argument("--quant-to-stereo",dest="quant_to_stereo",help="Transform quantitative images to stereotaxic space. If \"analysis space\" is \"stereo\" then this option is redundant (default=False) ", action='store_true', default=False)
    parser.add_argument("--k2",dest="tka_k2",help="With reference region input it may be necessary to specify also the population average for regerence region k2",type=float, default=None)
    parser.add_argument("--k2s",dest="tka_k2s",help="With reference region input it may be necessary to specify also the population average for regerence region k2",type=float, default=None)
    parser.add_argument("--thr",dest="tka_thr",help="Pixels with AUC less than (threshold/100 x max AUC) are set to zero. Default is 0%",type=float, default=None)
    parser.add_argument("--max",dest="tka_max",help="Upper limit for Vt or DVR values; by default max is set pixel-wise to 10 times the AUC ratio.",type=float, default=None)
    
    parser.add_argument("--R1",dest="tka_R1",help="Program computes also an R1 image.",type=str, default=None)
    parser.add_argument("--rp",dest="tka_rp",help="Program writes regression parameters in the specified image file.",type=str, default=None)
    parser.add_argument("--dual",dest="tka_dual",help="Instead of BP, program saves the DVR (=BP+1) values.",type=str, default=None)
    parser.add_argument("--DVR",dest="tka_DVR",help="Program writes number of i in set p in NNLS dual solution vector in the specified image file",action='store_const', const=True, default=False)
    parser.add_argument("--no-srtm2",dest="tka_srtm2",help="STRM2 method is applied by default, this option will turn it off. In brief, traditional SRTM method is used first to calculate median k2 from all pixels where BPnd>0; then SRTM is run another time with fixed k2.",action='store_const', const=False, default=True)
    parser.add_argument("--bf",dest="tka_bf",help="Basis function curves are written in specified file.",type=str, default=None)
    parser.add_argument("--err",dest="tka_err",help="Errors are written in specified file.",type=str, default=None)
    parser.add_argument("--noneg",dest="tka_noneg",help="Pixels with negative BP values are set to zero.", action='store_const', const=True, default=None)
    parser.add_argument("--wss",dest="tka_wss",help="Weighted sum-of-squares are written in specified image file.",type=str, default=None)
    parser.add_argument("--min",dest="tka_min",help="Lower limit for Vt or DVR values, 0 by default",type=float, default=None)
    parser.add_argument("--t3max",dest="tka_t3max",help="Upper limit for theta3, 0.01 by default",type=float, default=None)
    parser.add_argument("--t3min",dest="tka_t3min",help="Lower limit for theta3, 0.001 by default",type=float, default=None)
    parser.add_argument("--nBF",dest="tka_nBF",help="Number of basis functions.",type=int, default=None)
    parser.add_argument("--filter",dest="tka_filter",help="Remove parametric pixel values that over 4x higher than their closest neighbours.",action='store_const',const=True, default=None)
    parser.add_argument("--reg-end",dest="tka_end",help="By default line is fit to the end of data. Use this option to enter the fit end time (in min).",type=float, default=None)
    parser.add_argument("--y-int",dest="tka_v",help="Y-axis intercepts time -1 are written as an image to specified file.",type=str, default=None)
    parser.add_argument("--num",dest="tka_n",help="Numbers of selected plot data points are written as an image.",type=str, default=None)
    parser.add_argument("--Ca",dest="tka_Ca",help="Concentration of native substrate in arterial plasma (mM).",type=float, default=None)
    parser.add_argument("--LC",dest="tka_LC",help="Lumped constant in MR calculation; default is 1.0.",type=float, default=None)
    parser.add_argument("--density",dest="tka_density",help="Tissue density in MR calculation; default is 1.0 g/ml.",type=float, default=None)
    parser.add_argument("--arterial",dest="arterial",help="Use arterial input input.", action='store_true', default=False)
    parser.add_argument("--start-time",dest="tka_start_time",help="Start time of either regression in MTGA or averaging time for SUV.",type=float, default=None)
    parser.add_argument("--end-time",dest="tka_end_time",help="End time for quantification.",type=float, default=None)
    parser.add_argument("--tka-type",dest="tka_type",help="Type of tka analysis: voxel or roi.",type=str, default="voxel")
    

    #Quality Control 
    parser.add_argument("--no-dashboard",dest="dashboard",help="Generate a dashboard.", action='store_const', const=False, default=True)
    parser.add_argument("--no-group-qc",dest="group_qc",help="Don't perform quantitative group-wise quality control.", action='store_const', const=False, default=True)  #FIXME Add to options
    parser.add_argument("--test-group-qc",dest="test_group_qc",help="Perform simulations to test quantitative group-wise quality control.", action='store_const', const=True, default=False)
    parser.add_argument_group(parser)

    #Results reporting
    parser.add_argument("--no-group-stats",dest="group_stats",help="Don't calculate quantitative group-wise descriptive statistics.", action='store_const', const=False, default=True)  #FIXME Add to options
    parser.add_argument_group(parser)

    parser.add_argument("-v","--verbose",dest="verbose",help="Write messages indicating progress. 0=quiet, 1=normal, 2=debug",type=int,default=1)
    
    
    return parser

def modify_opts(opts) :
    opts.targetDir = os.path.normpath(opts.targetDir)
    opts.sourceDir = os.path.normpath(opts.sourceDir)

    ############################
    #Automatically set sessions#
    ############################ 
    if opts.args == [] :
        opts.args = [ sub('sub-', '',os.path.basename(f)) for f in glob(opts.sourceDir+os.sep+"sub-*") ]
        print("Warning : No subject arguments passed. Will run all subjects found in source directory "+ opts.sourceDir)
        print("Subjects:", ' '.join( opts.args))
   
        if len(opts.args) == 0:
            print "\n\n*******ERROR********: \n     The subject IDs are not listed in the command-line \n********************\n\n"
            exit(1)


    if opts.sessionList == [] :
        opts.sessionList =np.unique( [ sub('_','',sub('ses-', '',os.path.basename(f))) for f in glob(opts.sourceDir+os.sep+"**/*ses-*") ])
        print("Warning : No session variables. Will run all sessions found in source directory "+ opts.sourceDir)
        print("Sessions:", ' '.join( opts.sessionList))
    

    #########################
    #Automatically set tasks#
    #########################
    if opts.taskList == [] :
        for f in glob(opts.sourceDir+os.sep+"**/**/pet/*task-*") :
            g=os.path.splitext(os.path.basename(f))[0]
            task_list = [ i  for i in   g.split('_') if 'task-' in i ]
            if task_list == [] : continue

            if opts.taskList == None : opts.taskList = []
            task = sub('task-', '', task_list[0])
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
    if opts.runList == [] :
        for f in glob(opts.sourceDir+os.sep+"**/**/pet/*run-*") :
            g=os.path.splitext(os.path.basename(f))[0]
            task_list = [ i  for i in   g.split('_') if 'run-' in i ]
            if task_list == [] : continue

            if opts.runList == None : opts.runList = []
            run = sub('run-', '', task_list[0])
            opts.runList.append(run)

        if opts.runList != None : 
            opts.runList = np.unique(opts.runList)
        else : 
            opts.runList =[]
        
        print("Warning : No run variables. Will process all runs found in source directory "+ opts.sourceDir)
        print("Runs:", ' '.join( opts.runList))
    
    ##########################################################
    # Check inputs to make sure there are no inconsistencies #
    ##########################################################
    if not opts.sourceDir or not opts.targetDir: 
        print "\n\n*******ERROR******** \n     You must specify --sourcedir, --targetdir \n********************\n"
        parser.print_help()
        sys.exit(1)

    #Check inputs for PVC masking 
    opts.pvc_label_type, opts.pvc_label_space = check_masking_options(opts, opts.pvc_label_img, opts.pvc_label_template, opts.pvc_label_space)
    #Check inputs for TKA masking
    opts.tka_label_type, opts.tka_label_space = check_masking_options(opts, opts.tka_label_img, opts.tka_label_template, opts.tka_label_space)
    #Check inputs for results masking
    opts.results_label_type, opts.results_label_space = check_masking_options(opts, opts.results_label_img, opts.results_label_template, opts.results_label_space)
    #Set default label for atlas ROI
    masks={ "tka":[opts.tka_label_type, opts.tka_label_img], "pvc":[opts.pvc_label_type, opts.pvc_label_img], "results": [opts.results_label_type, opts.results_label_img] }

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


    printOptions(opts,opts.args,opts.sessionList,opts.taskList, opts.runList, opts.acq, opts.rec)
    #FIXME Depreceating tka_method in favor of quant_method
    #Creating the opts.quant_method to start transition away from using tka_method
    opts.quant_method = opts.tka_method
    return opts


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
