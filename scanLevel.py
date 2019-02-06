#vim: set tabstop=4 expandtab shgftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
#vim: filetype plugin indent on

import os
import sys
import argparse
import time

import Initialization.initialization as init
import Quality_Control.dashboard as dash
from workflows import Workflows

"""
.. module:: scanLevel
    :platform: Unix
    :synopsis: Module to launch scan level analysis.
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""
def run_scan_level(opts,args): 
    ###Define args with exiting subject and condition combinations
    sub_valid_args, task_valid_args=init.gen_args(opts, args)
    
    scan_level_workflow = Workflows(opts)

    scan_level_workflow.initialize(opts) 

    #Run the work flow
    if opts.num_threads > 1 :
        scan_level_workflow.workflow.run(plugin='MultiProc', plugin_args={'n_procs': opts.num_threads})
    else : 
        print(scan_level_workflow.workflow._get_all_nodes())
        scan_level_workflow.workflow.run()
        print("Done.")
    return 0


