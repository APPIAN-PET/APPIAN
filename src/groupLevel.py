import os
import sys

import src.results as results
import src.qc as qc
import src.dashboard.dashboard as dash


def run_group_level(opts,args):
    #List of group level commands that can be run
    default=(opts,args)
   
    #List of tuples containing info about group level workflows to run
    # 1) module that we are loading
    # 2) function to call
    # 3) arguments to pass to the function. default = (opts, args)
    # 4) run flag
    args_list=[
            #(qc, qc.group_level_qc, default, opts.group_qc, 1 ),
            (results,results.group_level_descriptive_statistics, default ,opts.group_stats, 1 ),
            #(qc,dash.groupLevel_dashboard, default, opts.dashboard, 0)
            ]
    
    for module, command, fargs, run_flag, min_args in args_list:
        print(command, run_flag, len(args))
        if run_flag and len(args) > min_args :
            command(*fargs)
            #continue
            #try :
            #    print("Trying")
            #    command(*fargs)
            #except KeyboardInterrupt:
            #    raise
            #except:
            #    pass
        elif  len(args) < min_args :
            print( "Warning: only one subject, cannot run group level analysis.")

