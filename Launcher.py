#!/usr/bin/env python
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a hlsearch
import os
import sys
from Extra.nii2mnc_batch import nii2mnc_batch
from Extra.minc_json_header_batch import create_minc_headers
from scanLevel import run_scan_level
from groupLevel import run_group_level
from arg_parser import get_parser, modify_opts

version = "1.0"

############################################
# Define dictionaries for default settings #
############################################

if __name__ == "__main__":
    parser = get_parser()
    
    opts = parser.parse_args() 
    opts = modify_opts( opts ) 
    args=opts.args 

    ############################################
    # Create BIDS-style header for MINC inputs #
    ############################################
    create_minc_headers( opts.sourceDir )
    
    #######################################
    ### Convert NII to MINC if necessary. # 
    #######################################
    nii2mnc_batch(opts)	
   
    #################
    # Launch APPIAN #
    #################
    if opts.run_scan_level:
        run_scan_level(opts,args)
    if opts.run_group_level:
        run_group_level(opts,args)



#def validate_inputs(opts) :
#    '''
#    Check that user has specified required inputs
#    '''
#    if opts.labels_template_img != None and not os.path.exists(opts.labels_template_img
#        pass

