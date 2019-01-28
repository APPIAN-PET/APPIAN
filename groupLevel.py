import os
import sys

import Results_Report.results as results
import Quality_Control.qc as qc
import Test.test_group_qc as tqc
import Quality_Control.dashboard as dash

def run_group_level(opts,args):
    #List of group level commands that can be run
    module_list=[qc, tqc, results]
    group_level_commands=[qc.group_level_qc, tqc.test_group_qc_groupLevel, results.group_level_descriptive_statistics ]
    #List of boolean flags that determine whether or not to run the comman
    if len(args) > 1 :
        group_level_run_flag=[opts.group_qc, opts.test_group_qc, opts.group_stats]
        for module, command, run_flag in zip(module_list, group_level_commands, group_level_run_flag):
            print(command, run_flag)
            if run_flag: 
                command(opts,args)
                if opts.dashboard:
                    try :
                        dash.link_stats(opts,args,module.final_dir)
                    except AttributeError :
                        pass
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




