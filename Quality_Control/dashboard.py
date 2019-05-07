import os
import glob
import json
import subprocess
import sys
import importlib
import h5py
import nipype.interfaces.minc as minc
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.utility as niu
import minc2volume_viewer as minc2volume
import distutils
import nibabel as nib
import Registration.registration as reg
import Initialization.initialization as init
import Partial_Volume_Correction.pvc as pvc 
import Results_Report.results as results
import Tracer_Kinetic.tka as tka
import Quality_Control.qc as qc
import Test.test_group_qc as tqc
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)

from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.utils.filemanip import loadcrash
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.dom import minidom
from Extra.utils import splitext
from distutils import dir_util
from nipype.interfaces.utility import Rename
from Extra.conversion import  nii2mncCommand
from Masking import masking as masking

from Masking import surf_masking
global path
path = os.path.dirname(os.path.abspath(__file__))
path_split = path.split(os.sep)
pvc_path = '/'.join(path_split[0:-1])+os.sep+"Partial_Volume_Correction"+os.sep+"methods"
tka_path = '/'.join(path_split[0:-1])+os.sep+"Tracer_Kinetic"+os.sep+"methods"
sys.path.insert(0, pvc_path)
sys.path.insert(0, tka_path)
importlib.import_module("pvc_method_GTM")
importlib.import_module("quant_method_lp")

def cmd(command):
    return subprocess.check_output(command.split(), universal_newlines=True).strip()

def adjust_hdr(niftifile):
    f = h5py.File(niftifile,'r')
    n_dims = len(f['minc-2.0/dimensions'])
    # list_dims = ['xspace', 'yspace', 'zspace', 'time']
    # list_dims.pop() if ndims == 3 else False
    list_dims = ['xspace', 'yspace', 'zspace']  
    for dim in list_dims:
        dir_cosine = {
            "xspace" : '1.,0.,0.',
            "yspace" : '0.,1.,0.',
            "zspace" : '0.,0.,1.',
        } [str(dim)]
        cmd("minc_modify_header -sinsert {}:direction_cosines='{}' {}".format(dim, dir_cosine, niftifile))
    if n_dims == 4:
        cmd("minc_modify_header -dinsert time:start=0 {}".format(niftifile))
        cmd("minc_modify_header -dinsert time:step=1 {}".format(niftifile))

def mnc2vol(niftifile):
    if not os.path.exists(niftifile) :
        print('Warning: could not find file', niftifile)
        exit(1)

    datatype = nib.load(niftifile).get_data().dtype
    basename = os.getcwd()+os.sep+ splitext(os.path.basename(niftifile))[0]
    rawfile = basename +'.raw'
    headerfile = basename +'.header'
    minc2volume.make_raw(niftifile, datatype, rawfile)
    minc2volume.make_header(niftifile, datatype, headerfile)


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding='UTF-8')

def get_stage_file_type(stage, method, stage_dir, prefix):
    '''
    Get the file format from the methods file for quant or pvc. These files contain 
    a variable that specifies the output file format for the quant/pvc node. 
    '''
    
    # Specify path to module
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+"../"+stage_dir+"/methods" )
    module_fn=prefix+"_method_"+method 
    
    # Load the module
    try :
        module = importlib.import_module(module_fn)
    except ImportError :
        print("Error: Could not find source file", pvc_module_fn, "corresponding to pvcification method:", opts.pvc_method )
        exit(1)
    
    #Read the file format from the module
    if stage == 'pvc' :
        return module.file_format
    elif stage =='tka' : 
        return module.out_file_format
    
    return None

def set_stage_node_file(stage, method) :
    if stage == 'pvc':
        conversion_node = 'convertPVC'
        stage_dir="Partial_Volume_Correction"
        prefix="pvc"
    elif stage == 'quant' :
        conversion_node = 'convertParametric'
        stage_dir="Tracer_Kinetic"
        prefix="tka"
    else :
        print("Error: stage must be with 'pvc' or 'tka' but received :", stage)
        exit(1)

    if method != None :
        file_type = get_stage_file_type(stage, method, stage_dir, prefix)
        node = method if file_type == "MINC"  else conversion_node

    return {"node" : node, "file" : 'out_file'} 


def generate_xml_nodes(sourceDir,targetDir,pvc_method,tka_method,analysis_space,images, info, out_file):
    #Create root for xml, called <qc> 
    xmlQC = Element('qc')
    
    # Initialize empty list to store volumes that may need to be converted
    listVolumes = list();

    # Write variables related to scan info: sid, ses, task, cid
    xmlscan = SubElement(xmlQC, 'scan')
    for key, value in info.items() :
        xmlscan.set(key, str(value))               
   
    # Iterate over the images dict and write the paths for
    # outMnc and inMnc
    for node_name, img in images.items() :
        xmlnode = SubElement(xmlscan, 'node')
        xmlnode.set('name', node_name)

        xmlkey = SubElement(xmlnode, 
            'volumet1' if node_name == 'pvc' else 'volume1')
        xmlkey.text = img["v1"].replace(targetDir+"/",'') 
        
        xmlkey = SubElement(xmlnode, 
            'volumet2' if node_name == 'pvc' else 'volume2')
        xmlkey.text = img["v2"].replace(targetDir+"/",'') 

        listVolumes.append(img["v1"])                        
        listVolumes.append(img["v2"])                        
    
    # Save the output xml file
    with open(out_file,"w") as f:
        f.write(prettify(xmlQC))

    # Perform conversion to raw
    for niftifile in listVolumes:
        rawfile = niftifile+'.raw'
        headerfile = niftifile+'.header'
        mnc2vol(niftifile)


