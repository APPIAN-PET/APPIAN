import unittest
import MRI.normalize
import scanLevel.run_scan_level
from Launcher import get_parser


class TestAPPIAN(unittest.TestCase):
    '''Basic class for testing APPIAN pipeline with various options'''



class TestMRI(TestAPPIAN): 
    '''Test modules related to MRI preprocessing: normalization, brain masking, segmentation'''
    #TODO MRI module currently doesn't have many options to test but this may need to change
    # as more options are added for more fine-tuned control
    def setUp(self) :
        self.test_opts.mri_preprocess_exit=True
        parser=get_parser(['--source', '/opt/test_data', '--target', '/opt/'])
        self.opts = parser.parse_args()
        self.args=opts.args 

    def tearDown(self) :
        pass
    
    def test_mri(self):
        self.assertEquals(run_scan_level(self.test_opts,self.args), 0)


def test(opts,args) :
    unittest.main()



