import os
import sys

import Results_Report.results as results
import Quality_Control.qc as qc
import Test.test_group_qc as tqc
import Quality_Control.dashboard as dash

def run_group_level(opts,args):
    print('HELLO!')
    #List of group level commands that can be run
    default=(opts,args)
    
    args_list=[
            (qc, qc.group_level_qc, default, opts.group_qc ),
            (tqc, tqc.test_group_qc_groupLevel,default, opts.test_group_qc ),
            (results,results.group_level_descriptive_statistics, default,opts.group_stats )
            ]
  
    final_dirs=[]
     
    for module, command, fargs, run_flag in args_list:
        try :
            final_dirs.append(module.final_dirs)
        except AttributeError :
            pass

    args_list.append( (qc,dash.groupLevel_dashboard, (opts, final_dirs), True) )
    
    #List of boolean flags that determine whether or not to run the comman
    if len(args) > 1 :
        for module, command, fargs, run_flag in args_list:
            print(command, run_flag)
            if run_flag: 
                command(*fargs)

                #if opts.dashboard:
                #    try :
                #        dash.link_stats_qc(opts,args,module.final_dir)
                #    except AttributeError :
                #        pass

    else :
        print "Warning: only one subject, cannot run group level analysis."


# 1) Concatenate the results .csv from subjects
# 2) Calculate average and standard deviation for each ROI within
#       subject
#       subject x session
#       subject x task
#       task 
#       session
#




