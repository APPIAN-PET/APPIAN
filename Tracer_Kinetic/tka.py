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
from Turku.dft import img2dftCommand
from Extra.extra import subject_parameterCommand
from Extra.turku import imgunitCommand
import ntpath
import numpy as np
import re

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

class suvrOutput(TraitedSpec):
    out_file = File(argstr="%s", position=-1, desc="Output SUV image.")

class suvrInput(MINCCommandInputSpec):
    
    pet_file = File(exists=True,mandatory=True, desc="PET file")
    reference = File(exists=True,mandatory=True,desc="Mask file")
    header = traits.Dict(desc="Input file ")

    out_file = File(desc="Output SUV image")

class suvrCommand(BaseInterface):
    input_spec =  suvrInput
    output_spec = suvrOutput

    _suffix = "_suvr" 
    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file) : self.inputs.out_file = self._gen_output(self.inputs.pet_file, self._suffix)
        print self.inputs.pet_file
        print self.inputs.reference
        header = self.inputs.header
        pet = volumeFromFile(self.inputs.pet_file)
        reference = volumeFromFile(self.inputs.reference)
        out = volumeLikeFile(self.inputs.reference, self.inputs.out_file )
        ndim = len(pet.data.shape)
        
        vol = pet.data
        if ndim > 3 :
            try : 
                float(header['time']['frames-time'][0]) 
                time_frames = [ float(h) for h in  header['time']["frames-time"] ]
            except ValueError :
                time_frames = [1.]
            
            vol = simps( pet.data, time_frames, axis=4)
        
        idx = reference.data > 0
        ref = np.mean(vol[idx])
        print "SUVR Reference = ", ref
        vol = vol / ref
        out.data=vol
        out.writeFile()
        out.closeVolume()


        return runtime

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



class loganROIOutput(TraitedSpec):
    result_file = File(argstr="%s", position=-1, desc="Logan Plot distribution volume (DVR) parametric image.")

class loganROIInput(MINCCommandInputSpec):
    result_file = File(argstr="%s", position=-1, desc="image to operate on")
    input_file = File(exists=True, position=-4, argstr="%s", desc="PET file")
    ttac_file = File(exists=True,  position=-5, argstr="%s", desc="Reference file")
    BPnd = traits.Bool(argstr="-BPnd", position=1, usedefault=True, default_value=True)
    C = traits.Bool(argstr="-C", position=2, usedefault=True, default_value=True)
    start_time=traits.Float(argstr="%s", position=-3, desc="Start time for regression in mtga.")
    k2=  traits.Float(argstr="-k2=%f", desc="With reference region input it may be necessary to specify also the population average for regerence region k2")
    end_time=traits.Float(argstr="%s", position=-2, desc="By default line is fit to the end of data. Use this option to enter the fit end time.")


class loganROI(MINCCommand):
    input_spec =  loganROIInput
    output_spec = loganROIOutput

    _cmd = "logan" #input_spec.pvc_method 
    _suffix = "_lp" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["result_file"] = self.inputs.result_file
        return outputs

    def _gen_filename(self, name):
        if name == "result_file":
            return self._list_outputs()["result_file"]
        return None

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix + fname_list[1]

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.result_file):
            self.inputs.result_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(loganROI, self)._parse_inputs(skip=skip)




class lpOutput(TraitedSpec):
    out_file = File(argstr="%s", position=-1, desc="Logan Plot distribution volume (DVR) parametric image.")

class lpInput(MINCCommandInputSpec):
    out_file = File(argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, position=-3, argstr="%s", desc="PET file")
    reference = File(exists=True,  position=-4, argstr="%s", desc="Reference file")
    start_time=traits.Float(argstr="%s", position=-2, desc="Start time for regression in mtga.")
    k2=  traits.Float(argstr="-k2=%f", desc="With reference region input it may be necessary to specify also the population average for regerence region k2")
    thr=traits.Float(argstr="-thr=%f", desc="Pixels with AUC less than (threshold/100 x max AUC) are set to zero. Default is 0%")
    Max=traits.Float(argstr="-max=%f",default=10000, use_default=True, desc="Upper limit for Vt or DVR values; by default max is set pixel-wise to 10 times the AUC ratio.")
    Min=traits.Float(argstr="-min=%f", desc="Lower limit for Vt or DVR values, 0 by default")
    Filter=traits.Bool(argstr="-filter",  desc="Remove parametric pixel values that over 4x higher than their closest neighbours.")
    end=traits.Float(argstr="-end %f", desc="By default line is fit to the end of data. Use this option to enter the fit end time.")
    v=traits.Str(argstr="-v %s", desc="Y-axis intercepts time -1 are written as an image to specified file.")
    n=traits.Str(argstr="-n %s", desc="Numbers of selected plot data points are written as an image.")


