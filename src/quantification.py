from nipype.interfaces.utility import Function
from nipype.interfaces.base import TraitedSpec, File, traits, InputMultiPath, BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined
from nipype.utils.filemanip import load_json, save_json, split_filename, fname_presuffix, copyfile
from scipy.interpolate import interp1d
from scipy.integrate import simps
from src.utils import splitext
from scipy.stats import linregress
from scipy.linalg import solve
from scipy.optimize import minimize_scalar
import numpy.matlib as mat
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
import nibabel as nib
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import ntpath
import numpy as np
import os
import re
import importlib
import sys
import json
import pint

"""
.. module:: quant
    :platform: Unix
    :synopsis: Module to perform for PET quantification 

"""
### Quantification models 


def patlak_plot(vol,  int_vol, ref, int_ref, time_frames, opts={}, header=None ):
    n_frames = len(time_frames)
    start_time = opts["quant_start_time"]
    end_time = opts["quant_end_time"]
    dim = list(vol.shape)

    x = int_vol * (1./ vol)  
    x[np.isnan(x) | np.isinf(x) ] = 0.
    del int_ref

    y = ref * (1./ vol)
    y[np.isnan(y) | np.isinf(y) ] = 0.

    regr_start = np.sum(start_time > np.array(time_frames)) 
    regr_end = np.sum(end_time >= np.array(time_frames)) 
    x = x[:, regr_start:regr_end]
    y = y[:, regr_start:regr_end]
    del vol     
    del int_vol
    n_frames = regr_end - regr_start

    #ki = np.array(map(slope,x,y)) 

    ki = regr(x,y, dim[0], n_frames )
    return ki


def logan_plot(vol,  int_vol, ref, int_ref, time_frames, opts={}, header=None ):
    n_frames = len(time_frames)
    start_time = opts["quant_start_time"]
    end_time = opts["quant_end_time"]
    dim = list(vol.shape)

    x = int_ref * 1.0/vol #[brain_mask]    
    x[np.isnan(x) | np.isinf(x) ] = 0.

    y = int_vol * 1.0/ vol # [brain_mask]
    y[np.isnan(y) | np.isinf(y) ] = 0.


    regr_start = np.sum(start_time >= np.array(time_frames)) 
    regr_end = np.sum(end_time >= np.array(time_frames)) 
    print("Start frame (counting from 0):", regr_start)
    x = x[:, regr_start:regr_end]
    y = y[:, regr_start:regr_end]
    del vol     
    del int_vol
    n_frames = regr_end - regr_start

    dvr = regr(x,y, dim[0],n_frames )
    #dvr = np.array(list(map(slope,x,y))) 

    if opts["quant_DVR"] :
        out = dvr
    else :
        out = dvr - 1 #BPnd
    print(out)
    return out

def suv(vol,  int_vol, ref, int_ref, time_frames, opts={}, header=None ):
    start_time = opts["quant_start_time"]
    end_time = opts["quant_end_time"]
    start_frame = np.sum(start_time >= np.array(time_frames)) 
    end_frame = np.sum(end_time >= np.array(time_frames)) 

    num = simps( vol[:,start_frame:end_frame], time_frames[start_frame:end_frame], axis=1)
    bw=dose=0

    try :
        bw=float(header["Info"]["BodyWeight"])
    except KeyError :
        print("Error : body weight of subject not set in json header in entry [\"Info\"][\"BodyWeight\"]")
        exit(1)

    try :
        dose=float(header["Info"]["InjectedRadioactivity"])
    except :
        print("Error : injected dose for scan not set in json header in entry [\"Info\"][\"InjectedRadioactivity\"]")
        exit(1)

    return num / (dose/bw)

def suvr(vol,  int_vol, ref, int_ref, time_frames, opts={}, header=None ):

    start_time = opts["quant_start_time"]
    end_time = opts["quant_end_time"]


    end_time = opts["quant_end_time"]
    if end_time == None :
        end_time=time_frames[-1]

    start_frame = np.sum(start_time >= np.array(time_frames)) 
    end_frame = np.sum(end_time >= np.array(time_frames)) 
    print(start_time, end_time)
    print(start_frame, end_frame)

    num = simps( vol[:,start_frame:end_frame], time_frames[start_frame:end_frame], axis=1)
    den = simps( ref[:,start_frame:end_frame], time_frames[start_frame:end_frame], axis=1)
    print(num.shape, den.shape)
    return num / den

