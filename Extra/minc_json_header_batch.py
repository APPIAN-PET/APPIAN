from glob import glob
from Extra.nii2mnc_batch import find
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
        BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
import os
from re import sub
from Extra.info import  mincinfoCommand
import json

def stdout_to_list( stdout ):
    time_list=[]
    temp_str=''
    for t in stdout : #var_dict["time"] :
        temp_str += t
        if '\n' in t :
            temp_str = sub('\n', '', temp_str)
            temp_str =float(temp_str)
            time_list += [temp_str]
            temp_str = '' 
    try :
        time_value = float(temp_str)
    except ValueError :
        time_value = temp_str
        
    time_list += [time_value]
    return time_list

class CreateHeaderOutput(TraitedSpec):
    output_file = traits.Str(desc="Ouput .json file")

class CreateHeaderInput(BaseInterfaceInputSpec):
    output_file = traits.Str(desc="Ouput .json file")
    input_file = traits.Str(desc="Input MINC file")

class CreateHeaderRunning(BaseInterface):
    input_spec = CreateHeaderInput
    output_spec = CreateHeaderOutput
    _suffix = '.json'

    def _run_interface(self, runtime):
        pet=self.inputs.input_file
        self.inputs.output_file = self._gen_output(self.inputs.input_file)
        exit_flag=False
        if not os.path.exists(pet) :
            print("Error: Could not find file $pet")
            exit(1)
        
        options=[
                ('acquisition','radionuclide', '-attvalue acquisition:radionuclide'),
                ('acquisition','radionuclide_halflife', '-attvalue acquisition:radionuclide_halflife'),
                ('time','units', '-attvalue time:units'),
                ('','time', '-varvalue time'),
                ('','time-width', '-varvalue time-width')]
        var_dict={}
        for key, var, opt in options:
            run_mincinfo=mincinfoCommand()
            run_mincinfo.inputs.in_file = self.inputs.input_file
            run_mincinfo.inputs.opt_string = opt
            run_mincinfo.inputs.error = 'unknown'
            run_mincinfo.terminal_output = 'file_split'
            r=run_mincinfo.run()
            if 'unknown' in r.runtime.stdout :
                key_string=key+':'+var
                if key == '' : key_string = var

                print("Error: could not find variable <"+key_string+'> in '+ self.inputs.input_file )
                exit_flag=True
            var_dict[var]=r.runtime.stdout

        out_dict={}
        out_dict["Info"]={"Isotope":var_dict['radionuclide'],"Halflife":var_dict['radionuclide_halflife']}
        out_dict["Time"]={"FrameTimes":{}}

        unit=sub('\n', '', var_dict["units"])
        out_dict["Time"]["FrameTimes"]["Units"]=[unit, unit]
        time_start  = stdout_to_list(var_dict['time'])
        time_width = stdout_to_list(var_dict['time-width'])
        time_list = []
       
        if len(time_start) != len(time_width) :
            print("Warning: Length of time list and time-widths list is not the same!")
        
        for i in range(len(time_start)):
            t0=time_start[i]
            t1=time_start[i] + time_width[i]
            time_list.append( [t0,t1] )
             
        out_dict["Time"]["FrameTimes"]["Values"]=time_list
        with open(self.inputs.output_file, 'w') as fp:
            json.dump(out_dict, fp)
        if exit_flag : 
            print("Error: Could not find requisite variables from MINC file "+self.inputs.input_file)
            exit(1)
        return runtime
   
    def _gen_output(self, input_file):
        split = os.path.splitext(input_file)
        return split[0] + self._suffix
    
    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.output_file):
            self.inputs.output_file = self._gen_output(self.inputs.input_file)
        
        outputs["output_file"]= self.inputs.output_file
        return outputs

def create_minc_headers(source_dir, clobber=False):
    pet_list = find(source_dir, "*_pet.mnc" )
   
    for pet in pet_list :
        out_fn=sub('.mnc','.json',pet)
        if not os.path.exists(out_fn) or clobber :
            create_json = CreateHeaderRunning()
            create_json.inputs.input_file = pet
            create_json.inputs.output_file = out_fn
            create_json.run()
    
    