class lpCommand(MINCCommand):
    input_spec =  lpInput
    output_spec = lpOutput

    _cmd = "imgdv" #input_spec.pvc_method 
    _suffix = "_lp" 

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
        return super(lpCommand, self)._parse_inputs(skip=skip)

class ppOutput(TraitedSpec):
    out_file = File(argstr="-o %s",  desc="Patlak plot ki parametric image.")

class ppInput(MINCCommandInputSpec):
    out_file = File(argstr="%s", position=-1, desc="image to operate on")
    in_file= File(exists=True, position=-3, argstr="%s", desc="PET file")
    reference = File(exists=True,  position=-4, argstr="%s", desc="Reference file")
    start_time=traits.Float(argstr="%s", position=-2, desc="Start time for regression in mtga.")
    Ca=traits.Float(argstr="-Ca=%f", desc="Concentration of native substrate in arterial plasma (mM).")
    LC=traits.Float(argstr="-LC=%f", desc="Lumped constant in MR calculation; default is 1.0")
    density=traits.Float(argstr="-density %f", desc="Tissue density in MR calculation; default is 1.0 g/ml")
    thr=traits.Float(argstr="-thr=%f", desc="Pixels with AUC less than (threshold/100 x max AUC) are set to zero. Default is 0%")
    Max=traits.Float(argstr="-max=%f", default=10000, use_default=True,desc="Upper limit for Vt or DVR values; by default max is set pixel-wise to 10 times the AUC ratio.")
    #Min=traits.Float(argstr="-min %f", desc="Lower limit for Vt or DVR values, 0 by default")
    Filter=traits.Bool(argstr="-filter",  desc="Remove parametric pixel values that over 4x higher than their closest neighbours.")
    end=traits.Float(argstr="-end=%f", desc="By default line is fit to the end of data. Use this option to enter the fit end time.")
    v=traits.Str(argstr="-v %s", desc="Y-axis intercepts time -1 are written as an image to specified file.")
    n=traits.Str(argstr="-n %s", desc="Numbers of selected plot data points are written as an image.")


class ppCommand(MINCCommand):
    input_spec =  ppInput
    output_spec = ppOutput

    _cmd = "imgki" #input_spec.pvc_method 
    _suffix = "_pp" 

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
        return super(ppCommand, self)._parse_inputs(skip=skip)

class patlakOutput(TraitedSpec):
    out_file = File(argstr="-o %s",  desc="Patlak plot ki parametric image.")

class patlakInput(MINCCommandInputSpec):
    in_file= File(exists=True, position=-5, argstr="%s", desc="PET file")
    reference = File(exists=True,  position=-4, argstr="%s", desc="Reference file")
    start_time=traits.Float(argstr="%s", position=-3, desc="Start time for regression in mtga.")
    end=traits.Float(argstr="%s", position=-2, desc="By default line is fit to the end of data. Use this option to enter the fit end time.")
    out_file = File(argstr="%s", position=-1, desc="image to operate on")
    Ca=traits.Float(argstr="-Ca=%f", desc="Concentration of native substrate in arterial plasma (mM).")
    LC=traits.Float(argstr="-LC=%f", desc="Lumped constant in MR calculation; default is 1.0")
    density=traits.Float(argstr="-density %f", desc="Tissue density in MR calculation; default is 1.0 g/ml")
    thr=traits.Float(argstr="-thr=%f", desc="Pixels with AUC less than (threshold/100 x max AUC) are set to zero. Default is 0%")
    Max=traits.Float(argstr="-max=%f", default=10000, use_default=True,desc="Upper limit for Vt or DVR values; by default max is set pixel-wise to 10 times the AUC ratio.")
    #Min=traits.Float(argstr="-min %f", desc="Lower limit for Vt or DVR values, 0 by default")
    Filter=traits.Bool(argstr="-filter",  desc="Remove parametric pixel values that over 4x higher than their closest neighbours.")
    v=traits.Str(argstr="-v %s", desc="Y-axis intercepts time -1 are written as an image to specified file.")
    n=traits.Str(argstr="-n %s", desc="Numbers of selected plot data points are written as an image.")


class patlakCommand(MINCCommand):
    input_spec =  patlakInput
    output_spec = patlakOutput

    _cmd = "patlak" #input_spec.pvc_method 
    _suffix = "_pp" 

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
        return dname+ os.sep+fname_list[0] + _suffix + '.dft'

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.in_file, self._suffix)
        return super(patlakCommand, self)._parse_inputs(skip=skip)



class srtmOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Parametric image of binding potential.")
    out_file_t3map = File(argstr="-err=%s",desc="Theta3 image.")

class srtmInput(MINCCommandInputSpec):
    in_file= File(exists=True, position=-3, argstr="%s", desc="PET file")
    reference = File(exists=True,  position=-2, argstr="%s", desc="Reference file")
    out_file = File(argstr="%s", position=-1, desc="image to operate on")
    out_file_t3map = File(argstr="-err=%s", position=0, desc="Theta3 image.")
    t3max = traits.Float(argstr="-max=%f", position=1, desc="Maximum value for theta3.")
    t3min = traits.Float(argstr="-min=%f", position=2, desc="Minimum value for theta3.")
    nBF = traits.Int(argstr="-nr=%d", position=3, desc="Number of basis functions.")


class srtmCommand(MINCCommand):
    input_spec =  srtmInput
    output_spec = srtmOutput

    _cmd = "imgbfbp" #input_spec.pvc_method 
    _suffix = "_srtm" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        outputs["out_file_t3map"] = self.inputs.out_file_t3map
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        if name == "out_file_t3map":
            return self._list_outputs()["out_file_t3map"]
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
        if not isdefined(self.inputs.out_file_t3map):
            self.inputs.out_file_t3map = self._gen_output(self.inputs.in_file, "_t3err")
        return super(srtmCommand, self)._parse_inputs(skip=skip)





class srtmROIOutput(TraitedSpec):
    out_file = File(argstr="%s",  desc="Result file.")
    out_fit_file = File(argstr="%s",  desc="Fitting dft.")

class srtmROIInput(MINCCommandInputSpec):
    roi = File(exists=True,  position=-4, argstr="%s", desc="ROI file")
    reference = File(exists=True,  position=-3, argstr="%s", desc="Reference file")
    fit_time = traits.Int(position=-2, argstr="%d", usedefault=True, default_value=999, desc="Fit time")
    out_file = File(argstr="%s", position=-1, desc="Result file")
    out_fit_file = File(argstr="-fit=%s", position=2, desc="Fitting dft")
    sd = traits.Bool(argstr="-SD=y", position=1, usedefault=True, default_value=True, desc="Calculation of standard deviations")

class srtmROICommand(MINCCommand):
    input_spec =  srtmROIInput
    output_spec = srtmROIOutput

    _cmd = "fit_srtm" #input_spec.pvc_method 
    _suffix = "_srtmROI.res" 
    _suffix2 = "_srtmROI.fit" 

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        outputs["out_fit_file"] = self.inputs.out_fit_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        if name == "out_fit_file":
            return self._list_outputs()["out_fit_file"]
        return None

    def _gen_output(self, basefile, _suffix):
        fname = ntpath.basename(basefile)
        fname_list = os.path.splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] + _suffix

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_output(self.inputs.roi, self._suffix)
        if not isdefined(self.inputs.out_fit_file):
            self.inputs.out_fit_file = self._gen_output(self.inputs.roi, self._suffix2)
        return super(srtmROICommand, self)._parse_inputs(skip=skip)



standard_fields=["in_file", "header",  "reference", "mask", "like_file"] #NOTE: in_file and out_file must be defined in field
ecat_methods=["lp", "pp", "pp-roi", "srtm", "suv"]
tka_param={}
tka_param["lp"]=standard_fields
tka_param["pp"]=standard_fields
tka_param["pp-roi"]=standard_fields
tka_param["srtm"]=standard_fields
tka_param["suv"]=["in_file", "header"]
tka_param["suvr"]=["in_file", "header", "reference"]
reference_methods=["pp-roi","pp", "lp", "srtm", "suvr"]


