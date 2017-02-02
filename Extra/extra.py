import nipype.interfaces.io as nio
import nipype.interfaces.utility as niu
import nipype.algorithms.misc as misc
from nipype.interfaces.utility import Function
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix, copyfile)
from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec
from nipype.interfaces.minc.conversion import (ecattomincCommand, ecattomincWorkflow, minctoecatCommand, minctoecatWorkflow)
import ntpath
import pandas as pd
import os



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
	print(parameter_name)
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
			parameter=format(float('5e-06'), 'f')	
		except ValueError: pass
	self.inputs.parameter=str(parameter)

	print parameter
	return(runtime)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["parameter"] = self.inputs.parameter
        return outputs
	
