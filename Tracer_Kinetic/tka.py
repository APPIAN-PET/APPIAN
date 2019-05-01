from pyminc.volumes.factory import *
from nipype.interfaces.utility import Function
from nipype.interfaces.base import TraitedSpec, File, traits, InputMultiPath, BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined
from nipype.utils.filemanip import load_json, save_json, split_filename, fname_presuffix, copyfile

from Extra.base import MINCCommand, MINCCommandInputSpec
from Extra.conversion import (ecat2mincCommand, minc2ecatCommand, ecattomincCommand, minctoecatInterfaceCommand, minctoecatWorkflow, mincconvertCommand, ecattominc2Command)
from Extra.modifHeader import FixHeaderLinkCommand
from Turku.dft import img2dft_unit_conversion
from Extra.extra import subject_parameterCommand
from Extra.turku import imgunitCommand
from Extra.turku import JsonToSifCommand
from Registration.ants_mri_normalize import APPIANApplyTransforms
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
import ntpath
import numpy as np
import os
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
        ref = nib.load(self.inputs.like_file)
        ref_data = ref.get_data()
        out_data = np.zeros(ref_data.shape)
        roi=[]
        with open(self.inputs.in_file) as f :
            for l in f.readlines() :
                if 'Mask' in l : 
                    ll=re.split(' |\t', l)
                    roi.append([int(ll[1]), float(ll[3])])

        for label, value in roi : 
            out_data[ref_data == label] = value
        
        out = nib.Nifti1Image(out_data, ref.get_affine())
        out.to_filename(self.inputs.out_file )

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
    inputnode = pe.Node(niu.IdentityInterface(fields=["stereo","tfm_mri_stx", "tfm_pet_mri", "like_file", "in_file", "header",  "reference", "mask", "like_file"] ), name='inputnode')

    out_files = ["out_file", "out_file_stereo"]
    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=out_files), name='outputnode')

    ### Quantification module
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+"/methods/" )
    print(os.path.dirname(os.path.abspath(__file__))+"/methods/") 
    quant_module_fn="quant_method_"+opts.tka_method #+".py"

    #quant_module = importlib.import_module(quant_module_fn)
    try :
        quant_module = importlib.import_module(quant_module_fn)
    except ImportError :
        print("Error: Could not find source file",quant_module_fn,"corresponding to quantification method:",opts.tka_method)
        exit(1)

    tkaNodeName=opts.tka_method
    
    if opts.pvc_label_name != None :
        tkaNodeName += "_"+opts.pvc_label_name
    if opts.quant_label_name != None :
        tkaNodeName += "_"+opts.quant_label_name

    try :
        tkaNode = pe.Node(interface=quant_module.QuantCommandWrapper(), name=tkaNodeName)
    except AttributeError :
        tkaNode = pe.Node(interface=quant_module.quantCommand(), name=tkaNodeName)

    tkaNode = quant_module.check_options(tkaNode, opts)
 
    #If the quantification node takes a header input, then pass it from inputnode
    try : 
        tkaNode.inputs.header
        workflow.connect(inputnode, 'header', tkaNode, 'header')
    except AttributeError :
        pass
   
    pet_source = inputnode
    pet_file = "in_file" 
    
    ### Setup output from quantification function
    if quant_module.out_file_format == "ECAT" :
        # Node to convert ECAT to MINC
        convertParametric=pe.Node(ecattominc2Command(), name="convertParametric")
        
        #Connect quantification node to output node
        workflow.connect(tkaNode, 'out_file', convertParametric, 'in_file')
        workflow.connect(inputnode, 'header', convertParametric, 'header')

        tka_source = convertParametric
    elif quant_module.out_file_format == "NIFTI"  :
        tka_source = tkaNode
    elif quant_module.out_file_format == "DFT"  :
        #Create 3/4D volume based on ROI values
        roi2img = pe.Node(interface=createImgFromROI(), name='img') 
        workflow.connect(inputnode, 'mask', roi2img, 'like_file')
        workflow.connect(tkaNode, 'out_file', roi2img, 'in_file')
        tka_source = roi2img
    elif quant_module.out_file_format == "MINC" :
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
        extractROI=pe.Node(interface=img2dft_unit_conversion(), name="roimask_extract")
        workflow.connect(inputnode, 'mask', extractROI, 'mask_file')
        workflow.connect(inputnode, 'header', extractROI, 'pet_header_json')
        workflow.connect(pet_source, pet_file, extractROI, 'in_file')
        workflow.connect(extractROI, 'out_file', tkaNode, 'in_file')

    turku_methods = [ 'lp', 'lp-roi', 'pp', 'pp-roi', 'srtm', 'srtm-roi' ]
    #If the Quantification method is from the Turku PET Centre tools, need to create .sif
    if opts.tka_method in turku_methods:
        JsonToSifNode = pe.Node( JsonToSifCommand(), 'sif'  )
        workflow.connect(pet_source, pet_file, JsonToSifNode, 'pet')
        workflow.connect(inputnode, 'header', JsonToSifNode, 'pet_header_json')
        workflow.connect(JsonToSifNode, 'out_file', tkaNode, 'sif' )

    workflow.connect(tka_source, 'out_file', outputnode, 'out_file')
   
    if opts.quant_to_stereo and not opts.analysis_space == "stereo" :
        quant_to_stereo = pe.Node( APPIANApplyTransforms(), name="quant_stereo"  )
        workflow.connect(inputnode, 'tfm_mri_stx', quant_to_stereo, "transform_2")
        if opts.analysis_space=='pet' :
            workflow.connect(inputnode, 'tfm_pet_mri', quant_to_stereo, "transform_3")
        workflow.connect(inputnode, 'stereo', quant_to_stereo, "reference_image")
        workflow.connect(tka_source, 'out_file', quant_to_stereo, "input_image")
        workflow.connect(quant_to_stereo, 'output_image', outputnode, 'out_file_stereo')
        quant_to_stereo.inputs.tricubic_interpolation = True


    ### Reference Region / TAC
    if  quant_module.reference :
        #Define an empty node for reference region
        tacReference = pe.Node(niu.IdentityInterface(fields=["reference"]), name='tacReference')

        if opts.arterial  :
            #Using arterial input file (which must be provided by user). 
            #No conversion or extraction necessary
            #Extract TAC from input image using reference mask
            workflow.connect(inputnode, 'reference', tacReference, 'reference')
        else :
            if quant_module.in_file_format == "NIFTI" and opts.tka_method in turku_methods :
                #Convert reference mask from minc to ecat
                extractReference=pe.Node(interface=img2dft_unit_conversion(), name="referencemask_extract")
                workflow.connect(inputnode, 'header', extractReference, 'pet_header_json')
                # convertReference --> extractReference 
                workflow.connect(inputnode, 'reference', extractReference, 'mask_file')
                workflow.connect(pet_source, pet_file, extractReference, 'in_file')
                workflow.connect(extractReference, 'out_file', tacReference, 'reference')
            else : # quant_module.in_file_format == "NIFTI" :
                # inputnode --> tacReference
                workflow.connect(inputnode, 'reference', tacReference, 'reference')
        
        workflow.connect(tacReference, 'reference', tkaNode, 'reference')


    return(workflow)


