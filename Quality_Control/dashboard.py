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
    f = h5py.File(mincfile)
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


def generate_xml_nodes(sourceDir,targetDir,pvc_method,tka_method):

    listOfNodes = [
            {"name" : "pet2mri", 
             "mnc_inputs" : {"node" : "pet2mri", "file" : 'in_target_file'},
             "mnc_outputs" : {"node" : "pet2mri", "file" : 'out_file_img'}
            }];
    if pvc_method != None :
        listOfNodes.append({"name" : "pvc",
                 "mnc_inputs" : {"node" : pvc_method, "file" : 'in_file'},
                 "mnc_outputs" : {"node" : pvc_method, "file" : 'out_file'}
                });
    if tka_method != None :
        listOfNodes.append({"name" : "tka",
                 "mnc_inputs" : {"node" : "convertParametric", "file" : 'out_file'},
                 "mnc_outputs" : {"node" : "pet2mri", "file" : 'in_target_file'}
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
                for key, value in nodeReport.inputs.items():
                    if key == "cid":
                        cid = str(value)
                    if key == "sid":
                        sid = str(value)
                xmlscan = SubElement(xmlQC, 'scan')
                xmlscan.set('sid', sid)
                xmlscan.set('cid', cid)

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
        rawfile = mincfile+'.raw'
        headerfile = mincfile+'.header'
        if not os.path.exists(rawfile) or not os.path.exists(headerfile):
            adjust_hdr(mincfile)
            mnc2vol(mincfile)


def link_stats(opts, arg):
    if not os.path.exists(targetDir+"/preproc/dashboard/") :
        os.makedirs(targetDir+"/preproc/dashboard/");
    # distutils.dir_util.copy_tree('/opt/appian/APPIAN/Quality_Control/dashboard_web', targetDir+'/preproc/dashboard', update=1, verbose=0)
    if os.path.exists(os.path.join(targetDir,'preproc/dashboard/public/stats')):
        os.remove(os.path.join(targetDir,'preproc/dashboard/public/stats'))
    os.symlink('../../stats', os.path.join(targetDir,'preproc/dashboard/public/stats'))




class deployDashOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class deployDashInput(BaseInterfaceInputSpec):
    targetDir = traits.File(mandatory=True, desc="Target directory")
    sourceDir = traits.File(mandatory=True, desc="Source directory")
    pvc_method = traits.Str(desc="PVC method")
    tka_method = traits.Str(desc="TKA method")
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
        # petmri = self.inputs.petmri
        # pvc = self.inputs.pvc
        # tka = self.inputs.tka
        targetDir = self.inputs.targetDir;
        sourceDir = self.inputs.sourceDir;
        pvc_method = self.inputs.pvc_method;
        tka_method = self.inputs.tka_method;

        if not os.path.exists(targetDir+"/preproc/dashboard/") :
            os.makedirs(targetDir+"/preproc/dashboard/");

        distutils.dir_util.copy_tree(os.path.split(os.path.abspath(__file__))[0]+'/dashboard_web', targetDir+'/preproc/dashboard', update=1, verbose=0)

        os.chdir(targetDir+'/preproc/dashboard/public/')
        if os.path.exists(os.path.join(targetDir,'preproc/dashboard/public/preproc')):
            os.remove(os.path.join(targetDir,'preproc/dashboard/public/preproc'))
        os.symlink('../../../preproc', os.path.join(targetDir,'preproc/dashboard/public/preproc'))
        for sub in glob.glob(os.path.join(sourceDir,'sub*')):
            if os.path.isdir(sub):
                dest = os.path.join(targetDir,'preproc/dashboard/public/',os.path.basename(sub))
                if os.path.exists(dest):
                    os.remove(dest)
                os.symlink(sub, dest)        

        generate_xml_nodes(sourceDir,targetDir,pvc_method,tka_method);
        
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined( self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs
