#vim: set tabstop=4 expandtab shgftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
#vim: filetype plugin indent on

import os
import sys
import argparse
import time

#import Initialization.initialization as init
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


def gen_args(opts, subjects):
    session_ids = opts.sessionList 
    task_ids = opts.taskList 
    run_ids = opts.runList
    acq = opts.acq 
    rec = opts.rec
    
    task_args=[]
    sub_ses_args=[]
    sub_ses_dict={}
    test_arg_list=[]
    if len(session_ids) == 0 : session_ids=['']
    if len(task_ids) == 0 : task_ids=['']
    if len(run_ids) == 0 : run_ids=['']

    for sub in subjects:
        if opts.verbose: print("Sub:", sub)
        for ses in session_ids:
            if opts.verbose: print("Ses:",ses)
            for task in task_ids:
                if opts.verbose: print("Task:",task)
                for run in run_ids:
                    sub_arg='sub-'+sub
                    ses_arg='ses-'+ses
                    task_arg=rec_arg=acq_arg=""

                    pet_fn=mri_fn=""
                    if  acq == '': acq_arg='acq-'+acq
                    if  rec == '': rec_arg='rec-'+rec
                    pet_string=opts.sourceDir+os.sep+ sub_arg + os.sep+ '*'+ ses_arg + os.sep+ 'pet/*_pet.mnc'
                    pet_string_gz=opts.sourceDir+os.sep+ sub_arg + os.sep+ '*'+ ses_arg + os.sep+ 'pet/*_pet.mnc.gz'
                    pet_list=glob(pet_string) + glob(pet_string_gz)
                    arg_list = ['sub-'+sub, 'ses-'+ses]
                    mri_arg_list = ['sub-'+sub, 'ses-'+ses]
                    if not task == '': arg_list += ['task-'+task]
                    if not acq == '': arg_list += ['acq-'+acq]
                    if not rec == '': arg_list += ['rec-'+rec]
                    if not run == '': arg_list += ['run-'+run]
                    if opts.verbose : print( arg_list );
                    if pet_list != []:
                        pet_fn = unique_file(pet_list, arg_list, opts.verbose )
                    mri_list=glob(opts.sourceDir+os.sep+ sub_arg + os.sep + '*/anat/*_T1w.mnc' ) + glob(opts.sourceDir+os.sep+ sub_arg + os.sep + '*/anat/*_T1w.mnc.gz' )
                    if mri_list != []:
                        mri_fn = unique_file(mri_list, mri_arg_list )
                    #if pet_fn == [] or mri_fn == [] : continue

                    if os.path.exists(pet_fn) and os.path.exists(mri_fn):
                        #compression=''
                        #if '.gz' in pet_fn : compression='.gz'

                        d={'task':task, 'ses':ses, 'sid':sub, 'run':run} #,'compression':compression}
                        sub_ses_dict[sub]=ses
                        if opts.verbose :
                            print(pet_fn, os.path.exists(pet_fn))
                            print(mri_fn, os.path.exists(mri_fn))
                            print('Adding to dict of valid args',d)
                        task_args.append(d)
                    else:
                        if not os.path.exists(pet_fn) and opts.verbose :
                            print "Could not find PET for ", sub, ses, task, pet_fn
                        if not os.path.exists(mri_fn) and opts.verbose :
                            print "Could not find T1 for ", sub, ses, task, mri_fn

    for key, val in sub_ses_dict.items() :
        sub_ses_args.append({"sid":key,"ses":ses})

    if opts.verbose :
        print("Args:\n", task_args)
    
    opts.sub_valid_args = sub_ses_args
    opts.task_valid_args = task_args

    return sub_ses_args, task_args
