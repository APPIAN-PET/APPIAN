import os
import glob
import json
import subprocess
import sys
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.utils.filemanip import loadcrash
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.dom import minidom
import h5py
import minc2volume_viewer as minc2volume
import distutils
from distutils import dir_util
from bs4 import BeautifulSoup as bs


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

def mnc2vol(mincfile):
    # image_precision = cmd("mincinfo -vartype image {}".format(mincfile)).replace("_","")
    # image_signtype = cmd("mincinfo -attvalue image:signtype {}".format(mincfile)).replace("_","")
    # datatype = {
    #     "byte signed" : "int8",
    #     "byte unsigned" : "uint8",
    #     "short signed" : "int16",
    #     "short unsigned" : "uint16",
    #     "int signed" : "int32",
    #     "int unsigned" : "uint32",
    #     "int signed" : "int32",
    #     "int unsigned" : "uint32",
    #     "float signed" : "float32",
    #     "float" : "float32",
    #     "double" : "float64",
    # }[str(image_precision+" "+image_signtype)]


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



def generate_xml(opts, arg):

    listOfNodes = [
            {"name" : "pet_brainmask", 
             "mnc_inputs" : ['in_file'],
             "mnc_outputs" : ['out_file']
            },
            # {"name" : "petVolume", 
            #  "mnc_inputs" : ['input_files'],
            #  "mnc_outputs" : ['output_file']
            # },
            {"name" : "pet2mri", 
             "mnc_inputs" : ['in_target_mask','in_target_file','in_source_mask','in_source_file'],
             "mnc_outputs" : ['out_file_img']
            },
            {"name" : "pvc", 
             "mnc_inputs" : ['input_file'],
             "mnc_outputs" : ['out_file']
            }]

    filename=opts.targetDir+"/preproc/graph1.json";
    fp = file(filename, 'r')
    data=json.load(fp)
    fp.close()

    xmlQC = Element('qc')
    listVolumes = list();
    for subjIdx in range(0,len(data["groups"])):
        for nodeID in range(data["groups"][subjIdx]["procs"][0],data["groups"][subjIdx]["procs"][-1]):
            nodeName = "_".join(data["nodes"][nodeID]["name"].split("_")[1:])
            if nodeName == "datasource":
                nodeReport = loadcrash(opts.targetDir+"/preproc/"+data["nodes"][nodeID]["result"])
                for key, value in nodeReport.inputs.items():
                    if key == "acq":
                        acq = str(value)
                    if key == "cid":
                        cid = str(value)
                    if key == "sid":
                        sid = str(value)
                    if key == "task":
                        task = str(value)
                    if key == "rec":
                        rec = str(value)
                xmlscan = SubElement(xmlQC, 'scan')
                xmlscan.set('acq', acq)
                xmlscan.set('sid', sid)
                xmlscan.set('cid', cid)
                xmlscan.set('task', task)
                xmlscan.set('rec', rec)
            nodeReport = loadcrash(opts.targetDir+"/preproc/"+data["nodes"][nodeID]["result"])
            nodeIOs = nodeReport.inputs.keys()
            if nodeName in [x['name'] for x in listOfNodes] :
                try:
                    idx = [bool(set(x['mnc_inputs']).intersection(nodeIOs)) for x in listOfNodes].index(True)
                except ValueError:
                    continue;
                nodeReport = loadcrash(opts.targetDir+"/preproc/"+data["nodes"][nodeID]["result"])
                xmlnode = SubElement(xmlscan, 'node')
                xmlnode.set('name', nodeName)
                if listOfNodes[idx].has_key("mnc_inputs"):
                    xmlinmnc = SubElement(xmlnode, 'inMnc')
                    for key, value in nodeReport.inputs.items():
                        if key in listOfNodes[idx]['mnc_inputs']:
                            value = value[0] if type(value) == list else value
                            xmlkey = SubElement(xmlinmnc, str(key))
                            xmlkey.text = str(value).replace(opts.sourceDir+"/",'').replace(opts.targetDir+"/",'')
                            listVolumes.append(str(value))
                if listOfNodes[idx].has_key("mnc_outputs"):
                    xmloutmnc = SubElement(xmlnode, 'outMnc')
                    for key, value in nodeReport.outputs.items():
                        if key in listOfNodes[idx]['mnc_outputs']:
                            value = value[0] if type(value) == list else value
                            xmlkey = SubElement(xmloutmnc, str(key))
                            xmlkey.text = str(getattr(nodeReport.outputs,key)).replace(opts.targetDir+"/",'').replace(opts.sourceDir+"/",'')
                            listVolumes.append(str(getattr(nodeReport.outputs,key)))


     
        
    # print listVolumes
    with open(opts.targetDir+"/preproc/dashboard/public/nodes.xml","w") as f:
        f.write(prettify(xmlQC))

    for mincfile in listVolumes:
        rawfile = mincfile+'.raw'
        headerfile = mincfile+'.header'
        if not os.path.exists(rawfile) or not os.path.exists(headerfile):
            adjust_hdr(mincfile)
            mnc2vol(mincfile)

def generate_dashboard(opts, arg):
    if not os.path.exists(opts.targetDir+"/preproc/dashboard/") :
        os.makedirs(opts.targetDir+"/preproc/dashboard/");
    distutils.dir_util.copy_tree('./appian/APPIAN/Quality_Control/dashboard_web', opts.targetDir+'/preproc/dashboard', update=1, verbose=0)
    generate_xml(opts, arg);
    os.chdir(opts.targetDir+'/preproc/dashboard/public/')
    if os.path.exists(os.path.join(opts.targetDir,'preproc/dashboard/public/preproc')):
        os.remove(os.path.join(opts.targetDir,'preproc/dashboard/public/preproc'))
    os.symlink('../../../preproc', os.path.join(opts.targetDir,'preproc/dashboard/public/preproc'))
    for sub in glob.glob(os.path.join(opts.sourceDir,'sub*')):
        if os.path.isdir(sub):
            dest = os.path.join(opts.targetDir,'preproc/dashboard/public/',os.path.basename(sub))
            if os.path.exists(dest):
                os.remove(dest)
            os.symlink(sub, dest)
    # soup = bs(open(opts.targetDir+'/preproc/dashboard//pipelineIO.html'), "html.parser")
