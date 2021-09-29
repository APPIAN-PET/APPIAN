#vim: set tabstop=4 expandtab shgftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
#vim: filetype plugin indent on
from glob import glob
import re
import os
import sys
import argparse
import time
import pandas as pd
from src.workflows import Workflows

"""
.. module:: scanLevel
    :platform: Unix
    :synopsis: Module to launch scan level analysis.
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""
def run_scan_level(opts,args): 
    ###Define args with exiting subject and condition combinations
    if not os.path.exists(opts.targetDir) :
        os.makedirs(opts.targetDir)

    sub_valid_args, task_valid_args=gen_args(opts, args)
    
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
    '''
    Generate arguments for preinfosource
    '''

    session_ids = opts.sessionList 
    task_ids = opts.taskList 
    run_ids = opts.runList
    acq = opts.acq 
    rec = opts.rec
    
    task_args=[]
    sub_ses_args=[]
    sub_ses_dict={}

    report_columns = {'Sub':[]}

    print(session_ids, len(session_ids))
    if len(session_ids) == 0 : 
        session_ids=['']
    else :
        report_columns['Ses']=[]
    
    if len(task_ids) == 0 : 
        task_ids=['']
    else :
        report_columns['Task']=[]

    if len(run_ids) == 0 : 
        run_ids=['']
    else :
        report_columns['Run']=[]

    rec_arg=acq_arg=""
    if  not acq == '': 
        acq_arg='acq-'+acq
        report_columns['Acq']=[]

    if  not rec == '': 
        rec_arg='rec-'+rec
        report_columns['Rec']=[]

    report = pd.DataFrame(report_columns)
    for sub in subjects:
        if opts.verbose >= 2: print("Sub:", sub)
        for ses in session_ids:
            if opts.verbose >= 2: print("Ses:",ses)
            for task in task_ids:
                if opts.verbose >= 2: print("Task:",task)
                for run in run_ids:
                    sub_arg='sub-'+sub


                    if ses == '' :
                        pet_string=opts.sourceDir+os.sep+ sub_arg + os.sep + f'pet/*{rec_arg}*_pet.nii*'
                        pet_header_string=opts.sourceDir+os.sep+ sub_arg + os.sep + f'pet/*{rec_arg}*_pet.json'
                        mri_string=opts.sourceDir + os.sep + sub_arg + os.sep + 'anat/*_T1w.nii*'
                    else :
                        ses_arg='ses-'+ses
                        pet_string=opts.sourceDir+os.sep+ sub_arg + os.sep+ '*'+ ses_arg + os.sep+ f'pet/*{rec_arg}*_pet.nii*'
                        pet_header_string=opts.sourceDir+os.sep+ sub_arg + os.sep+ '*'+ ses_arg + os.sep+ f'pet/*{rec_arg}*_pet.json'
                        mri_string=opts.sourceDir + os.sep + sub_arg + os.sep + '*/anat/*_T1w.nii*'
                    mri_arg_list = ['sub-'+sub]
                    arg_list = ['sub-'+sub ]

                    if not ses == '' :
                        arg_list += ['ses-'+ses]
                        if opts.t1_ses == '' :
                            mri_arg_list += ['ses-'+ses]
                        else :
                            mri_arg_list += ['ses-'+opts.t1_ses]

                    if not task == '': arg_list += ['task-'+task]
                    if not acq == '': arg_list += ['acq-'+acq]
                    if not rec == '': arg_list += ['rec-'+rec]
                    if not run == '': arg_list += ['run-'+run]
                     
                    pet_fn = unique_file(pet_string, arg_list, opts.verbose )
                    pet_header_fn = unique_file(pet_header_string, arg_list, opts.verbose )
                    mri_fn = unique_file(mri_string, mri_arg_list, opts.verbose )
                    
                    report_row = {"Sub":sub}
                    d={'sid':sub} 
                    if "Ses" in report_columns.keys() :
                        report_row['Ses']=ses
                        d['ses']=ses
                        d['t1_ses']=opts.t1_ses

                    if opts.t1_ses != '' : d['t1_ses']=opts.t1_ses

                    if "Task" in report_columns.keys():
                        report_row['Task']=task
                        d['task']=task

                    if "Acq" in report_columns.keys() :
                        report_row['Acq']=acq
                        d['acq']=acq

                    if "Rec" in report_columns.keys() :
                        report_row['Rec']=rec
                        d['rec']=rec

                    if "Run" in report_columns.keys() :
                        report_row['Run']=run
                        d['run']=run

                    if not os.path.exists(pet_fn):
                        report_row['PET Volume']=pet_string
                        print('Warning: could not find PET file', pet_string)
                    else :
                        report_row['PET Volume']='OK'

                    if not os.path.exists(pet_header_fn):
                        report_row['PET Header']=pet_header_string
                        print('Warning: could not find PET header file', pet_header_fn)
                    else : 
                        report_row['PET Header']='OK'

                    if not os.path.exists(mri_fn):
                        report_row['MRI Volume']=mri_string
                        print('Warning: could not find MRI', mri_fn)
                    else : 
                        report_row['MRI Volume']='OK'

                    if os.path.exists(pet_fn) and os.path.exists(pet_header_fn) and os.path.exists(mri_fn):


                        d={'task':task, 'ses':ses, 't1_ses':opts.t1_ses, 'sid':sub, 'run':run} 
                        sub_ses_dict[sub]=ses
                        task_args.append(d)
                    
                    report=report.append(report_row,ignore_index=True)
    if opts.verbose >= 1 : 
        print(report)
    report.to_csv(opts.targetDir+os.sep+'input_file_report.csv',index=False)

    for key, val in sub_ses_dict.items() :
        sub_ses_args.append({"sid":key,"ses":ses,'t1_ses':ses})

    if opts.verbose >= 2:
        print("Scans on which APPIAN will be run")
        print( task_args)
    
    opts.sub_valid_args = sub_ses_args
    opts.task_valid_args = task_args
    return sub_ses_args, task_args


def unique_file(file_string, attributes, verbose=1):
    files = glob(file_string) 
    out_files=[]
    out_fn=""
    
    for f in files :
        missing_attributes=[]
        for a in attributes :
            if not a in f :
                if verbose >= 2 : 
                    print(a, "not in ", f)
                missing_attributes.append(a)
                break
        if verbose >= 2 : 
            if len(missing_attributes) == 0 :
                print("Valid file", f)
            else :
                print("File missing attributes " +";".join(missing_attributes) +" skipping:",f)

        if  len(missing_attributes) == 0 :
            out_files.append(f)

    if attributes == [] or len(out_files) == 0 : return ''

    # If there are 2 out_files, check if one is a compressed version of the other
    # If so keep the compressed version
    if len(out_files) == 2  :
        print(out_files)
        if out_files[0] == out_files[1] + '.gz' :
            out_files=[out_files[1]+'.gz']
        elif out_files[1] == out_files[0] + '.gz' : 
            out_files=[out_files[0]+'.gz']
        print(out_files)

    if len(out_files) >= 1 :
        out_fn = out_files[0]

    if len(out_files) > 1 :
        print("Warning: File is not uniquely specified. Multiple files found for the attributes ", attributes)
        print("Using file:", out_fn)
    
    if 'json' in file_string :
        print(out_fn)

    return( out_fn )
