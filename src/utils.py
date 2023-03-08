import os 
import re
import gzip
import shutil
import gzip
import subprocess
import src.ants_nibabel as nib
import ntpath
import pandas as pd
import numpy as np 
import tempfile
import src.ants_nibabel as nib
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, CommandLine, CommandLineInputSpec,
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)

def nib_load_3d(fn):
    img = nib.load(fn)
    vol = img.get_data()
    vol = vol.reshape(vol.shape[0:3])
    img_3d = nib.Nifti1Image(vol, img.affine)
    return img_3d

def cmd(command):
    try:
        output = subprocess.check_output(command,stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        exit(1)
    else:
        print("Output: \n{}\n".format(output))


def splitext(s):
    try :
        ssplit = os.path.basename(s).split('.')
        ext='.'+'.'.join(ssplit[1:])
        basepath= re.sub(ext,'',s)
        return [basepath, ext]
    except TypeError :  
        return s


def gz(ii, oo):
    with open(ii, 'rb') as in_file:
        with gzip.open(oo, 'wb') as out_file:
            shutil.copyfileobj(in_file, out_file)

def gunzip(ii, oo):
    with gzip.open(ii, 'rb') as in_file:
        with open(oo, 'wb') as out_file:
            shutil.copyfileobj(in_file, out_file)

def check_gz(in_file_fn) :
    img, ext = splitext(in_file_fn)
    if '.gz' in ext :
        out_file_fn = tempfile.mkdtemp() + os.path.basename(img) + '.nii'
        sif = img + '.sif'
        if os.path.exists(sif) : 
            shutil.copy(sif, '/tmp/'+os.path.basename(img)+'.sif'  )
        gunzip(in_file_fn, out_file_fn) 
        return out_file_fn
    else :
        return in_file_fn

class separate_mask_labelsOutput(TraitedSpec):
    out_file=traits.File(argstr="%s", desc="4D label image")

class separate_mask_labelsInput(TraitedSpec):
    in_file=traits.File(argstr="%s", desc="3D label image")
    out_file=traits.File(argstr="%s", desc="4D label image")

class separate_mask_labelsCommand(BaseInterface ):
    input_spec = separate_mask_labelsInput  
    output_spec = separate_mask_labelsOutput

    def _run_interface(self, runtime):
        vol = nib.load(self.inputs.in_file)
        data = vol.get_data()
        data = data.reshape(*data.shape[0:3])
        

        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_outputs(self.inputs.in_file)

        unique = np.unique( data ).astype(int)

        nUnique = len(unique)-1

        out = np.zeros( [data.shape[0], data.shape[1], data.shape[2], nUnique] )
        print('unique', unique)
        print('shape',out.shape)
        print('data', data.shape)

        for t,i in enumerate( unique ) :
            if i != 0 :
                print(t-1, i )
                out[ data == i, t-1 ] = 1 

        out_file=nib.Nifti1Image(out, vol.get_affine())
        out_file.to_filename(self.inputs.out_file)
        return(runtime)

    def _gen_outputs(self, fn) :
        fn_split = splitext(fn)
        return os.getcwd() + os.sep +  os.path.basename( fn_split[0] ) + "_4d" + fn_split[1]

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_outputs(self.inputs.in_file)

        outputs["out_file"] = self.inputs.out_file
        return outputs

class concat_dfOutput(TraitedSpec):
    out_file = traits.File(desc="Output file")

class concat_dfInput(BaseInterfaceInputSpec):
    in_list = traits.List(mandatory=True, exists=True, desc="Input list")
    out_file = traits.File(mandatory=True, desc="Output file")
    test = traits.Bool(default=False, usedefault=True, desc="Flag for if df is part of test run of pipeline")


class concat_df(BaseInterface):
    input_spec =  concat_dfInput 
    output_spec = concat_dfOutput 

    def _run_interface(self, runtime):
        df=pd.DataFrame([])
        test = self.inputs.test
        print('in_list:', self.inputs.in_list)
        for f in self.inputs.in_list:
            dft = pd.read_csv(f)
            df = pd.concat([df, dft], axis=0)
        #if test : print df
        df.to_csv(self.inputs.out_file, index=False)
        print('\tWriting', self.inputs.out_file)
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.getcwd() + os.sep + self.inputs.out_file
        return outputs

class ConcatOutput(TraitedSpec):
    out_file = File(exists=True, desc="resampled image")

class ConcatInput(CommandLineInputSpec):
    in_file = InputMultiPath(File(mandatory=True), position=0, argstr='%s', desc='List of input images.')
    out_file = File(position=1, argstr="%s", mandatory=True, desc="Output image.")

    dimension = traits.Str(argstr="-concat_dimension %s", desc="Concatenate along a given dimension.")
    start = traits.Float(argstr="-start %s", desc="Starting coordinate for new dimension.")
    step = traits.Float(argstr="-step %s", desc="Step size for new dimension.")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class copyOutput(TraitedSpec):
    output_file=traits.File(argstr="%s", desc="input")

class copyInput(TraitedSpec):
    input_file=traits.File(argstr="%s", desc="input")
    output_file=traits.File(argstr="%s", desc="output")

class copyCommand(BaseInterface ):
    input_spec = copyInput  
    output_spec = copyOutput

    def _run_interface(self, runtime):
        if not isdefined(self.inputs.output_file) :
            self.inputs.output_file = self._gen_output(self.inputs.input_file)
            shutil.copy(self.inputs.input_file, self.inputs.output_file)
        return(runtime)

    def _gen_output(self, fn) :
        return os.getcwd() + os.sep +  os.path.basename( fn ) 

    def _list_outputs(self):
        outputs = self.output_spec().get()

        if not isdefined(self.inputs.output_file) :
            self.inputs.output_file = self._gen_output(self.inputs.input_file)

        outputs["output_file"] = self.inputs.output_file
        return outputs


#In theory, this information should be contained in the header.
# Often, however, the information will either not be present in the header or it will be saved under an unexpected variable name (e.g., "Patient_Weight", "body_weight", "weight" ).
# One way around this problem is to allow the user to create a .csv file with the subject
#name and the parameter of interest. This way, if the paramter cannot be read from the header, it can still be read from the text file.
class subject_parameterOutput(TraitedSpec):
    parameter=traits.String(argstr="%s", desc="Subject parameter")

class subject_parameterInput(TraitedSpec):
    parameter_name=traits.String(argstr="%s", desc="File containing subject parameters")
    header = traits.Dict(desc="Python dictionary containing PET header")
    parameter=traits.String(argstr="%s", desc="Subject parameter")
    sid=traits.String(desc="Subject ID")

class subject_parameterCommand(BaseInterface ):
    input_spec = subject_parameterInput  
    output_spec = subject_parameterOutput

    def _run_interface(self, runtime):
        parameter_name = self.inputs.parameter_name
        header = self.inputs.header
        sid = self.inputs.sid
        if  os.path.exists(parameter_name):
            #Case 1: paramter_name is a file name containing the subjects and parameters
            #	--> attempt to extract parameter from header
            df=pd.read_csv(parameter_name, header=None)
            parameter=df.iloc[:, 1][ df.iloc[:,0] == sid ].values[0]

        #Case 2: parameter_name is a string representing the name of the parameter
        else:
            parameter=_finditem(header, parameter_name)
            if type(parameter) == list: 
                parameter=parameter[0]
                #convert scientific notation number to floating point number, stored as string
                try: 
                    parameter=format(float(parameter), 'f')	
                except ValueError: pass
        self.inputs.parameter=str(parameter)
        return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["parameter"] = self.inputs.parameter
        return outputs

