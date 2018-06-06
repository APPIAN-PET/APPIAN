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

class gtmInput(CommandLineInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask = File( position=2, argstr="-mask %s", desc="Integer mask file")
    input_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    fwhm = traits.Float( argstr="-fwhm %f", desc="FWHM of PSF all axes")
     
class gtmOutput(TraitedSpec):
    out_file = File(argstr="-o %s", exists=True, desc="Output PET image")

class gtmCommand(CommandLine):
    input_spec =  gtmInput
    output_spec = gtmOutput
    _cmd='gtm'
    _suffix='gtm'

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.input_file, self._suffix)
        outputs["out_file"] = self.inputs.out_file
        return outputs

class idSURFInput(CommandLineInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask = File( position=2, argstr="-mask %s", desc="Integer mask file")
    input_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    fwhm = traits.Float( argstr="-fwhm %f", desc="FWHM of PSF all axes")
     
    max_iterations = traits.Int(argstr="-max-iterations %d", desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-tolerance %f", desc="Tolerance")
    nvoxel_to_average = traits.Int( argstr="-nvoxel-to-average %f", desc="Number of voxels to average over.")
class idSURFOutput(TraitedSpec):
    out_file = File(argstr="-o %s", exists=True, desc="Output PET image")

class idSURFCommand(CommandLine):
    input_spec =  idSURFInput
    output_spec = idSURFOutput
    _cmd='idSURF'
    _suffix='idSURF'

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.input_file, self._suffix)
        outputs["out_file"] = self.inputs.out_file
        return outputs

class petpvcInput(CommandLineInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask = File( position=2, argstr="-mask %s", desc="Integer mask file")
    input_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    z_fwhm = traits.Float( argstr="-z %f", desc="FWHM of PSF along z-axis")
    y_fwhm = traits.Float( argstr="-y %f", desc="FWHM of PSF along y-axis")
    x_fwhm = traits.Float( argstr="-x %f", desc="FWHM of PSF along x-axis")

    max_iterations = traits.Int(argstr="-k %d", desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-s %f", desc="Tolerance")
class petpvcOutput(TraitedSpec):
    out_file = File(argstr="-o %s", exists=True, desc="Output PET image")

class petpvcCommand(CommandLine):
    input_spec =  petpvcInput
    output_spec = petpvcOutput
    _cmd='petpvc'
    _suffix='petpvc'

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.input_file, self.inputs.pvc_method)
        outputs["out_file"] = self.inputs.out_file
        return outputs


class PVCInput(CommandLineInputSpec):
    out_file = File(position=3, argstr="-o %s",desc="image to operate on")
    mask = File( position=2, argstr="-mask %s", desc="Integer mask file")
    input_file = File(exists=True, position=1, argstr="-pet %s", desc="PET file")
    z_fwhm = traits.Float( argstr="-z %f", desc="FWHM of PSF along z-axis")
    y_fwhm = traits.Float( argstr="-y %f", desc="FWHM of PSF along y-axis")
    x_fwhm = traits.Float( argstr="-x %f", desc="FWHM of PSF along x-axis")
    fwhm = traits.Float( argstr="-fwhm %f", desc="FWHM of PSF all axes")
     
    max_iterations = traits.Int(argstr="-max-iterations %d", desc="Maximum number of iterations")
    tolerance = traits.Float( argstr="-tolerance %f", desc="Tolerance")
    nvoxel_to_average = traits.Int( argstr="-nvoxel-to-average %f", desc="Number of voxels to average over.")
    pvc_method = traits.Str(argstr="--pvc %s",mandatory=False, desc="PVC type")
  
class PVCOutput(TraitedSpec):
    out_file = File( desc="Output PET image in T1 native space")

import shutil
"""
.. module:: pvc
    :platform: Unix
    :synopsis: Module to perform image registration. 
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""
class PVCCommand(BaseInterface):
    input_spec =  PVCInput
    output_spec = PVCOutput
    #def __init__(self, pvc_method):
    #    pass
    #self._cmd = pvc_method 
    #    self._suffix = "_" + self._cmd 

    def _run_interface(self, runtime):
        petpvc_method_list=['LABBE', "RL", "VC", "RBV", "LABBE+RBV", "RBV+VC", "RBV+RL", "LABBE+RBV+VC", "LABBE+RBV+RL", "STC", "MTC", "LABBE+MTC", "MTC+VC", "MTC+RL", "LABBE+MTC+VC", "LABBE+MTC+RL", "IY", "IY+VC", "IY+RL", "MG", "MG+VC", "MG+RL" ]
        #pvc_method_dict = { 'GTM':gtm, 'idSURF':idSURF, petpvc_method_list   }
        
        self._suffix=self.inputs.pvc_method
        if self.inputs.pvc_method in ['GTM', 'gtm'] :
            pvcNode = gtmCommand()
            pvcNode.inputs.fwhm = self.inputs.fwhm
            pvcNode.inputs.input_file = self.inputs.input_file
            pvcNode.inputs.mask = self.inputs.mask
            pvcNode.inputs.out_file = self._gen_output(self.inputs.input_file, self.inputs.pvc_method)
            pvcNode.run()
        elif self.inputs.pvc_method == 'idSURF':
            pvcNode = idSURFCommand()
            pvcNode.inputs.fwhm = self.inputs.z_fwhm
            pvcNode.inputs.input_file = self.inputs.input_file
            pvcNode.inputs.mask = self.inputs.mask
            pvcNode.inputs.tolerance= self.inputs.tolerance
            pvcNode.inputs.nvoxel_to_average = self.inputs.nvoxel_to_average
            pvcNode.inputs.max_iterations = self.inputs.max_iterations
            pvcNode.inputs.out_file = self._gen_output(self.inputs.input_file, self.inputs.pvc_method)
            pvcNode.run()
        elif self.inputs.pvc_method in petpvc_method_list:
            pvcNode = petpvcCommand()
            pvcNode.inputs.z_fwhm = self.inputs.z_fwhm
            pvcNode.inputs.y_fwhm = self.inputs.y_fwhm
            pvcNode.inputs.x_fwhm = self.inputs.x_fwhm
            pvcNode.inputs.input_file = self.inputs.input_file
            pvcNode.inputs.mask = self.inputs.mask
            pvcNode.inputs.pvc_method = self.inputs.pvc_method
            pvcNode.inputs.max_iterations = self.inputs.max_iterations
            pvcNode.inputs.tolerance = self.inputs.tolerance
            pvcNode.inputs.out_file = self._gen_output(self.inputs.input_file, self.inputs.pvc_method)
            pvcNode.run()
        print pvcNode.cmdline
        print '\n\nPVC:', pvcNode.inputs.out_file, '\n\n'

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.input_file, self.inputs.pvc_method)
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
        print  dname, os.sep+fname_list[0], _suffix, fname_list[1]

        return dname+ os.sep+fname_list[0] + '_'+ _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.input_file, self._suffix)
        return super(PVCCommand, self)._parse_inputs(skip=skip)

'''class PVCCommand(CommandLine):
    input_spec =  PVCInput
    output_spec = PVCOutput
    _cmd='idSURF'
    _suffix='_idSURF' 
    #FIXME: Should make this node with basicinterface so that it can have multiple "subnodes"
    # that will execute the proper pvc technique
    #def __init__(self, pvc_method):
    #    pass
    #self._cmd = pvc_method 
    #    self._suffix = "_" + self._cmd 

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
            self.inputs.out_file = self._gen_output(self.inputs.input_file, self._suffix)
        return super(PVCCommand, self)._parse_inputs(skip=skip)
'''

'''
def get_workflow(name, infosource, datasink, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_center", "pet_mask"]), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputnode')
    node_name=opts.pvc_method
    PVCNode = pe.Node(interface=PVCCommand(), name=node_name)
    if opts.pvc_method == "gtm":
        PVCNode.inputs.fwhm = opts.scanner_fwhm[0]
    elif opts.pvc_method == "idSURF":
        PVCNode.inputs.fwhm = opts.scanner_fwhm[0]
        PVCNode.inputs.max_iterations = opts.max_iterations
        PVCNode.inputs.tolerance = opts.tolerance
        #PVCNode.inputs.denoise_fwhm = opts.denoise_fwhm
        #PVCNode.inputs.lambda_var = opts.lambda_var
        PVCNode.inputs.nvoxel_to_average=opts.nvoxel_to_average
    else:
        PVCNode.inputs.z_fwhm = opts.scanner_fwhm[0]
        PVCNode.inputs.y_fwhm = opts.scanner_fwhm[1]
        PVCNode.inputs.x_fwhm = opts.scanner_fwhm[2]
        PVCNode.inputs.pvc_method = opts.pvc_method
    workflow.connect([
                    (inputnode, PVCNode, [('pet_center','input_file')]),
                    (inputnode, PVCNode, [('pet_mask','mask')])
                    ])
    workflow.connect(PVCNode, 'out_file', datasink, 'pvc')
    workflow.connect(PVCNode, 'out_file', outputnode, "out_file")

    return(workflow)
'''
