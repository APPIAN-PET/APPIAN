import os
import ntpath
import nipype.pipeline.engine as pe
import re
import pandas as pd
import json
from sys import argv
import numpy as np
import json
import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
import nipype.interfaces.minc as minc
from resample import param2xfmCommand
from modifHeader import ModifyHeaderCommand, FixHeaderCommand
from shutil import move, copyfile
import nibabel as nib
from sys import argv
from re import sub
from pyminc.volumes.factory import *
from turku import imgunitCommand, e7emhdrInterface, eframeCommand, sifCommand
from time import gmtime, strftime
import time

np.random.seed(int(time.time()))

class convertOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class convertInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")
    two= traits.Bool(argstr="-2", usedefault=True, default_value=True, desc="Convert from minc 1 to minc 2")
    clobber= traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite existing file")

class mincconvertCommand(CommandLine):
    input_spec =  convertInput
    output_spec = convertOutput

    _cmd = "mincconvert"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = list(os.path.splitext(fname)) # [0]= base filename; [1] =extension
        print fname_list
        if "_mnc1"  in  fname_list[0] :
            fname_list[0]=re.sub("_mnc1", "", fname_list[0])
        elif "_mnc2"  in fname_list[0] :
            fname_list[0]=re.sub("_mnc2", "", fname_list[0])
        elif self.inputs.two: #Converting from minc1 to minc
            fname_list[0] = fname_list[0] + "_mnc2"
        else: #Converting from minc to minc1
            fname_list[0] = fname_list[0] + "_mnc1"


        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(mincconvertCommand, self)._parse_inputs(skip=skip)



##################
### minctoecat ###
##################
def minctoecatWorkflow(name):
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputNode = pe.Node(niu.IdentityInterface(fields=["in_file", "header"]), name='inputNode')
    conversionNode = pe.Node(interface=minctoecatInterfaceCommand(), name="conversionNode")
    #conversionNode.inputs.out_file=name+'.v'
    sifNode = pe.Node(interface=sifCommand(), name="sifNode")
    eframeNode = pe.Node(interface=eframeCommand(), name="eframeNode")
    ###imgunitNode = pe.Node(interface=imgunitCommand(), name="imgunitCommand")
    ###imgunitNode.inputs.u = "Bq/cc"
    outputNode = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputNode')

    workflow.connect(inputNode, 'in_file', conversionNode, 'in_file')
    workflow.connect(inputNode, 'in_file', sifNode, 'in_file')
    workflow.connect(inputNode, 'header', sifNode, 'header')

    workflow.connect(conversionNode, 'out_file', outputNode, 'out_file')
    workflow.connect(conversionNode, 'out_file', eframeNode, 'pet_file')
    workflow.connect(sifNode, 'out_file', eframeNode, 'frame_file')
    ###workflow.connect(eframeNode, 'out_file', imgunitNode, 'in_file')
    ###workflow.connect(imgunitNode, 'out_file', outputNode, 'out_file')

    return(workflow)


class ecat2mincOutput(TraitedSpec):
    out_file = File(desc="PET image with correct time frames.")

class ecat2mincInput(CommandLineInputSpec):
    in_file = File(exists=True, mandatory=True, desc="PET file")
    header  = File(exists=True, desc="PET header file")
    out_file= File(argstr="%s", desc="MINC PET file")
    like_file= File(exists=True, mandatory=True, desc="Template MINC file")
#tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a hlsearch

class ecat2mincCommand(BaseInterface):
    input_spec = ecat2mincInput
    output_spec = ecat2mincOutput

    def _run_interface(self, runtime):
        in_fn = self.inputs.in_file
        like_fn = self.inputs.like_file
        fn = os.path.splitext(os.path.basename(self.inputs.in_file))
        self.inputs.out_file = out_fn =  os.getcwd() +os.sep+ fn[0]+ '.mnc'
        ecat_vol = nib.ecat.load(in_fn)
        minc_vol = volumeLikeFile(like_fn, out_fn)
        data = ecat_vol.get_data()
        data = data.reshape(minc_vol.data.shape)

        print(minc_vol.data.shape)
        print(data.shape)
        #for y in range(data.shape[1]):
        #    temp = np.copy(data[:,y,:])
        #    for z in range(temp.shape[0]) :
        #        for x in range(temp.shape[1]) :
        #    data[z,y,x] = temp[x,z]
        #    #out_data[:,y,:] = temp.reshape(temp.shape[1],temp.shape[0])
        #    del temp

        minc_vol.data = data
        minc_vol.writeFile()
        minc_vol.closeVolume()

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


class ecattominc2Output(TraitedSpec):
    out_file = File(desc="PET image with correct time frames.")

