# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a
import nipype.pipeline.engine as pe
import os
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
import numpy as np
import ntpath
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
import shutil
import sys
import importlib
from Extra.conversion import nii2mncCommand, mnc2niiCommand
from Extra.extra import separate_mask_labelsCommand
"""
.. module:: pvc
    :platform: Unix
    :synopsis: Module to perform image registration. 
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""


def get_pvc_workflow(name, infosource, datasink, opts):
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=['in_file', 'mask_file']), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=['out_file']), name='outputnode')
    
    mask_source=inputnode
    mask_file="mask_file"
    
    ### Quantification module
    print(os.path.dirname(os.path.abspath(__file__))+"/methods")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+"/methods" )
    pvc_module_fn="pvc_method_"+opts.pvc_method #+".py"
     
    pvc_module = importlib.import_module(pvc_module_fn)
    try :
        pvc_module = importlib.import_module(pvc_module_fn)
    except ImportError :
        print("Error: Could not find source file", pvc_module_fn, "corresponding to pvcification method:", opts.pvc_method )
        exit(1)
    
    pvcNode = pe.Node(interface=pvc_module.pvcCommand(), name=opts.pvc_method)
    pvcNode = pvc_module.check_options(pvcNode, opts)

    if pvc_module.separate_labels :
        separate_mask_labelsNode = pe.Node( separate_mask_labelsCommand(), name="separate_mask_labels")
        workflow.connect(inputnode, 'mask_file', separate_mask_labelsNode, 'in_file' )
        mask_source=separate_mask_labelsNode
        mask_file="out_file"


    if pvc_module.file_format == "NIFTI" : 
        convertPET=pe.Node(mnc2niiCommand(), name="convertPET")
        workflow.connect(inputnode, 'in_file', convertPET, 'in_file')

        convertMask=pe.Node(interface=mnc2niiCommand(), name="convertMask")
        workflow.connect(mask_source, mask_file, convertMask, 'in_file')

        convertPVC=pe.Node(nii2mncCommand(), name="convertPVC")
        workflow.connect(pvcNode, 'out_file', convertPVC, 'in_file')
        workflow.connect(inputnode, 'in_file', convertPVC, 'like_file')
        workflow.connect(convertPVC, 'out_file', outputnode, 'in_file')

        pet_source = convertPET
        pet_file = "out_file" 
        mask_source = convertMask
        mask_file="out_file"
       

    elif pvc_module.file_format == "MINC"  :
        pet_source = inputnode
        pet_file = "in_file" 

        workflow.connect(pvcNode, 'out_file', outputnode, 'out_file')
    else :
        print("Error: not file format specified in module file.\nIn", pvc_module_fn,"include:\nglobal file_format\nfile_format=<MINC/ECAT>")
        exit(1)

    workflow.connect(pet_source, pet_file, pvcNode, 'in_file')
    workflow.connect(mask_source, mask_file, pvcNode, 'mask_file')


    return(workflow)

