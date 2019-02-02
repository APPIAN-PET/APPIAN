import os
import glob
import json
import subprocess
import sys
import importlib

from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)

from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.utils.filemanip import loadcrash
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.dom import minidom
import h5py
import minc2volume_viewer as minc2volume
import distutils
from distutils import dir_util

import nipype.interfaces.minc as minc
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.interfaces.utility as niu
from nipype.interfaces.utility import Rename

from Extra.conversion import  nii2mncCommand

from Masking import masking as masking
import Registration.registration as reg
import Initialization.initialization as init
import Partial_Volume_Correction.pvc as pvc 
import Results_Report.results as results
import Tracer_Kinetic.tka as tka
import Quality_Control.qc as qc
import Test.test_group_qc as tqc
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

def adjust_hdr(mincfile):
    f = h5py.File(mincfile,'r')
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
        cmd("minc_modify_header -sinsert {}:direction_cosines='{}' {}".format(dim, dir_cosine, mincfile))
    if n_dims == 4:
        cmd("minc_modify_header -dinsert time:start=0 {}".format(mincfile))
        cmd("minc_modify_header -dinsert time:step=1 {}".format(mincfile))

def mnc2vol(mincfile):
    if not os.path.exists(mincfile) :
        print('Warning: could not find file', mincfile)
        exit(1)

    f = h5py.File(mincfile, 'r')
    datatype = str(f['minc-2.0/image/0']['image'].dtype)
    rawfile = mincfile+'.raw'
    headerfile = mincfile+'.header'
    minc2volume.make_raw(mincfile, datatype, rawfile)
    minc2volume.make_header(mincfile, datatype, headerfile)


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


def generate_xml_nodes(sourceDir,targetDir,pvc_method,tka_method,analysis_space):
    
    #
    # Set input / output nodes for Coregistration stage
    #
    listOfNodes = [
            {"name" : "pet2mri", 
             "mnc_inputs" : {"node" : "pet2mri", "file" : 'in_target_file'},
             "mnc_outputs" : {"node" : "pet2mri", "file" : 'out_file_img'}
            }];

    #
    # Set input / output nodes for PVC stage
    #
    if pvc_method != None :
        print('pvc_method', pvc_method)
        pvc_outputs_dict = set_stage_node_file('pvc', pvc_method )

        listOfNodes.append({"name" : "tka",
                    "mnc_inputs" : {"node" : pvc_method, "file" : 'in_file'},
                    "mnc_outputs" : pvc_outputs_dict
                });
    #
    # Set input / output nodes for TKA / Quantification stage
    #
    if tka_method != None :
        tka_file_type = get_stage_file_type('quant', tka_method)
        node_tka = tka_method if tka_file_type == "MINC"  else "convertParametric"
       
        if analysis_space == "pet":
            quant_output_dict={"node":"t1_pet_space", "file":"out_file"}
        elif analysis_space == "t1":
            quant_output_dict={"node" : "pet2mri", "file" : 'in_target_file'}
        elif analysis_space == "stereo":
            quant_output_dict={"node" : "mri_normalize", "file" : 'out_file_vol'}

        quant_input_dict = set_stage_node_file('quant', tka_method )

        listOfNodes.append({"name" : "tka",
                    "mnc_inputs" : quant_input_dict,
                    "mnc_outputs" : quant_output_dict
                });



    filename=targetDir+"/preproc/graph1.json";
    fp = file(filename, 'r')
    data=json.load(fp)
    fp.close()

    xmlQC = Element('qc')
    listVolumes = list();

    for subjIdx in range(0,len(data["groups"])):
        for nodeID in range(data["groups"][subjIdx]["procs"][0],data["groups"][subjIdx]["procs"][-1]):
            nodeName = "_".join(data["nodes"][nodeID]["name"].split("_")[1:])
            if nodeName == "datasourcePET":
                nodeReport = loadcrash(targetDir+"/preproc/"+data["nodes"][nodeID]["result"])
                xmlscan = SubElement(xmlQC, 'scan')
                for key, value in nodeReport.inputs.items():
                    if key in ('cid', 'sid', 'ses', 'run') :
                        xmlscan.set(key, str(value))               

        for x in listOfNodes :
            xmlnode = SubElement(xmlscan, 'node')
            xmlnode.set('name', x['name'])
            for nodeID in range(data["groups"][subjIdx]["procs"][0],data["groups"][subjIdx]["procs"][-1]):
                nodeName = "_".join(data["nodes"][nodeID]["name"].split("_")[1:])
                if nodeName == x["mnc_inputs"]["node"]:
                    nodeReport = loadcrash(targetDir+"/preproc/"+data["nodes"][nodeID]["result"])
                    xmlmnc = SubElement(xmlnode, 'inMnc')
                    for key, value in nodeReport.inputs.items():
                        if key in x['mnc_inputs']["file"]:
                            value = value[0] if type(value) == list else value
                            xmlkey = SubElement(xmlmnc, str(key))
                            xmlkey.text = str(value).replace(sourceDir+"/",'').replace(targetDir+"/",'')
                            listVolumes.append(str(value))
                if nodeName == x["mnc_outputs"]["node"]:
                    nodeReport = loadcrash(targetDir+"/preproc/"+data["nodes"][nodeID]["result"])
                    xmlmnc = SubElement(xmlnode, 'outMnc')
                    for key, value in nodeReport.inputs.items():
                        if key in x['mnc_outputs']["file"]:
                            value = value[0] if type(value) == list else value
                            xmlkey = SubElement(xmlmnc, str(key))
                            xmlkey.text = str(value).replace(sourceDir+"/",'').replace(targetDir+"/",'')
                            listVolumes.append(str(value))                        


    with open(targetDir+"/preproc/dashboard/public/nodes.xml","w") as f:
        f.write(prettify(xmlQC))

    for mincfile in listVolumes:
        print("MINC; ", mincfile)
        rawfile = mincfile+'.raw'
        headerfile = mincfile+'.header'
        if not os.path.exists(rawfile) or not os.path.exists(headerfile):
            print "mnc2vol"
            #adjust_hdr(mincfile) #CANNOT USE THIS BECAUSE IT MODIFIES EXISTING FILES. ALSO MESSES UP COSINES
            mnc2vol(mincfile)


