import os
import nipype.pipeline.engine as pe
from pyminc.volumes.factory import *
import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from Extra.base import MINCCommand, MINCCommandInputSpec
from Extra.conversion import (ecat2mincCommand, minc2ecatCommand, ecattomincCommand, minctoecatInterfaceCommand, minctoecatWorkflow)
from Extra.modifHeader import FixHeaderCommand
from Turku.dft import img2dftCommand
from Extra.extra import subject_parameterCommand
from Extra.turku import imgunitCommand
import ntpath
import numpy as np
import re
import importlib
import sys

class createImgFromROIOutput(TraitedSpec):  
    out_file = File(desc="Reconstruced 3D image based on .dft ROI values")

class createImgFromROIInput(TraitedSpec):
    out_file = File(desc="Reconstruced 3D image based on .dft ROI values")
    in_file = File(exists=True, mandatory=True, desc=" .dft ROI values")
    like_file = File(exists=True, mandatory=True, desc="File that gives spatial coordinates for output volume")


class createImgFromROI(BaseInterface) :
    input_spec = createImgFromROIInput
    output_spec = createImgFromROIOutput


    def _run_interface(self, runtime) :
        if not isdefined(self.inputs.out_file) : self.inputs.out_file = self._gen_output(self.inputs.in_file)
        ref = volumeFromFile(self.inputs.like_file)
        out = volumeLikeFile(self.inputs.like_file, self.inputs.out_file )
        roi=[]
        with open(self.inputs.in_file) as f :
            for l in f.readlines() :
                if 'Mask' in l : 
                    ll=re.split(' |\t', l)
                    print(ll[1],ll[3])
                    roi.append([int(ll[1]), float(ll[3])])

        for label, value in roi : 
            out.data[ref == label] = value
            print(label, np.mean(out.data[ref == label]))
        out.writeFile()
        out.closeVolume()

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + '.mnc'

'''
class suvOutput(TraitedSpec):
    out_file = File(argstr="%s", position=-1, desc="Output SUV image.")

class suvInput(MINCCommandInputSpec):
    
    in_file= File(exists=True, position=-6, argstr="%s", desc="PET file")
    start_time=traits.String(argstr="%s", position=-5, desc="Start time (minutes).")
    end_time=traits.String(argstr="%s", position=-4, desc="End time (minutes).")
    radiotracer_dose=traits.String(argstr="%s", position=-3, desc="Injected radiotracer dose (MBq).")
    body_weight=traits.String(argstr="%s", position=-2, desc="Patient weight (kg).")
    out_file = File(argstr="%s", position=-1, desc="Output SUV image")

class suvCommand(MINCCommand):
    input_spec =  suvInput
    output_spec = suvOutput

    _cmd = "imgsuv" #input_spec.pvc_method 
    _suffix = "_suv" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(suvCommand, self)._parse_inputs(skip=skip)
'''


standard_fields=["in_file", "header",  "reference", "mask", "like_file"] #NOTE: in_file and out_file must be defined in field
ecat_methods=["lp", "pp", "lp-roi", "pp-roi", "srtm", "suv"]
tka_param={}
tka_param["lp"]=standard_fields
tka_param["pp"]=standard_fields
tka_param["pp-roi"]=standard_fields
tka_param["lp-roi"]=standard_fields
tka_param["srtm"]=standard_fields
tka_param["suv"]=["in_file", "header"]
tka_param["suvr"]=["in_file", "header", "mask", "reference"]
reference_methods=["pp-roi","pp", "lp-roi", "lp", "srtm", "suvr"]

