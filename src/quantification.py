from nipype.interfaces.utility import Function
from nipype.interfaces.base import TraitedSpec, File, traits, InputMultiPath, BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined
from nipype.utils.filemanip import load_json, save_json, split_filename, fname_presuffix, copyfile
from scipy.interpolate import interp1d
from scipy.integrate import simps
from src.turku import img2dft_unit_conversion
from src.utils import subject_parameterCommand
from src.turku import imgunitCommand
from src.turku import JsonToSifCommand
from src.ants import APPIANApplyTransforms
from src.utils import splitext
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
import nibabel as nib
import ntpath
import numpy as np
import os
import re
import importlib
import sys
import json

### Quantification models 


def patlak_plot(vol,  int_vol, ref, int_ref, time_frames, opts={}):
    n_frames = len(time_frames)
    start_time = opts["quant_start_time"]
    dim = list(vol.shape)
    
    x = int_vol * (1./ vol)  
    x[np.isnan(x) | np.isinf(x) ] = 0.
    del int_ref

    y = ref * (1./ vol)
    y[np.isnan(y) | np.isinf(y) ] = 0.

    regr_start = np.sum(start_time > np.array(time_frames)) 
    x = x[:, regr_start:n_frames]
    y = y[:, regr_start:n_frames]
    del vol     
    del int_vol
    n_frames -= regr_start

    ki = regr(x,y,dim[0],n_frames)

    return ki


def logan_plot(vol,  int_vol, ref, int_ref, time_frames, opts={} ):
    n_frames = len(time_frames)
    start_time = opts["quant_start_time"]
    dim = list(vol.shape)

    x = int_ref * 1.0/vol #[brain_mask]    
    x[np.isnan(x) | np.isinf(x) ] = 0.
    del int_ref

    y = int_vol * 1.0/ vol # [brain_mask]
    y[np.isnan(y) | np.isinf(y) ] = 0.

    regr_start = np.sum(start_time > np.array(time_frames)) 
    x = x[:, regr_start:n_frames]
    y = y[:, regr_start:n_frames]
    del vol     
    del int_vol
    n_frames -= regr_start

    dvr = regr(x,y,dim[0],n_frames)

    return dvr

def suv(vol, brain_mask, int_vol, int_ref, time_frames, opts):
    pass

def suvr(vol, brain_mask, int_vol, int_ref, time_frames, opts):
    pass

global model_dict
model_dict={'pp':patlak_plot, 'lp':logan_plot,  'suv':suv, 'suvr':suvr}


### Helper functions 

def regr(x,y,tac_len, n_frames):
    x_mean = np.mean( x, axis=1)
    y_mean = np.mean( y, axis=1)
    x_mean = np.repeat(x_mean, n_frames).reshape( [tac_len]+[-1] )
    y_mean = np.repeat(y_mean, n_frames).reshape( [tac_len]+[-1] )

    xx = x - x_mean 
    del x
    del x_mean
    yy = y - y_mean
    del y_mean
    del y

    return np.sum(xx*yy, axis=1) / np.sum( xx**2, axis=1 )

def integrate_tac(vol, time_frames):
    int_vol = np.zeros(vol.shape).astype('f4')
    for t in range(1,len(time_frames)) :
        integrated = simps( vol[:,0:t], time_frames[0:t], axis=1)
        int_vol[:,t] = integrated

    return int_vol

def read_arterial_file(arterial_file) :
    ref_times = []
    ref_tac = []
    with open(arterial_file, 'r') as f:
        for i, l in enumerate(f.readlines()) :
            if i >= 4 :
                lsplit = l.split(' ')
                stime = float(lsplit[0])
                etime = float(lsplit[1])
                
                activity = float(lsplit[2])
                ref_times += [ (stime + etime) / 2. ]
                ref_tac += [ activity ]
                
    return ref_times, ref_tac
    
def get_reference(pet_vol, brain_mask_vol, ref_file, time_frames, arterial_file=None):
    ref_tac = np.zeros([1,len(time_frames)])
    ref_times = np.zeros(len(time_frames))
    
    if isdefined(arterial_file) and arterial_file != None : 
        '''read arterial input file'''
        art_times, art_tac = read_arterial_file(arterial_file)
        vol_times = np.array([ (t[0]+t[1]) / 2.0 for f in time_frames ])
        f = interp1d(art_times, art_tac, kind='cubic')
        ref_tac = f(vol_times)

    elif isdefined(ref_file) and  ref_file != None :
        ref_img = nib.load(ref_file)
        ref_vol = ref_img.get_data()
        ref_vol = ref_vol.reshape(np.product(ref_vol.shape), -1) 
        ref_vol = ref_vol[brain_mask_vol]
        for t in range(len(time_frames)) :
            frame = pet_vol[:,t]
            frame = frame.reshape( list(frame.shape)+[1] )
            ref_tac[0,t] = np.mean(frame[ ref_vol != 0 ])
    else :
        print('Error: no arterial file or reference volume file')
        exit(1)
    
    return  ref_tac

