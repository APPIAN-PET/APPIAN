#!/usr/bin/env python
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a hlsearch
import os
import sys
from src.scanLevel import run_scan_level
from src.groupLevel import run_group_level
from src.arg_parser import get_parser, modify_opts

version = "1.0"

############################################
# Define dictionaries for default settings #
############################################

if __name__ == "__main__":
    parser = get_parser()
    
    opts = parser.parse_args() 
    opts = modify_opts( opts ) 
    args=opts.args 
 
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

