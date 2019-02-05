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

global base_dir
global appian_dir

appian_dir = os.path.split( os.path.abspath(__file__) )
#######
# MRI # 
#######

class TestMRI(unittest.TestCase): 
    '''Test modules related to MRI preprocessing: normalization, brain masking, segmentation'''
    #TODO MRI module currently doesn't have many options to test but this may need to change
    # as more options are added for more fine-tuned control
    def setUp(self) :
        parser=get_parser()
        self.opts = parser.parse_args(['--source',base_dir+'/test_data', '--target', base_dir, '--mri-preprocess-exit'])
        self.opts = modify_opts(self.opts)
        
        self.args=self.opts.args 

    def test_mri(self):
        self.assertEquals(run_scan_level(self.opts,self.args), 0)

##################
# Coregistration #
##################
class TestCoreg(unittest.TestCase): 
    '''Test modules related to PET - MRI coregistration '''
    def setUp(self) :
        parser=get_parser()
        self.opts = parser.parse_args(['--source',base_dir+'/test_data', '--target', base_dir, '--coregistration-exit'])
        self.opts = modify_opts(self.opts)
        self.args=self.opts.args 

    def test_coreg(self):
        self.assertEquals(run_scan_level(self.opts,self.args), 0)

#############################
# Partial-volume Correction #
#############################
       
class TestPVC(unittest.TestCase): 
    def __init__(self):
        self.base_args =  ['--source',base_dir+'/test_data', '--target', base_dir, '--coregistration-exit','--fwhm', '6', '6', '6']

    '''Test modules related to Partial Volume Correction '''
    def setUp(self):
        self.parser = get_parser()

    def test_GTM(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--pvc-method', 'GTM']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_VC(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--pvc-method', 'VC']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_idSURF(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--pvc-method', 'idSURF']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

##################
# Quantification #
##################
       
class TestQuantification(unittest.TestCase): 
    def __init__(self):
        self.base_args =  ['--source',base_dir+'/test_data', '--target', base_dir, '--start-time', '2.5', '--tka-label', '3' ,'--tka-labels-ones-only' ,'--tka-label-erosion', '1']

    '''Test modules related to Partial Volume Correction '''
    def setUp(self):
        self.parser = get_parser()

    def test_lp(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--quand-method', 'lp']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_lp_roi(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--quand-method', 'lp-roi']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_pp(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--quand-method', 'pp']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_pp_roi(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--quand-method', 'pp-roi']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_suv(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--quand-method', 'suv']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_suvr(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--quand-method', 'suvr']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_srtm(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--quand-method', 'srtm']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_srtm_bp(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--quand-method', 'srtm-bf']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_idSURF_srtm(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--fwhm','6','6','6','--pvc-method','idSURF' ,'--quand-method', 'srtm']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_idSURF_suvr(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--fwhm','6','6','6','--pvc-method','idSURF' ,'--quand-method', 'suvr']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_VC_srtm(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--fwhm','6','6','6','--pvc-method','VC' ,'--quand-method', 'srtm']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_VC_suvr(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--fwhm','6','6','6','--pvc-method','VC' ,'--quand-method', 'suvr']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_arterial_lp(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--arterial', '--quand-method', 'lp']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_arterial_pp(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--arterial', '--quand-method', 'pp']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_arterial_lp-roi(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--arterial', '--quand-method', 'lp-roi']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_arterial_pp-roi(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--arterial', '--quand-method', 'pp-roi']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_arterial_srtm(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--arterial', '--quand-method', 'srtm']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_arterial_srtm_roi(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--arterial', '--quand-method', 'srtm-roi']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

##########
# Spaces #
##########

class TestSpace(unittest.TestCase): 
    def __init__(self):
        self.base_args =  ['--source',base_dir+'/test_data', '--target', base_dir, '--start-time', '2.5', '--tka-label', '3' ,'--tka-labels-ones-only' ,'--tka-label-erosion', '1', '--tka-method', 'suvr' ]

    '''Test modules related to Partial Volume Correction '''
    def setUp(self):
        self.parser = get_parser()

    def test_stereo(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--analysis-space' ,'stereo']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_t1(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--analysis-space' ,'t1']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_dka(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--tka-label-img', appian_path+'/Atlas/MNI152/dka.mnc' , '--results-label-img', appian_path+'/Atlas/MNI152/dka.mnc']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

    def test_aal(self):
        self.opts = modify_opts(self.parser.parse_args(self.base_args + ['--results-label-img',  appian_path+'/Atlas/COLIN27/ROI_MNI_AAL_V5_UBYTE_round.mnc', '--results-label-template', appian_path+'/Atlas/COLIN27/colin27_t1_tal_lin_ubyte.mnc']))
        self.assertEquals(run_scan_level(self.opts, self.opts.args), 0)

 

def test_appian(source_dir) :
    base_dir=source_dir
    suites_list=[]
    for mod in [TestMRI, TestCoreg, TestPVC, TestQuantification, TestSpaces]:
        suites_list.append( unittest.TestLoader().loadTestsFromTestCase(mod) )
    suites = unittest.TestSuite(suites_list)
    unittest.TextTestRunner(verbosity=2).run(suites)