def get_roi_tac(roi_file,pet_vol ):
    roi_img = nib.load(roi_file)
    roi_vol = roi_img.get_data()
    roi_vol = roi_vol.reshape(-1,)
    unique_roi = np.unique(roi_vol)[1:]
    roi_tac = np.zeros( (len(unique_roi), len(time_frames)) )
    for t in range(len(time_frames)) :
        for i, roi in enumerate(unique_roi):
            frame = pet_vol[:,t]
            roi_tac[i][t] = np.mean(frame[roi_vol == roi])
    del pet_vol
    return roi_tac, unique_roi, roi_vol


def create_output_array(dims,  roi_based, quant_vol, roi_vol, brain_mask_vol ):
    n3d=np.product(dims[0:3]) 
    n_frames=dims[3]
    unique_roi=np.unique(roi_vol)
    
    ar = np.zeros([n3d] )
    
    if  roi_based == True :
        for t in range(n_frames) :
            for label, value in enumerate(unique_roi) : 
                ar[ roi_vol == value ] = quant_vol[label]
    else : 
        ar[ brain_mask_vol ] = quant_vol
    ar = ar.reshape(dims[0:3])
    return ar

### Class Node for doing quantification

class ApplyModelOutput(TraitedSpec):  
    out_file = File(desc="Reconstruced 3D image based on .dft ROI values")

class ApplyModelInput(TraitedSpec):
    out_file = File(desc="Reconstruced 3D image based on .dft ROI values")
    pet_file = File(exists=True, mandatory=True, desc=" .dft ROI values")
    header_file = File(exists=True, mandatory=True, desc=" .dft ROI values")
    brain_mask_file = File( desc=" .dft ROI values") #,default_value=None, usedefault=True)
    reference_file = File(mandatory=True, desc=" .dft ROI values") #, usedefault=True, default_value=None)
    roi_file = File( desc=" .dft ROI values") #, usedefault=True, default_value=None)
    arterial_file = File( desc=" .dft ROI values")
    quant_method = traits.Str(mandatory=True)
    roi_based = traits.Bool(mandatory=False)
    opts = traits.Dict(mandatory=True)


class ApplyModel(BaseInterface) :
    input_spec = ApplyModelInput
    output_spec = ApplyModelOutput

    def _run_interface(self, runtime) :
        pet_file = self.inputs.pet_file
        ref_file = self.inputs.reference_file
        header_file = self.inputs.header_file
        arterial_file = self.inputs.arterial_file
        brain_mask_file = self.inputs.brain_mask_file
        roi_file = self.inputs.roi_file
        opts = self.inputs.opts
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()

        pet_img = nib.load(pet_file)
        pet_vol = pet_img.get_data().astype('f4')
        dims = pet_vol.shape
        n3d=np.product(pet_vol.shape[0:3])
        pet_vol = pet_vol.reshape([n3d]+[pet_vol.shape[3]])
       
        brain_mask_img = nib.load(brain_mask_file)
        brain_mask_vol = brain_mask_img.get_data().astype(bool).reshape(-1,)
        
        pet_vol = pet_vol[ brain_mask_vol, :  ]
        
        model = model_dict[self.inputs.quant_method]
        header = json.load(open(header_file, "r") )
        time_frames = [ (float(s) + float(e)) / 2. for s,e in  header['Time']["FrameTimes"]["Values"] ]
        n_frames=len(time_frames)
        
        ref_tac = get_reference(pet_vol, brain_mask_vol, ref_file, time_frames, arterial_file)

        roi_vol=unique_roi=None
        if  self.inputs.roi_based == True :
            pet_vol, unique_roi, roi_vol = get_roi_tac(roi_file, pet_vol )
        
        int_vol = integrate_tac(pet_vol, time_frames)
        int_ref = integrate_tac(ref_tac, time_frames)

        quant_vol = model(pet_vol, int_vol, ref_tac, int_ref, time_frames, opts=opts)

        out_ar = create_output_array(dims, self.inputs.roi_based, quant_vol, roi_vol, brain_mask_vol )

        print(self.inputs.out_file)
        nib.Nifti1Image(out_ar, pet_img.affine).to_filename(self.inputs.out_file)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_output(self):
        fname = ntpath.basename(self.inputs.pet_file)
        fname_list = splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        return dname+ os.sep+fname_list[0] +'_quant-'+ self.inputs.quant_method +'.nii.gz'

