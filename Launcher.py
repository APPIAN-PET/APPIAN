#!/usr/bin/env python
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a hlsearch
import os
import sys
from Extra.nii2mnc_batch import nii2mnc_batch
from Extra.minc_json_header_batch import create_minc_headers
from scanLevel import run_scan_level
from groupLevel import run_group_level
from test_appian_bkp import test_appian
from arg_parser import get_parser, modify_opts

version = "1.0"

############################################
# Define dictionaries for default settings #
############################################

if __name__ == "__main__":
    parser = get_parser()
    
    opts = parser.parse_args() 
    #if opts.test :
    #    test_appian(opts.sourceDir, opts.targetDir, opts.num_threads)
    #    exit(0)
    opts = modify_opts( opts ) 
    args=opts.args 

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



