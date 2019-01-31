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
    
    ###Define args with exiting subject and condition combinations
    sub_valid_args, task_valid_args=init.gen_args(opts, args)
    
    opts.sub_valid_args = sub_valid_args
    opts.task_valid_args = task_valid_args
 
    scan_level_workflow = Workflows(opts)

    scan_level_workflow.initialize(opts) 

    #vizualization graph of the workflow
    #workflow.write_graph(opts.targetDir+os.sep+"workflow_graph.dot", graph2use = 'exec')

    printOptions(opts,args, opts.sessionList, opts.taskList,opts.runList, opts.acq, opts.rec)
    #run the work flow
    if opts.num_threads > 1 :
        plugin_args = {'n_procs' : opts.num_threads,
                   #'memory_gb' : num_gb, 'status_callback' : log_nodes_cb
                      }
        scan_level_workflow.workflow.run(plugin='MultiProc', plugin_args=plugin_args)
    else : 
        scan_level_workflow.workflow.run()

    return 0