"""
.. module:: quant
    :platform: Unix
    :synopsis: Module to perform for PET quantification 
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""
''' 


    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["stereo","tfm_mri_stx", "tfm_pet_mri", "like_file", "in_file", "header",  "reference", "mask"] ), name='inputnode')

    out_files = ["out_file", "out_file_stereo"]
    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=out_files), name='outputnode')

    ### src module
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+"/quant_methods/" )
    quant_module_fn="quant_method_"+opts.quant_method #+".py"

    #quant_module = importlib.import_module(quant_module_fn)
    try :
        quant_module = importlib.import_module(quant_module_fn)
    except ImportError :
        print("Error: Could not find source file",quant_module_fn,"corresponding to quantification method:",opts.quant_method)
        exit(1)

    quantNodeName=opts.quant_method
    
    if opts.pvc_label_name != None :
        quantNodeName += "_"+opts.pvc_label_name
    if opts.quant_label_name != None :
        quantNodeName += "_"+opts.quant_label_name

    try :
        quantNode = pe.Node(interface=quant_module.QuantCommandWrapper(), name=quantNodeName)
    except AttributeError :
        quantNode = pe.Node(interface=quant_module.quantCommand(), name=quantNodeName)

    quantNode = quant_module.check_options(quantNode, opts)
 
    #If the quantification node takes a header input, then pass it from inputnode
    try : 
        quantNode.inputs.header
        workflow.connect(inputnode, 'header', quantNode, 'header')
    except AttributeError :
        pass
    ### Setup output from quantification function
    if quant_module.out_file_format == "NIFTI"  :
        quant_source = quantNode
    elif quant_module.out_file_format == "DFT"  :
        #Create 3/4D volume based on ROI values
        roi2img = pe.Node(interface=createImgFromROI(), name='img') 
        workflow.connect(inputnode, 'mask', roi2img, 'like_file')
        workflow.connect(quantNode, 'out_file', roi2img, 'in_file')
        quant_source = roi2img
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
        workflow.connect(pet_source, pet_file, quantNode, 'in_file')
    else : 
        extractROI=pe.Node(interface=img2dft_unit_conversion(), name="roimask_extract")
        workflow.connect(inputnode, 'mask', extractROI, 'mask_file')
        workflow.connect(inputnode, 'header', extractROI, 'pet_header_json')
        workflow.connect(pet_source, pet_file, extractROI, 'in_file')
        workflow.connect(extractROI, 'out_file', quantNode, 'in_file')

    turku_methods = [ 'lp', 'lp-roi', 'pp', 'pp-roi', 'srtm', 'srtm-roi' ]
    #If the src method is from the Turku PET Centre tools, need to create .sif
    if opts.quant_method in turku_methods:
        JsonToSifNode = pe.Node( JsonToSifCommand(), 'sif'  )
        workflow.connect(pet_source, pet_file, JsonToSifNode, 'pet')
        workflow.connect(inputnode, 'header', JsonToSifNode, 'pet_header_json')
        workflow.connect(JsonToSifNode, 'out_file', quantNode, 'sif' )

    workflow.connect(quant_source, 'out_file', outputnode, 'out_file')
   
    if opts.quant_to_stereo and not opts.analysis_space == "stereo" :
        quant_to_stereo = pe.Node( APPIANApplyTransforms(), name="quant_stereo"  )
        workflow.connect(inputnode, 'tfm_mri_stx', quant_to_stereo, "transform_2")
        if opts.analysis_space=='pet' :
            workflow.connect(inputnode, 'tfm_pet_mri', quant_to_stereo, "transform_3")
        workflow.connect(inputnode, 'stereo', quant_to_stereo, "reference_image")
        workflow.connect(quant_source, 'out_file', quant_to_stereo, "input_image")
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
            if quant_module.in_file_format == "NIFTI" and opts.quant_method in turku_methods :
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
        
        workflow.connect(tacReference, 'reference', quantNode, 'reference')


    return(workflow)
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
        
        out = nib.Nifti1Image(out_data, ref.get_affine(), ref.header)
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

    '''

