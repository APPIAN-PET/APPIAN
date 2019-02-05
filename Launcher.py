#!/usr/bin/env python
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a hlsearch
import os
import sys
import time
from Extra.nii2mnc_batch import nii2mnc_batch
from Extra.minc_json_header_batch import create_minc_headers
from scanLevel import run_scan_level
from groupLevel import run_group_level
from test_appian import test_appian
from arg_parser import get_parser, modify_opts

version = "1.0"


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


############################################
# Define dictionaries for default settings #
############################################

if __name__ == "__main__":
    parser = get_parser()
    
    opts = parser.parse_args() 
    if opts.test :
        test_appian(opts.sourceDir)
        exit(0)
    
    opts = modify_opts( opts ) 
    args=opts.args 


    printOptions(opts,opts.args,opts.sessionList,opts.taskList, opts.runList, opts.acq, opts.rec)
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
