import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from Extra.utils import splitext
import nibabel as nib
import ntpath
import pandas as pd
import os
import shutil
import numpy as np 


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



def _finditem(obj, key):
#Recursively search for item associated with key in hierarchy of embedded dictionaries
    if key in obj: return obj[key]
    for k, v in obj.items():
        if isinstance(v,dict):
            item = _finditem(v, key)
            if item is not None:
                return item

#It is often necessary to know some specific parameter about the subject (e.g., body weight in SUV. 
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

        if not isdefined(self.inputs.out_file) :
            self.inputs.out_file = self._gen_outputs(self.inputs.in_file)
        
        unique = np.unique( data )

        nUnique = len(unique)-1

        out = np.zeros( [data.shape[0], data.shape[1], data.shape[2], nUnique] )

        for t,i in enumerate( unique ) :
            if i != 0 :
                print(t, i )
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
	