def link_stats_qc(*args):
    opts=args[0]
    if not os.path.exists(opts.targetDir+'/preproc/dashboard/public/') :
        os.makedirs(opts.targetDir+'/preproc/dashboard/public/')
    os.chdir(opts.targetDir+'/preproc/dashboard/public/')
    
    final_dirs = [ os.path.basename(f) for f in glob.glob(opts.targetDir+'/*') ]
    for flag in final_dirs :
        lnk=os.path.join(opts.targetDir,'preproc/dashboard/public/',flag)
        if os.path.islink(lnk):
            os.remove(lnk)
        os.symlink(os.path.join('../../../',flag), lnk)


class deployDashOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class deployDashInput(BaseInterfaceInputSpec):
    targetDir = traits.File(mandatory=True, desc="Target directory")
    sourceDir = traits.File(mandatory=True, desc="Source directory")
    pvc_method = traits.Str(desc="PVC method")
    tka_method = traits.Str(desc="TKA method")
    analysis_space = traits.Str(desc="Analysis Space")
    pet = traits.File(exists=True, mandatory=True, desc="PET image")
    pet_space_mri = traits.File(exists=True, mandatory=True, desc="Output PETMRI image")
    mri_space_nat = traits.File(exists=True, mandatory=True, desc="Output T1 native space image")
    t1_analysis_space = traits.File(exists=True, mandatory=True, desc="Output T1 in analysis space image")
    pvc = traits.File(exists=True, desc="Output PVC image")
    tka = traits.File(exists=True, desc="Output TKA image")
    sid =traits.Str()
    cid=traits.Str()
    ses=traits.Str()
    task=traits.Str()
    run=traits.Str()

    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)

class deployDashCommand(BaseInterface):
    input_spec = deployDashInput
    output_spec = deployDashOutput
  
    def _gen_output(self):
        fname = "nodes.xml"
        dname = os.getcwd()
        return dname+os.sep+fname

    def _run_interface(self, runtime):
        
        #create dictionary with information about scan
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        info={ "sid":self.inputs.sid, "cid":self.inputs.cid,  "ses":self.inputs.ses, "task":self.inputs.task, "run":self.inputs.run }

        #Create dictionary with file paths and names for volumes that we want to display in dashboard
        images={"pet2mri":{"v1":self.inputs.mri_space_nat, "v2":self.inputs.pet_space_mri}}

        # If PVC method is defined, then add PVC images
        if isdefined(self.inputs.pvc_method) :
            images["pvc"]= {"v1":self.inputs.pet, "v2":self.inputs.pvc}

        # If TKA method is defined, then add quantification images
        if isdefined(self.inputs.tka_method) :
            images["tka"]= {"v1":self.inputs.t1_analysis_space, "v2":self.inputs.tka}
       
        #Create xml for current scan
        generate_xml_nodes(self.inputs.sourceDir,self.inputs.targetDir,self.inputs.pvc_method,self.inputs.tka_method,self.inputs.analysis_space,images,info, self.inputs.out_file);
        
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs


def groupLevel_dashboard(opts, args):
    workflow = pe.Workflow(name="concat_dashboard_xml")
    workflow.base_dir = opts.targetDir + '/preproc'
  
    #Check for valid data sources
    sources=glob.glob(opts.targetDir+os.sep+opts.preproc_dir+'*'+os.sep+'dash_scanLevel'+os.sep+'nodes.xml')
    if len(sources) == 0 : return 0

    if not os.path.exists(opts.targetDir+"/preproc/dashboard/") :
        os.makedirs(opts.targetDir+"/preproc/dashboard/");

    distutils.dir_util.copy_tree(os.path.split(os.path.abspath(__file__))[0]+'/dashboard_web', opts.targetDir+'/preproc/dashboard', update=1, verbose=0)

    os.chdir(opts.targetDir+'/preproc/dashboard/public/')
    if os.path.exists(os.path.join(opts.targetDir,'preproc/dashboard/public/preproc')):
        os.remove(os.path.join(opts.targetDir,'preproc/dashboard/public/preproc'))
    os.symlink('../../../preproc', os.path.join(opts.targetDir,'preproc/dashboard/public/preproc'))

    link_stats_qc(opts)

    datasource = pe.Node( interface=nio.DataGrabber( outfields=['xml'], raise_on_empty=True, sort_filelist=False), name="datasourceDashboard")
    datasource.inputs.base_directory = opts.targetDir + os.sep +opts.preproc_dir
    datasource.inputs.template = '*'
    datasource.inputs.field_template = {"xml" : '*'+os.sep+'dash_scanLevel'+os.sep+'nodes.xml'}

    concat_dashboard_xmlNode=pe.Node(interface=concat_xml(), name="concat_xml")
    concat_dashboard_xmlNode.inputs.out_file=opts.targetDir+"/preproc/dashboard/public/nodes.xml"
    workflow.connect(datasource, 'xml', concat_dashboard_xmlNode, 'in_list')
    workflow.run() 


class concat_xmlOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class concat_xmlInput(BaseInterfaceInputSpec):
    in_list = traits.List(mandatory=True, exists=True, desc="Input list")
    out_file = traits.File(mandatory=True, desc="Output file")

class concat_xml(BaseInterface):
    input_spec =  concat_xmlInput 
    output_spec = concat_xmlOutput 

    def _run_interface(self, runtime):
        out = open(self.inputs.out_file, 'w+')
        out.write('<qc>\n')
        
        n=len(self.inputs.in_list)

        for filename in self.inputs.in_list :
            with open(filename, 'r') as f :
                for l in f.readlines() : 
                    if (not '<qc>' in l) and (not '</qc>' in l) and (not 'xml version' in l) :
                        out.write(l)
                    else :
                        pass

        out.write('</qc>')
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.getcwd() + os.sep + self.inputs.out_file
        return outputs



