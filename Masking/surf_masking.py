import os
import numpy as np
import tempfile
import shutil
import pickle
import ntpath 

from pyminc.volumes.factory import *
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)

from Extra.obj import transform_objectCommand, volume_object_evaluateCommand

def get_surf_workflow(name, infosource, datasink, opts):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=["vol_file","obj_file","T1MNI", "MNIT1", "PETT1", "T1PET"]), name='inputnode')
    internode = pe.Node(niu.IdentityInterface(fields=["surface"]), name='internode')
    outputnode = pe.Node(niu.IdentityInterface(fields=["surface", "mask"]), name='outputnode')

    if opts.analysis_space == 'icbm152':
        if opts.surface_space == 'icbm152':
            workflow.connect(inputnode, 'obj_file', internode, 'surface')

        # MNI --> PET
        if opts.surface_space == 'pet' :
            transform_MNI_T1 = pe.Node( transform_object(), name="transform_MNI_T1")
            workflow.connect(inputnode, 'obj_file', transform_MNI_T1, 'in_file' )
            workflow.connect(inputnode, 'MNIT1', transform_MNI_T1, 'tfm_file' )
            
            transform_T1_PET = pe.Node( transform_object(), name="transform_T1_PET")
            workflow.connect(transform_MNI_T1, 'out_file', transform_T1_PET, 'in_file' )
            workflow.connect(inputnode, 'T1PET', transform_T1_PET, 'in_file' )
            
            workflow.connect(transform_T1_PET, 'out_file', internode, 'surface')

        # MNI --> T1
        if opts.surface_space == 't1' :
            transform_MNI_T1 = pe.Node( transform_object(), name="transform_MNI_T1")
            workflow.connect(inputnode, 'obj_file', transform_MNI_T1, 'in_file' )
            workflow.connect(inputnode, 'MNIT1', transform_MNI_T1, 'tfm_file' )

            workflow.connect(transform_MNI_T1, 'out_file', internode, 'surface')

    elif opts.analysis_space == 'pet':
        # PET --> MNI
        if opts.surface_space == 'icbm152' :
            transform_PET_T1 = pe.Node( transform_object(), name="transform_MNI_T1")
            workflow.connect(inputnode, 'obj_file', transform_PET_T1, 'in_file' )
            workflow.connect(inputnode, 'PETT1', transform_PET_T1, 'tfm_file' )
            
            transform_T1_MNI = pe.Node( transform_object(), name="transform_T1_MNI")
            workflow.connect(transform_T1_MNI, 'out_file', transform_T1_MNI, 'in_file' )
            workflow.connect(inputnode, 'T1MNI', transform_T1_MNI, 'in_file' )
            
            workflow.connect(transform_T1_MNI, 'out_file', internode, 'surface')
        
        if opts.surface_space == 'pet' :
            workflow.connect(inputnode, 'obj_file', internode, 'surface')
        
        # PET -> T1
        if opts.surface_space == 't1' :
            transform_PET_T1 = pe.Node( transform_object(), name="transform_MNI_T1")
            workflow.connect(inputnode, 'obj_file', transform_PET_T1, 'in_file' )
            workflow.connect(inputnode, 'PETT1', transform_PET_T1, 'tfm_file' )
            
            workflow.connect(transform_PET_T1, 'out_file', internode, 'surface')

    elif opts.analysis_space == 't1':

        # T1 --> MNI
        if opts.surface_space == 'icbm152' :
            transform_T1_MNI = pe.Node( transform_object(), name="transform_T1_MNI")
            workflow.connect(inputnode, 'obj_file', transform_T1_MNI, 'in_file' )
            workflow.connect(inputnode, 'T1MNI', transform_T1_MNI, 'tfm_file' )

            workflow.connect(transform_T1_MNI, 'out_file', internode, 'surface')

        # T1 --> PET
        if opts.surface_space == 'pet' :
            transform_T1_PET = pe.Node( transform_object(), name="transform_T1_PET")
            workflow.connect(inputnode, 'obj_file', transform_T1_PET, 'in_file' )
            workflow.connect(inputnode, 'PETT1', transform_T1_PET, 'tfm_file' )

            workflow.connect(transform_T1_PET, 'out_file', internode, 'surface')

        if opts.surface_space == 't1' :
            workflow.connect(inputnode, 'obj_file', internode, 'surface')
    else :
        print("Error: variable <analysis_space> was not one of : icbm152, pet, t1")
        exit(1)

    volume_interpolateNode = pe.Node( volume_object_evaluateCommand(), name="volume_interpolate"  )
    workflow.connect(internode, 'surface', volume_interpolateNode, 'obj_file')
    workflow.connect(inputnode, 'vol_file', volume_interpolateNode, 'vol_file')

    workflow.connect(volume_interpolateNode, 'out_file', outputnode, 'mask' )
    workflow.connect(internode, 'surface', outputnode, 'surface' )

    return(workflow)