global half_life_dict
half_life_dict={"C11":20.364, "O15":61.12, "F18":109.771, "N13":9.97 }

def srtm(vol,  int_vol, ref, int_ref, time_frames, opts={}, header=None ):
    '''
    TODO: Add reference to author of code
    '''
    try :
        isotope=header["Info"]["Tracer"]["Isotope"][0]
        print(isotope)
        isotope=re.sub('-', '', isotope)
        print(isotope)
        half_life = half_life_dict[ isotope  ]
    except KeyError :
        half_life = opts.quant_half_life
        if half_life == None :
            print("Error : 1) isotope was either not found in .json header or not one of ",half_life_dict.keys()," was not specified manually with --half-life option.")
            exit(1)

    decayConstant = np.log(2) / half_life 
    time_widths = np.array(header["Time"]["FrameTimes"]["Duration"]).reshape(-1,) / 50.
    time_frames = np.array(time_frames).reshape(-1,) / 60.
    pet_sum = np.sum(vol,axis=0)
    weights = time_widths / (pet_sum * np.exp(decayConstant * time_frames))
    startActivity=0
    ref = ref.reshape(-1,)
    R1=BP=[]

    for k in range(vol.shape[0]):
        TAC = vol[k,:]
        W = mat.diag(weights)
        y = np.mat(TAC).T
        
        def energy_fun(theta3):
            exp_theta3_t = np.exp(np.asscalar(theta3)*time_frames)
            integrant = ref * exp_theta3_t
            conv=np.zeros_like(time_frames)
            for t in range(time_frames.shape[0])[1:]:
                conv[t] = simps(integrant[:t], time_frames[:t]) # km_integrate(integrant,time_frames, startActivity) / exp_theta3_t
            X = np.mat(np.column_stack((ref, conv)))
            thetas = solve(X.T * W * X, X.T * W * y)
            residual = y - X * thetas
            rss = residual.T * W * residual
            return rss

        res = minimize_scalar(energy_fun, bounds=(0.06, 0.6), method='bounded', options=dict(xatol=1e-1))
        theta3 = np.asscalar(res.x)

        exp_theta3_t = np.exp(theta3*time_frames)
        integrant = ref * exp_theta3_t
        conv = simps(integrant,time_frames) / exp_theta3_t
        X = np.mat(np.column_stack((ref, conv)))
        thetas = solve(X.T * W * X, X.T * W * y)

        R1 += thetas[0]
        k2 = thetas[1] + R1[-1]*theta3
        BP += [k2 / theta3 - 1]

    if opts["quant_R1"] :
        return R1

    return BP


global model_dict

model_dict={'pp':patlak_plot, 'lp':logan_plot,  'suv':suv, 'suvr':suvr, 'srtm':srtm }


def slope(x,y):
    return linregress(x,y)[0]
### Helper functions 

def create_tac_df(time_frames, pet_roi, int_roi, ref_tac, int_ref, df_fn, plot_fn) :
    df = {"Time":time_frames, "ref":ref_tac[0,:], "int_ref":int_ref[0,:]}
    df_tac = {"Time":time_frames, "ref":ref_tac[0,:]}
    df_int = {"Time":time_frames, "int_ref":int_ref[0,:]}

    for i in range(pet_roi.shape[0]) :
        df.update({"roi-"+str(i):pet_roi[i,:],"int_roi-"+str(i):pet_roi[i,:] })
        df_tac.update({"roi-"+str(i):pet_roi[i,:]})
        df_int.update({"int_roi-"+str(i):pet_roi[i,:]})

    df_tac = pd.DataFrame(df_tac)
    df_tac = pd.melt(df_tac,id_vars=['Time'])
    df_tac.columns = ['Time', 'TAC', 'Radio.Conc.']

    df_int = pd.DataFrame(df_int)
    df_int = pd.melt(df_int,id_vars=['Time'])
    df_int.columns = ['Time', 'TAC', 'Radio.Conc.']
    
    df = pd.DataFrame(df)
    df = pd.melt(df,id_vars=['Time'])
    df.columns = ['Time', 'TAC', 'Radio.Conc.']
    df.to_csv(df_fn)
    
    #Plotting
    plt.figure(dpi=150, figsize=(9, 9))
    sns.relplot(x="Time", y="Radio.Conc.", kind="line", hue="TAC", data=df_tac)

    plt.savefig(plot_fn)

