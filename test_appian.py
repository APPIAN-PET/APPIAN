import unittest
import os
import sys
import Registration.registration as reg
import Initialization.initialization as init
import Partial_Volume_Correction.pvc as pvc 
import Results_Report.results as results
import Tracer_Kinetic.tka as tka
import Quality_Control.qc as qc
import Quality_Control.dashboard as dash
import Test.test_group_qc as tqc
from arg_parser import get_parser, modify_opts
from Masking import masking as masking
from Masking import surf_masking
from MRI import normalize
from scanLevel import run_scan_level

def set_base_args():
    base_args =  ['--source',source_dir, '--target', target_dir,'--fwhm','6','6','6', '--start-time', '2.5', '--tka-label', '3' ,'--tka-labels-ones-only' ,'--tka-label-erosion', '1']
    return base_args

global appian_dir
appian_dir = os.path.split( os.path.abspath(__file__) )[0]

command_list= [['--pvc-method', 'GTM'],
    ['--pvc-method', 'VC'],
    ['--pvc-method', 'idSURF'],
    ['--quant-method', 'lp'],
    ['--quant-method', 'lp-roi'],
    ['--quant-method', 'pp'],
    ['--quant-method', 'pp-roi'],
    ['--quant-method', 'suv'],
    ['--quant-method', 'suvr'],
    ['--quant-method', 'srtm'],
    ['--quant-method', 'srtm-bf'],
    ['--pvc-method','idSURF' ,'--quant-method', 'srtm'],
    ['--pvc-method','idSURF' ,'--quant-method', 'suvr'],
    ['--pvc-method','VC' ,'--quant-method', 'srtm'],
    ['--pvc-method','VC' ,'--quant-method', 'suvr'],
    ['--arterial', '--quant-method', 'lp'],
    ['--arterial', '--quant-method', 'pp'],
    ['--arterial', '--quant-method', 'lp-roi'],
    ['--arterial', '--quant-method', 'pp-roi'],
    ['--arterial', '--quant-method', 'srtm'],
    ['--arterial', '--quant-method', 'srtm-roi'],
    ['--analysis-space' ,'stereo','--pvc-method','VC' ,'--quant-method', 'suvr'],
    ['--analysis-space' ,'t1','--pvc-method','VC' ,'--quant-method', 'suvr'],
    ['--tka-label-img', appian_dir+'/Atlas/MNI152/dka.mnc' , '--results-label-img', appian_dir+'/Atlas/MNI152/dka.mnc'],
    ['--results-label-img',  appian_dir+'/Atlas/COLIN27/ROI_MNI_AAL_V5_UBYTE_round.mnc', '--results-label-template', appian_dir+'/Atlas/COLIN27/colin27_t1_tal_lin_ubyte.mnc'],
]

def test_appian(source_dir_0, target_dir_0) :
    global source_dir
    global target_dir

    source_dir=source_dir_0 
    
    for i, command in enumerate(command_list) :
        parser=get_parser()
        target_dir=target_dir_0 + os.sep + 'test_'+str(i)
        base_args=set_base_args()
        opts = parser.parse_args(base_args+command)
        opts = modify_opts(opts)
        args=opts.args 
        results=[]
        print(opts )
        print( run_scan_level(opts,args) )
        exit(0)
        if run_scan_level(opts,args) == 0 :
            results.append( [ i, 'Passed', command  ] )
        else :
            results.append( [ i, 'Failed', command  ] )

        for result in results :
            print("Test :", result[0], "-->", result[1])
            if result[1] != 'Passed' : 
                print('Failed Command:', result[2] )
               
                