"""
.. module:: tka
    :platform: Unix
    :synopsis: Module to perform for PET quantification 
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""
def get_tka_workflow(name, opts):
    '''
    Nipype workflow that to perform PET quanfication. Requires conversion of PET file 
    and reference region mask to ECAT. Turku PET Centre tools are used to perform quantification.
    Finally, ECAT images are converted back to MINC.

    :param name: Name of workflow
    :param infosource: Infosource for basic variables like subject id (sid) and condition id (cid)
    :param datasink: Node in which output data is sent
    :param opts: User options

    .. aafig::
                            +---------+
                            |Reference|
                +---+       +----+----+
                |PET|            |
                +-+-+       +----+
                  |         |    |
                  |         V    V
            +---+ | +-------++  ++------+
            |ROI| | |Ref Mask|  |Ref TAC|
            +-+-+ | +-+------+  +-+-----+
              |   |   |           |    
              V   V   V           |
            +-+---+---++          |
            |MINC2ECAT +          |
            +-+---+---++          |
              |   |   |           | 
              | +-+-+ +-----+-----+
              | |   |       |
              | |   |       |
              V V   V       | 
              +-+-+ +-----+ |
              |ROI| |Voxel| |
              +-+-+ +---+-+ |
                ^       ^   | 
                |       |   |
                +-------+---+


    :returns: workflow
    '''
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=['sid']+tka_param[opts.tka_method]), name='inputnode')

    out_files = ["out_file"]
    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=out_files), name='outputnode')
    

    ### Quantification module
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+"/methods" )
    #quant_module_fn="Tracer_Kinetic.methods.quant_method_"+opts.tka_method +".py"
    quant_module_fn="quant_method_"+opts.tka_method #+".py"

    print("Loading modules", quant_module_fn) 
    quant_module = importlib.import_module(quant_module_fn)
    try :
        quant_module = importlib.import_module(quant_module_fn)
    except ImportError :
        print("Error: Could not find source file", quant_module_fn, "corresponding to quantification method:", opts.tka_method )
        exit(1)
    
    tkaNode = pe.Node(interface=quant_module.quantCommand(), name=opts.tka_method)
    tkaNode = quant_module.check_options(tkaNode, opts)
 
    #If the quantification node takes a header input, then pass it from inputnode
    try : 
        tkaNode.inputs.header
        workflow.connect(inputnode, 'header', tkaNode, 'header')
    except AttributeError :
        pass
   
    ### Setup input to quantification function
    if quant_module.in_file_format == "ECAT" :
        # Node to convert ECAT to MINC
        convertPET=pe.Node(minc2ecatCommand(), name="convertPET")
        
        #Connect input node to conversion
        workflow.connect(inputnode, 'in_file', convertPET, 'in_file')
        workflow.connect(inputnode, 'header', convertPET, 'header')

        pet_source = convertPET
        pet_file = "out_file" 
    elif quant_module.in_file_format == "MINC"  :
        pet_source = inputnode
        pet_file = "in_file" 
    elif quant_module.in_file_format == "NIFTI" :
        print("Error: NIFTI not yet implemented for quantification")
        exit(1)
    else :
        print("Error: not file format specified in module file.\nIn", quant_module_fn,"include:\nglobal file_format\nfile_format=<MINC/ECAT>")
        exit(1)

    ### Setup output from quantification function
    if quant_module.out_file_format == "ECAT" :
        # Node to convert ECAT to MINC
        #convertParametric=pe.Node(ecat2mincCommand(), name="convertParametric")
        convertParametric_to_minc=pe.Node(ecattomincCommand(), name="convertParametric_to_minc")
        convertParametric = pe.Node(interface=FixHeaderCommand(), name="convertParametric")
        
        #Connect quantification node to output node
        workflow.connect(tkaNode, 'out_file', convertParametric_to_minc, 'in_file')
        #workflow.connect(inputnode, 'like_file', convertParametric, 'like_file')
        #workflow.connect(inputnode, 'header', convertParametric, 'header')
        workflow.connect(convertParametric_to_minc, 'out_file', convertParametric, 'in_file')
        workflow.connect(inputnode, 'header', convertParametric, 'header')

        tka_source = convertParametric
    elif quant_module.out_file_format == "MINC"  :
        tka_source = tkaNode
    elif quant_module.out_file_format == "DFT"  :
        #Create 3/4D volume based on ROI values
        roi2img = pe.Node(interface= createImgFromROI(), name='img') 
        workflow.connect(inputnode, 'mask', roi2img, 'like_file')
        workflow.connect(tkaNode, 'out_file', roi2img, 'in_file')
        tka_source = roi2img
    elif quant_module.out_file_format == "NIFTI" :
        print("Error: NIFTI not yet implemented for quantification")
        exit(1)
    else :
        print("Error: not file format specified in module file.\nIn", quant_module_fn,"include:\nglobal file_format\nfile_format=<MINC/ECAT>")
        exit(1)

    ### ROI-based VS Voxel-wise quantification

    if quant_module.voxelwise :
        #Perform voxel-wise analysis
        #Connect convertPET to quant node
        workflow.connect(pet_source, pet_file, tkaNode, 'in_file')
    else : 
        convertROI=pe.Node(interface=minc2ecatCommand(), name="minctoecat_roi")
        extractROI=pe.Node(interface=img2dftCommand(), name="roimask_extract")
        workflow.connect(inputnode, 'mask', convertROI, 'in_file')
        workflow.connect(convertROI, 'out_file', extractROI, 'mask_file')
        #workflow.connect(tacReference, 'reference', tkaNode, 'reference')
        workflow.connect(pet_source, pet_file, extractROI, 'in_file')
        workflow.connect(extractROI, 'out_file', tkaNode, 'in_file')


    workflow.connect(tka_source, 'output_file', outputnode, 'out_file')
    
    ### Reference Region / TAC
    if  quant_module.reference :
        #Define an empty node for reference region
        tacReference = pe.Node(niu.IdentityInterface(fields=["reference"]), name='tacReference')

        if opts.arterial  :
            #Using arterial input file (which must be provided by user). 
            #No conversion or extraction necessary
            #Extract TAC from input image using reference mask
            workflow.connect(inputnode, 'reference', tkaReference, 'reference')
        else :
            if quant_module.in_file_format == "ECAT" :
                #Convert reference mask from minc to ecat
                convertReference=pe.Node(interface=minc2ecatCommand(), name="minctoecat_reference") 
                workflow.connect(inputnode, 'reference', convertReference, 'in_file')
                extractReference=pe.Node(interface=img2dftCommand(), name="referencemask_extract")
                # convertReference --> extractReference 
                workflow.connect(convertReference, 'out_file', extractReference, 'mask_file')
                workflow.connect(pet_source, pet_file, extractReference, 'in_file')
                # extractReference --> tacReference
                workflow.connect(extractReference, 'out_file', tacReference, 'reference')
            elif quant_module.in_file_format == "MINC" :
                # inputnode --> tacReference
                workflow.connect(inputnode, 'reference', tacReference, 'reference')
        
        workflow.connect(tacReference, 'reference', tkaNode, 'reference')


    return(workflow)