class ecattominc2Input(CommandLineInputSpec):
    in_file = File(exists=True, mandatory=True, desc="PET file")
    out_file= File(argstr="%s", desc="MINC PET file")
    header= File(argstr="%s", desc="Optional header file")
#tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a hlsearch

class ecattominc2Command(BaseInterface):
    input_spec = ecattominc2Input
    output_spec = ecattominc2Output

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)

        node1 = ecattomincCommand()
        node1.inputs.in_file = self.inputs.in_file
        node1.inputs.out_file =os.getcwd()+"/tmp_mnc_"+ strftime("%Y%m%d%H%M%S", gmtime())+str(np.random.randint(9999999999))+".mnc"
        node1.run()

        node2 = mincconvertCommand()
        node2.inputs.in_file = node1.inputs.out_file
        node2.inputs.out_file = os.getcwd()+"/tmp_mnc_"+ strftime("%Y%m%d%H%M%S", gmtime())+str(np.random.randint(9999999999))+".mnc"
        node2.run()
        os.remove(node1.inputs.out_file)

        if isdefined(self.inputs.header) :
            node3 = FixHeaderCommand()
            node3.inputs.in_file = node2.inputs.out_file
            node3.inputs.header = self.inputs.header
            node3.run()
            move(node3.inputs.output_file, self.inputs.out_file)
        else :
            move(node2.inputs.out_file, self.inputs.out_file)


        header_dict = json.load(open(self.inputs.header, 'r+'))
        if float(header_dict["zspace"]["step"][0]) > 0 :
            temp_fn=os.getcwd()+"/tmp_mnc_"+ strftime("%Y%m%d%H%M%S", gmtime())+str(np.random.randint(9999999999))+".mnc"
            vol = volumeFromFile(self.inputs.out_file)
            vol2 = volumeLikeFile(self.inputs.out_file, temp_fn)
            vol2.data = np.flipud(vol.data)
            vol2.writeFile()
            vol2.closeVolume()
            move(temp_fn, self.inputs.out_file)
        return runtime

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        outputs["out_file"] = self.inputs.out_file
        return outputs



def ecattomincWorkflow(name):
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputNode = pe.Node(niu.IdentityInterface(fields=["in_file", "header"]), name='inputNode')
    conversionNode = pe.Node(interface=ecattomincCommand(), name="conversionNode")
    mincConversionNode = pe.Node(interface=mincconvertCommand(), name="mincConversionNode")
    fixHeaderNode = pe.Node(interface=FixHeaderCommand(), name="fixHeaderNode")
    paramNode = pe.Node(interface=param2xfmCommand(), name="param2xfmNode")
    paramNode.inputs.rotation = "0 180 0"
    resampleNode = pe.Node(interface=minc.Resample(), name="resampleNode")
    resampleNode.inputs.vio_transform=True
    outputNode  = pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputNode')

    workflow.connect(inputNode, 'in_file', conversionNode, 'in_file')
    workflow.connect(conversionNode, 'out_file', fixHeaderNode, 'in_file')
    workflow.connect(inputNode, 'header', fixHeaderNode, 'header')
    workflow.connect(fixHeaderNode, 'out_file', outputNode, 'out_file')

    return(workflow)

class minc2ecatOutput(TraitedSpec):
    out_file = File(desc="PET image with correct time frames.")
    #out_file_bkp = File(desc="PET image with correct times frames backup.")

class minc2ecatInput(CommandLineInputSpec):
    in_file = File(exists=True, desc="PET file")
    header  = File( desc="header information")
    out_file= File(argstr="%s", position=-2, desc="PET file")


class minc2ecatCommand(BaseInterface):
    input_spec =  minc2ecatInput
    output_spec = minc2ecatOutput

    def _run_interface(self, runtime):
        conversionNode = minctoecatInterfaceCommand()
        conversionNode.inputs.in_file = self.inputs.in_file
        conversionNode.run()

        if isdefined(self.inputs.header):
            isotopeNode = e7emhdrInterface()
            isotopeNode.inputs.in_file = conversionNode.inputs.out_file
            isotopeNode.inputs.header = self.inputs.header
            isotopeNode.run()

            sifNode = sifCommand()
            sifNode.inputs.in_file = self.inputs.in_file
            sifNode.inputs.header = self.inputs.header
            sifNode.run()

            eframeNode = eframeCommand()
            eframeNode.inputs.frame_file = sifNode.inputs.out_file
            eframeNode.inputs.pet_file = isotopeNode.inputs.out_file
            eframeNode.run()

            imgunitNode = imgunitCommand()
            imgunitNode.inputs.in_file = eframeNode.inputs.pet_file
            imgunitNode.inputs.u = "Bq/cc"
            imgunitNode.run()

            self.inputs.out_file = imgunitNode.inputs.out_file
        else :
            self.inputs.out_file = conversionNode.inputs.out_file

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs




class minctoecatOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class minctoecatInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")

class minctoecatCommand(CommandLine):
    input_spec =  minctoecatInput
    output_spec = minctoecatOutput
    _cmd = "minctoecat"

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".v"

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)

        return super(minctoecatCommand, self)._parse_inputs(skip=skip)

class minctoecatInterfaceOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Output ECAT file.")

class minctoecatInterfaceInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="Input MINC file")

class minctoecatInterfaceCommand(BaseInterface):
    input_spec =  minctoecatInterfaceInput
    output_spec = minctoecatInterfaceOutput

    def _run_interface(self, runtime):
        #Apply threshold and create and write outputfile
        cmd = minctoecatCommand();
        cmd.inputs.in_file = self.inputs.in_file
        cmd.inputs.out_file = "temp.v"
        print cmd.cmdline
        cmd.run()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        print("mv", cmd.inputs.out_file, self.inputs.out_file)
        copyfile(cmd.inputs.out_file, self.inputs.out_file)

        return runtime
    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".v"

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)

        return super(minctoecatInterfaceCommand, self)._parse_inputs(skip=skip)





class nii2mncOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="convert from nifti to minc")

class nii2mncInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="minc file")
    like_file = File( argstr="%s", position=-1, desc="minc file")
    in_file= File(exists=True, argstr="%s", position=-2, desc="nifti file")

class nii2mncCommand(BaseInterface):
    input_spec =  nii2mncInput
    output_spec = nii2mncOutput

    _cmd = "nii2mnc"
    def _run_interface(self, runtime):
        if not isdefined(self.inputs.like_file) :
            node = pe.Node(interface=nii2mnc_shCommand, in_file=self.inputs.in_file, name="nii2mnc")
            node.run()
            self.inputs.out_file=node.inputs.out_file
            return runtime
        in_fn = self.inputs.in_file
        fn = os.path.splitext(os.path.basename(self.inputs.in_file))
        self.inputs.out_file = out_fn =  os.getcwd() +os.sep+ fn[0]+ '.mnc'

        minc_vol = volumeLikeFile(self.inputs.like_file, out_fn)
        test = nib.nifti1.load(in_fn)

        if len(test.shape) > 3 :
            tmax = test.shape[3]
        else :
            tmax = 1

        zmax=test.shape[0]
        ymax=test.shape[1]
        xmax=test.shape[2]
        if len(test.shape) > 4 :
            ar = np.zeros([tmax,zmax,ymax,xmax])
        else :
            ar = np.zeros([zmax,ymax,xmax])

        zz, yy, xx = np.meshgrid(range(zmax), range(ymax), range(xmax) )
        zz = zz.flatten()
        yy = yy.flatten()
        xx = xx.flatten()
        data =  np.copy(test.dataobj)

        print("data", data.shape)
        print("ar", ar.shape)
        print(minc_vol.data.shape)
        if tmax > 1 :
            for t in range(tmax) :
                ar[t,zz,yy,xx] = data[zz,yy,xx,t]
        else :
            ar[zz,yy,xx] = data[zz,yy,xx]


        minc_vol.data = ar
        minc_vol.writeFile()
        minc_vol.closeVolume()

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(nii2mncCommand, self)._parse_inputs(skip=skip)



class mnc2niiOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="convert from minc to nii")

class mnc2niiInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="nii file")
    in_file= File(exists=True, argstr="%s", position=-2, desc="minc file")

class mnc2niiCommand(BaseInterface):
    input_spec =  mnc2niiInput
    output_spec = mnc2niiOutput

    #_cmd = "mnc2nii"

    def _run_interface(self, runtime):
        in_fn = self.inputs.in_file
        fn = os.path.splitext(os.path.basename(self.inputs.in_file))
        self.inputs.out_file = out_fn =  os.getcwd() +os.sep+ fn[0]+ '.nii'

        test = nib.minc2.load(in_fn)
        
        if len(test.shape) >= 4 :
            tmax = test.shape[0]
            offset = 1
        else :
            tmax = 1
            offset = 0
        zmax=test.shape[offset+0]
        ymax=test.shape[offset+1]
        xmax=test.shape[offset+2]

        if len(test.shape) > 3 :
            ar = np.zeros([zmax,ymax,xmax,tmax])
        else :
            ar = np.zeros([zmax,ymax,xmax])

        zz, yy, xx = np.meshgrid(range(zmax), range(ymax), range(xmax) )
        zz = zz.flatten()
        yy = yy.flatten()
        xx = xx.flatten()
        data =  np.copy(test.dataobj)

        if tmax > 1 :
            for t in range(tmax) :
                ar[zz,yy,xx,t] = data[t,zz,yy,xx]
        else :
            ar[zz,yy,xx] = data[zz,yy,xx]

        out = nib.nifti1.Nifti1Image(ar , test.affine)
        nib.save( out, out_fn )

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".nii"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(mnc2niiCommand, self)._parse_inputs(skip=skip)