def link_stats_qc(opts, arg, flag):
    os.chdir(opts.targetDir+'/preproc/dashboard/public/')
    lnk=os.path.join(opts.targetDir,'preproc/dashboard/public/',flag)
    if not os.path.exists(opts.targetDir+"/preproc/dashboard/") :
        os.makedirs(opts.targetDir+"/preproc/dashboard/");
    if os.path.islink(lnk):
        os.remove(lnk)
    os.symlink(os.path.join('../../../',flag), lnk)




class deployDashOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class deployDashInput(BaseInterfaceInputSpec):
    targetDir = traits.File(mandatory=True, desc="Target directory")
    sourceDir = traits.File(mandatory=True, desc="Source directory")
    pvc_method = traits.Str(desc="PVC method", default_value=None, usedefault=True)
    tka_method = traits.Str(desc="TKA method", default_value=None, usedefault=True)
    analysis_space = traits.Str(desc="Analysis Space")
    petmri = traits.File(exists=True, mandatory=True, desc="Output PETMRI image")
    pvc = traits.File(desc="Output PVC image")
    tka = traits.File(desc="Output TKA image")
    out_file = traits.File(desc="Output file")
    clobber = traits.Bool(desc="Overwrite output file", default=False)

class deployDashCommand(BaseInterface):
    input_spec = deployDashInput
    output_spec = deployDashOutput
  
    def _gen_output(self):
        fname = "nodes.xml"
        dname = self.inputs.targetDir+"/preproc/dashboard/public" 
        return dname+os.sep+fname

    def _run_interface(self, runtime):
        targetDir = self.inputs.targetDir;
        sourceDir = self.inputs.sourceDir;
        pvc_method = self.inputs.pvc_method;
        tka_method = self.inputs.tka_method;
        analysis_space = self.inputs.analysis_space

        if not os.path.exists(targetDir+"/preproc/dashboard/") :
            os.makedirs(targetDir+"/preproc/dashboard/");

        distutils.dir_util.copy_tree(os.path.split(os.path.abspath(__file__))[0]+'/dashboard_web', targetDir+'/preproc/dashboard', update=1, verbose=0)

        os.chdir(targetDir+'/preproc/dashboard/public/')
        if os.path.exists(os.path.join(targetDir,'preproc/dashboard/public/preproc')):
            os.remove(os.path.join(targetDir,'preproc/dashboard/public/preproc'))
            os.symlink('../../../preproc', os.path.join(targetDir,'preproc/dashboard/public/preproc'))
        #for sub in glob.glob(os.path.join(sourceDir,'sub*')):
        #    if os.path.isdir(sub):
        #        dest = os.path.join(targetDir,'preproc/dashboard/public/',os.path.basename(sub))
        #        if os.path.islink(dest):
        #            os.remove(dest)
        #        os.symlink(sub, dest)        

        generate_xml_nodes(sourceDir,targetDir,pvc_method,tka_method,analysis_space);
        
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs
