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
from Extra.conversion import nii2mnc2Command, mnc2nii_shCommand, mnc2niiCommand
from Extra.extra import separate_mask_labelsCommand
from Extra.modifHeader import FixHeaderLinkCommand
"""
.. module:: pvc
    :platform: Unix
    :synopsis: Module to perform image registration.
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""


def get_pvc_workflow(name, infosource, opts):
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=['in_file', 'mask_file', 'header']), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=['out_file']), name='outputnode')

    mask_source=inputnode
    mask_file="mask_file"

    ### Quantification module
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+"/methods" )
    pvc_module_fn="pvc_method_"+opts.pvc_method #+".py"

    try :
        pvc_module = importlib.import_module(pvc_module_fn)
    except ImportError :
        print("Error: Could not find source file", pvc_module_fn, "corresponding to pvc method:", opts.pvc_method )
        exit(1)

    pvcNodeName=opts.pvc_method
    if opts.pvc_label_name != None :
        pvcNodeName += "_"+opts.pvc_label_name
    pvcNode = pe.Node(interface=pvc_module.pvcCommand(), name=pvcNodeName)
    pvcNode = pvc_module.check_options(pvcNode, opts)

    if pvc_module.separate_labels :
        separate_mask_labelsNode = pe.Node( separate_mask_labelsCommand(), name="separate_mask_labels")
        workflow.connect(inputnode, 'mask_file', separate_mask_labelsNode, 'in_file' )
        mask_source=separate_mask_labelsNode
        mask_file="out_file"

    pet_source = inputnode
    pet_file = "in_file"
    
    workflow.connect(pet_source, pet_file, pvcNode, 'in_file')
    workflow.connect(mask_source, mask_file, pvcNode, 'mask_file')

    workflow.connect(pvcNode, 'out_file', outputnode, 'out_file')
    return(workflow)