class mnc2nii_shOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="convert from minc to nii")

class mnc2nii_shInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="nii file")
    in_file= File(exists=True, argstr="%s", position=-2, desc="minc file")
    truncate_path = traits.Bool(  default=False, use_default=True, desc="truncate file path for output file")

class mnc2nii_shCommand(CommandLine):
    input_spec =  mnc2nii_shInput
    output_spec = mnc2nii_shOutput
    _cmd = "mnc2nii"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        if self.inputs.truncate_path :
            fname = ntpath.basename(basefile)
        else :
            fname = basefile

        print("File Name:", fname)
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".nii"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(mnc2nii_shCommand, self)._parse_inputs(skip=skip)

class nii2mnc_shOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="convert from minc to nii")

class nii2mnc_shInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="nii file")
    _xor_dtype=('dfloat', 'ddouble', 'dbyte', 'dint', 'dshort' )
    dfloat = traits.Bool(argstr="-float", position=-3, desc="data type", xor=_xor_dtype )
    ddouble = traits.Bool(argstr="-double", position=-3, desc="data type", xor=_xor_dtype )
    dbyte = traits.Bool(argstr="-byte", position=-3, desc="data type", xor=_xor_dtype )
    dint = traits.Bool(argstr="-int", position=-3, desc="data type", xor=_xor_dtype )
    dshort = traits.Bool(argstr="-short", position=-3, desc="data type", xor=_xor_dtype )
    in_file= File(exists=True, argstr="%s", position=-2, desc="minc file", xor=_xor_dtype)
    truncate_path = traits.Bool(  default=False, use_default=True, desc="truncate file path for output file")

class nii2mnc_shCommand(CommandLine):
    input_spec =  nii2mnc_shInput
    output_spec = nii2mnc_shOutput

    _cmd = "nii2mnc"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        if self.inputs.truncate_path :
            fname = ntpath.basename(basefile)
        else :
            fname = basefile

        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(nii2mnc_shCommand, self)._parse_inputs(skip=skip)

class nii2mnc2Command(BaseInterface):
    input_spec =  nii2mnc_shInput
    output_spec = nii2mnc_shOutput

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)

        temp_fn = os.getcwd()+"/tmp_mnc_"+ strftime("%Y%m%d%H%M%S", gmtime())+str(np.random.randint(9999999999))+".mnc"
        convert = nii2mnc_shCommand()
        convert.inputs.in_file=self.inputs.in_file
        convert.inputs.out_file=temp_fn

        convert.inputs.dfloat = self.inputs.dfloat 
        convert.inputs.dint = self.inputs.dint
        print(convert.cmdline)
        convert.run()

        minc2 = mincconvertCommand()
        minc2.inputs.in_file=temp_fn
        minc2.inputs.out_file=self.inputs.out_file
        minc2.inputs.two=True
        print(minc2.cmdline)
        minc2.run()

        move(minc2.inputs.out_file, self.inputs.out_file)
        os.remove(temp_fn)
        return runtime
    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self, basefile):
        if self.inputs.truncate_path :
            fname = ntpath.basename(basefile)
        else :
            fname = basefile

        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        if '.gz' in fname_list :
            fname_list = os.path.splitext(fname_list[0])
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(nii2mnc2Command, self)._parse_inputs(skip=skip)


##################
### ecattominc ###
##################

class ecattomincOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Logan Plot distribution volume (DVR) parametric image.")

class ecattomincInput(CommandLineInputSpec):
    out_file = File( argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, argstr="%s", position=-2, desc="PET file")

class ecattomincCommand(CommandLine):
    input_spec =  ecattomincInput
    output_spec = ecattomincOutput

    _cmd = "ecattominc"

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    #def _gen_filename(self, name):
    #    if name == "out_file":
    #        return self._list_outputs()["out_file"]
    #    return None

    def _gen_output(self, basefile):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd()
        return dname+ os.sep+fname_list[0] + ".mnc"

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file)
        return super(ecattomincCommand, self)._parse_inputs(skip=skip)