def get_tka_workflow(name, opts):
    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=['sid']+tka_param[opts.tka_method]), name='inputnode')

    out_files = ["out_file"]
    outputnode = pe.Node(niu.IdentityInterface(fields=out_files), name='outputnode')
    
    pet_node=inputnode
    pet_file='in_file'
    if opts.tka_method in ecat_methods :
        #Define node to convert the input file from minc to ecat
        convertPET=pe.Node(minc2ecatCommand(), name='minc2ecat') #  minctoecatWorkflow("minctoecat_PET")
        #Connect input node to conversion
        workflow.connect(inputnode, 'in_file', convertPET, 'in_file')
        #workflow.connect(inputnode, 'like_file', convertPET, 'like_file')
        workflow.connect(inputnode, 'header', convertPET, 'header')
        pet_node=convertPET
        pet_file='out_file'

    #Define an empty node for reference region
    tacReference = pe.Node(niu.IdentityInterface(fields=["reference"]), name='tacReference')

    #Define empty node for output
    if opts.tka_method == 'srtm': out_files += ["out_file_t3map"]
    
    if not opts.arterial and opts.tka_method in ecat_methods:
        #Extracting TAC from reference region and putting it into text file
        #Convert reference mask from minc to ecat
        #convertReference=pe.Node(interface=minctoecatInterfaceCommand(), name="minctoecat_reference") 
        convertReference=pe.Node(interface=minc2ecatCommand(), name="minctoecat_reference") 
        #convertReference.inputs.out_file="tempREF.mnc"
        workflow.connect(inputnode, 'reference', convertReference, 'in_file')

        #Extract TAC from input image using reference mask
        extractReference=pe.Node(interface=img2dftCommand(), name="referencemask_extract")
        # convertReference --> extractRefernce 
        workflow.connect(convertReference, 'out_file', extractReference, 'mask_file')
        workflow.connect(pet_node, pet_file, extractReference, 'in_file')
        # extractReference --> tacReference
        workflow.connect(extractReference, 'out_file', tacReference, 'reference')
    elif opts.tka_method in reference_methods:
        #Using arterial input file (which must be provided by user). No conversion or extraction necessary
        # inputnode --> tacReference
        workflow.connect(inputnode, 'reference', tacReference, 'reference')

    if not 'roi' in opts.tka_method:
    #Do voxel-wise tracer kinetric analysis on 4D PET image to produce parametric ma
        if opts.tka_method in reference_methods: 
            if opts.tka_method == "lp":
                #Define node for logan plot analysis 
                tkaNode = pe.Node(interface=lpCommand(), name=opts.tka_method)
                if opts.tka_k2 != None: tkaNode.inputs.k2=opts.tka_k2
                if opts.tka_thr != None: tkaNode.inputs.thr=opts.tka_thr
                if opts.tka_max != None: tkaNode.inputs.Max=opts.tka_max
                if opts.tka_filter != None: tkaNode.inputs.Filter=opts.tka_filter
                if opts.tka_end != None: tkaNode.inputs.end=opts.tka_end
                if opts.tka_v != None: tkaNode.inputs.v=opts.tka_v
                if opts.tka_start_time != None:tkaNode.inputs.start_time=opts.tka_start_time
            elif opts.tka_method == "pp":
                #Define node for patlak-gjedde analysis
                tkaNode = pe.Node(interface=ppCommand(), name=opts.tka_method)
                if opts.tka_Ca != None: tkaNode.inputs.Ca=opts.tka_Ca
                if opts.tka_LC != None: tkaNode.inputs.LC=opts.tka_LC
                if opts.tka_density != None: tkaNode.inputs.density=opts.tka_density
                if opts.tka_thr != None: tkaNode.inputs.thr=opts.tka_thr
                if opts.tka_max != None: tkaNode.inputs.max=opts.tka_max
                if opts.tka_filter != None: tkaNode.inputs.filter=opts.tka_filter
                if opts.tka_end != None: tkaNode.inputs.end=opts.tka_end
                if opts.tka_v != None: tkaNode.inputs.v=opts.tka_v
                if opts.tka_n != None: tkaNode.inputs.n=opts.tka_n
                if opts.tka_start_time != None: tkaNode.inputs.start_time=opts.tka_start_time
            elif opts.tka_method == 'srtm':
                #Define node for srtm
                tkaNode = pe.Node(interface=srtmCommand(), name=opts.tka_method)
                if opts.tka_t3max != None: tkaNode.inputs.t3max=opts.tka_t3max
                if opts.tka_t3min != None: tkaNode.inputs.t3min=opts.tka_t3min
                if opts.tka_nBF != None: tkaNode.inputs.nBF=opts.tka_nBF
                convertParametricT3=pe.Node(ecat2mincCommand(), name="ecat2minc")
                workflow.connect(tkaNode, 'out_file_t3map', convertParametricT3, 'in_file')
                workflow.connect(inputnode, 'header', convertParametricT3, 'header')
                workflow.connect(convertParametricT3, 'out_file', outputnode, 'out_file_t3map')
            elif opts.tka_method == 'suvr':
                #Create a node for SUVR
                tkaNode = pe.Node(interface=suvrCommand(), name=opts.tka_method)
                workflow.connect(inputnode, 'header', tkaNode, 'header')
                workflow.connect(inputnode, 'in_file', tkaNode, 'pet_file')
                workflow.connect(inputnode, 'reference', tkaNode, 'reference')
                workflow.connect(tkaNode, 'out_file', outputnode, 'out_file')
                return(workflow)
            else : print "Warning: tka method ", opts.tka_method, "not found"

            workflow.connect(tacReference, 'reference', tkaNode, 'reference')
            workflow.connect(pet_node, pet_file, tkaNode, 'in_file')
            
            if opts.tka_method in ecat_methods :
                convertParametric=pe.Node(ecat2mincCommand(), name="ecat2minc") 
                workflow.connect(tkaNode, 'out_file', convertParametric, 'in_file')
                workflow.connect(inputnode, 'header', convertParametric, 'header')
                workflow.connect(inputnode, 'like_file', convertParametric, 'like_file')
                workflow.connect(convertParametric, 'out_file', outputnode, 'out_file')
            else : 
                workflow.connect(tkaNode, 'out_file', outputnode, 'out_file')
        elif opts.tka_method == 'suv':
            #Get Body Weight from header or .csv file
            body_weightNode=pe.Node(interface=subject_parameterCommand(), name="body_weight")
            body_weightNode.inputs.parameter_name=opts.body_weight
            workflow.connect(inputnode, 'header', body_weightNode, 'header')
            workflow.connect(inputnode, 'sid', body_weightNode, 'sid')
            #Get radiotracer dose from header or .csv file
            radiotracer_doseNode=pe.Node(interface=subject_parameterCommand(), name="radiotracer_dose")
            radiotracer_doseNode.inputs.parameter_name=opts.radiotracer_dose
            workflow.connect(inputnode, 'header', radiotracer_doseNode, 'header')
            workflow.connect(inputnode, 'sid', radiotracer_doseNode, 'sid')
            #Create a node for SUV
            tkaNode = pe.Node(interface=suvCommand(), name=opts.tka_method)
            tkaNode.inputs.start_time=opts.tka_start_time
            tkaNode.inputs.end_time=opts.tka_end_time
            workflow.connect(body_weightNode, 'parameter', tkaNode, 'body_weight')
            workflow.connect(radiotracer_doseNode, 'parameter', tkaNode, 'radiotracer_dose')
            workflow.connect(tkaNode, 'out_file', outputnode, 'out_file')
        #if opts.tka_method == 'srtm':
        #    convertParametricT3=pe.Node(ecat2mincCommand(), name="ecat2minc")
        #    workflow.connect(tkaNode, 'out_file_t3map', convertParametricT3, 'in_file')
        #    workflow.connect(inputnode, 'header', convertParametricT3, 'header')
        #    workflow.connect(convertParametricT3, 'out_file', outputnode, 'out_file_t3map')
    else: #ROI-based
        convertROI=pe.Node(interface=minc2ecatCommand(), name="minctoecat_roi")
        extractROI=pe.Node(interface=img2dftCommand(), name="roimask_extract")
        roi2img = pe.Node(interface= createImgFromROI(), name='img') 
        if opts.tka_method == 'srtm':
            outputnode=pe.Node(niu.IdentityInterface(fields=["out_file","out_fit_file"]), name='outputnode')
            tkaNode = pe.Node(interface=srtmROICommand(), name='srmtROI')
            workflow.connect(tkaNode, 'out_fit_file', outputnode, 'out_fit_file')
        elif opts.tka_method == 'pp-roi' :
            tacROI = pe.Node(niu.IdentityInterface(fields=["mask"]), name='tacROI')
            outputnode=pe.Node(niu.IdentityInterface(fields=["out_file"]), name='outputnode')
            tkaNode = pe.Node(interface=patlakCommand(), name='patlakROI')
            tkaNode.inputs.end=opts.tka_end_time
            tkaNode.inputs.start_time=opts.tka_start_time

        workflow.connect(inputnode, 'mask', convertROI, 'in_file')
        workflow.connect(convertROI, 'out_file', extractROI, 'mask_file')
        workflow.connect(convertPET, 'out_file', extractROI, 'in_file')
        workflow.connect(tacReference, 'reference', tkaNode, 'reference')
        workflow.connect(extractROI, 'out_file', tkaNode, 'in_file')
        workflow.connect(inputnode, 'mask', roi2img, 'like_file')
        workflow.connect(tkaNode, 'out_file', roi2img, 'in_file')
        workflow.connect(roi2img, 'out_file', outputnode, 'out_file')

    return(workflow)


