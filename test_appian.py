import unittest
import os
import sys
from scanLevel import run_scan_level
sys.path.insert(0, os.getcwd())
base_args =  ['--source',source_dir, '--target', target_dir,'--fwhm','6','6','6', '--start-time', '2.5', '--tka-label', '3' ,'--tka-labels-ones-only' ,'--tka-label-erosion', '1']

global appian_dir
global source_dir
global target_dir

appian_dir = os.path.split( os.path.abspath(__file__) )[0]
source_dir="/opt/test_data"
target_dir="/opt/"

def base_test(command_args):
    opts = modify_opts(parser.parse_args(base_args+command_args))
    return run_scan_level(opts,opts.args) 

def test_pvc_GTM():
    assert base_test(['--pvc-method', 'GTM']) == 0

def test_pvc_VC():
    assert base_test(['--pvc-method', 'VC']) == 0

def test_pvc_idSURF():
    assert base_test(['--pvc-method', 'VC']) == 0
    ['--pvc-method', 'idSURF'],

def test_quant_lp():
    assert base_test(['--quant-method', 'lp']) == 0

def test_quant_lp_roi():
    assert base_test(['--quant-method', 'lp-roi']) == 0

def test_quant_pp():
    assert base_test(['--quant-method', 'pp']) == 0

def test_quant_pp_roi():
    assert base_test(['--quant-method', 'pp-roi']) == 0

def test_quant_suv():
    assert base_test(['--quant-method', 'suv']) == 0

def test_quant_suvr():
    assert base_test(['--quant-method', 'suvr']) == 0

def test_quant_srtm():
    assert base_test(['--quant-method', 'srtm']) == 0

def test_quant_srtm_bf():
    assert base_test(['--quant-method', 'srtm-bf']) == 0

def test_quant_idSURF_srtm():
    assert base_test(['--pvc-method','idSURF' ,'--quant-method', 'srtm']) == 0

def test_quant_idSURF_suvr():
    assert base_test(['--pvc-method','idSURF' ,'--quant-method', 'suvr']) == 0

def test_quant_srtm():
    assert base_test(['--pvc-method','VC' ,'--quant-method', 'srtm']) == 0

def test_quant_suvr():
    assert base_test(['--pvc-method','VC' ,'--quant-method', 'suvr']) == 0

def test_quant_arterial_lp():
    assert base_test(['--arterial', '--quant-method', 'lp']) == 0

def test_quant_arterial_pp():
    assert base_test(['--arterial', '--quant-method', 'pp']) == 0

def test_quant_lp_roi():
    assert base_test(['--arterial', '--quant-method', 'lp-roi']) == 0

def test_quant_pp_roi():
    assert base_test(['--arterial', '--quant-method', 'pp-roi']) == 0

def test_quant_srtm():
    assert base_test(['--arterial', '--quant-method', 'srtm']) == 0

def test_quant_srtm_roi():
    assert base_test(['--arterial', '--quant-method', 'srtm-roi']) == 0

def test_space_stereo():
    assert base_test(['--analysis-space' ,'stereo','--pvc-method','VC' ,'--quant-method', 'suvr']) == 0

def test_space_t1():
    assert base_test(['--analysis-space' ,'t1','--pvc-method','VC' ,'--quant-method', 'suvr']) == 0

def test_space_dka():
    assert base_test(['--tka-label-img', appian_dir+'/Atlas/MNI152/dka.mnc' , '--results-label-img', appian_dir+'/Atlas/MNI152/dka.mnc']) == 0

def test_space_aal():
    assert base_test(['--results-label-img',  appian_dir+'/Atlas/COLIN27/ROI_MNI_AAL_V5_UBYTE_round.mnc', '--results-label-template', appian_dir+'/Atlas/COLIN27/colin27_t1_tal_lin_ubyte.mnc']) == 0


                