def regr(x,y,tac_len, n_frames):
    x_mean = np.mean( x, axis=1)
    y_mean = np.mean( y, axis=1)
    x_mean = np.repeat(x_mean, n_frames).reshape( [tac_len]+[-1] )
    y_mean = np.repeat(y_mean, n_frames).reshape( [tac_len]+[-1] )
    #return (n_frames * np.sum(x*y,axis=1) - np.sum(x,axis=1)*np.sum(y,axis=1)) /  (n_frames * np.sum(x**2,axis=1) - np.sum(x,axis=1)**2)

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


def read_arterial_file(arterial_file, header) :
    ref_times = []
    ref_tac = []
    time_unit_conversion = 1.
    radio_unit_conversion = 1.
    
    ureg = pint.UnitRegistry()

    try :
        pet_radio_unit = header['Info']['Unit']
    except KeyError :
        print('Exit: Radioactivity units not set in PET json header in Info:Unit. Assuming same units for radioactivity cocnentrations in PET image and arterial input.')
        exit(1)

    with open(arterial_file, 'r') as f:
        for i, l in enumerate(f.readlines()) :
            split =lambda string : [ x for x in re.split('\t| |,', string) if x != '' ] 
            lsplit = split(l.rstrip('\n'))
            if len(lsplit) in [0,1] : continue

            if 'Time' in l or 'time' in l :
                time_unit_conversion = ureg.Quantity(1*lsplit[-1]).to('sec').magnitude
           
            if 'Activity' in l or 'activity' in l :
                radio_unit_conversion = ureg.Quantity(1*lsplit[-1]).to(pet_radio_unit).magnitude
                print('Conversion from', lsplit[-1], 'to', pet_radio_unit,':',radio_unit_conversion)

            try : 
                float(lsplit[0])
                if len(lsplit) != 3 :
                    print('Error: incorrectly formatted .dft file ', arterial_file) 
                    print('Expected format: <start time>\t<end time>\t<radioactivity concentration>\nbut got:', l)
                elif len(lsplit) == 3:
                    stime = float(lsplit[0])
                    etime = float(lsplit[1])
                    activity = float(lsplit[2])
                    ref_times += [ (stime + etime)/ 2.0 * time_unit_conversion ] 
                elif len(lsplit) == 2:
                    ref_times += [ float(lsplit[0]) * time_unit_conversion ] 
                    activity = float(lsplit[1])
                print(activity, activity * radio_unit_conversion )
                ref_tac += [ activity * radio_unit_conversion ]
            except ValueError : continue
    return np.array(ref_times), np.array(ref_tac)

def get_reference(pet_vol, brain_mask_vol, ref_file, time_frames, header,  arterial_file=None):
    ref_tac = np.zeros([1,len(time_frames)])
    ref_times = time_frames
    time_frames = np.array(time_frames)
    
    if isdefined(arterial_file) and arterial_file != None : 
        '''read arterial input file'''
        ref_times, ref_tac = read_arterial_file(arterial_file, header)
        ref_tac = ref_tac.reshape(1,-1)

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

    return  ref_tac, ref_times

def get_roi_tac(roi_file,pet_vol,brain_mask_vol, time_frames ):
    roi_img = nib.load(roi_file)
    roi_vol = roi_img.get_data()
    roi_vol = roi_vol.reshape(roi_vol.shape[0:3])
    roi_vol = roi_vol.reshape(-1,)
    roi_vol = roi_vol[brain_mask_vol]

    unique_roi = np.unique(roi_vol)[1:]
    roi_tac = np.zeros( (len(unique_roi), len(time_frames)) )
    for t in range(len(time_frames)) :
        for i, roi in enumerate(unique_roi):
            frame = pet_vol[:,t]
            roi_tac[i][t] = np.mean(frame[roi_vol == roi])
    del pet_vol
    return roi_tac


def create_output_array(dims,  roi_based, quant_vol, roi_file, brain_mask_vol ):
    roi_img = nib.load(roi_file)
    roi_vol = roi_img.get_data().reshape(-1,)
    n3d=np.product(dims[0:3]) 
    n_frames=dims[3]
    unique_roi=np.unique(roi_vol)[1:]

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
    out_df = File(desc="Reconstruced 3D image based on .dft ROI values")
    out_plot = File(desc="Reconstruced 3D image based on .dft ROI values")

class ApplyModelInput(TraitedSpec):
    out_file = File(desc="Reconstruced 3D image based on .dft ROI values")
    out_df = File(desc="Reconstruced 3D image based on .dft ROI values")
    out_plot = File(desc="Reconstruced 3D image based on .dft ROI values")
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
        #Setup input file variables
        pet_file = self.inputs.pet_file
        ref_file = self.inputs.reference_file
        header_file = self.inputs.header_file
        arterial_file = self.inputs.arterial_file
        brain_mask_file = self.inputs.brain_mask_file
        roi_file = self.inputs.roi_file
        opts = self.inputs.opts
        #setup output file variables
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()

        if not isdefined(self.inputs.out_df):
            self.inputs.out_df = os.getcwd() + os.sep + self.inputs.quant_method+"_tac.csv" 

        if not isdefined(self.inputs.out_plot):
            self.inputs.out_plot = os.getcwd() + os.sep + self.inputs.quant_method+"_tac.png" 

        pet_img = nib.load(pet_file)
        pet_vol = pet_img.get_data().astype('f4')
        dims = pet_vol.shape
        n3d=np.product(pet_vol.shape[0:3])
        pet_vol = pet_vol.reshape([n3d]+[pet_vol.shape[3]])

        brain_mask_img = nib.load(brain_mask_file)
        brain_mask_vol = brain_mask_img.get_data().astype(bool)
        brain_mask_vol = brain_mask_vol.reshape(-1,)
        pet_vol = pet_vol[ brain_mask_vol, :  ]

        model = model_dict[self.inputs.quant_method]
        header = json.load(open(header_file, "r") )
        time_frames = np.array([ (float(s) + float(e)) / 2. for s,e in  header['Time']["FrameTimes"]["Values"] ])
        n_frames=len(time_frames)

    

        #Calculate average TAC in Ref
        ref_tac, ref_times = get_reference(pet_vol, brain_mask_vol, ref_file, time_frames, header,arterial_file)

        #Calculate average TAC in ROI
        pet_roi = get_roi_tac(roi_file, pet_vol, brain_mask_vol, time_frames )
        
        int_roi = integrate_tac(pet_roi, time_frames)
        int_vol = integrate_tac(pet_vol, time_frames)
        int_ref = integrate_tac(ref_tac, ref_times)

        #Set start and end times
        if opts['quant_start_time'] == None or opts['quant_start_time'] < ref_times[0] :
            print('Warning: Changing quantification start time to ', ref_times[0])
            opts['quant_start_time'] = ref_times[0]
        if opts['quant_end_time'] == None or  opts['quant_start_time'] > ref_times[1] :
            print('Warning: Changing quantification end time to ', ref_times[-1])
            opts['quant_end_time'] = ref_times[-1]

        modified_time_frames = time_frames[ (time_frames >= min(ref_times)) & (time_frames <= max(ref_times)) ] 
        f = interp1d(ref_times, ref_tac[0], kind='cubic', fill_value="extrapolate")
        fint = interp1d(ref_times, int_ref[0], kind='cubic', fill_value="extrapolate")
        ref_tac = f(time_frames).reshape(1,-1)
        int_ref = fint(time_frames).reshape(1,-1)

        create_tac_df(time_frames, pet_roi, int_roi, ref_tac, int_ref, self.inputs.out_df, self.inputs.out_plot)
        quant_vol = model(pet_vol, int_vol, ref_tac, int_ref, time_frames, opts=opts, header=header)

        out_ar = create_output_array(dims, self.inputs.roi_based, quant_vol, roi_file, brain_mask_vol )

        nib.Nifti1Image(out_ar, pet_img.affine).to_filename(self.inputs.out_file)

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_output()
        if not isdefined(self.inputs.out_df)  :
            self.inputs.out_df = os.getcwd() + os.sep + self.inputs.quant_method+"_tac.csv" 
        if not isdefined(self.inputs.out_df)  :
            self.inputs.out_df = os.getcwd() + os.sep + self.inputs.quant_method+"_tac.png" 

        outputs["out_file"] = self.inputs.out_file
        outputs["out_df"] = self.inputs.out_df
        outputs["out_plot"] = self.inputs.out_plot
        return outputs

    def _gen_output(self):
        fname = ntpath.basename(self.inputs.pet_file)
        fname_list = splitext(fname) # [0]= base filename; [1] =extension
        dname = os.getcwd() 
        kind='vxl'
        if self.inputs.roi_based == True :
            kind = 'roi'
        return dname+ os.sep+fname_list[0] +'_quant-'+kind+'-'+ self.inputs.quant_method +'.nii.gz'


