import os
import numpy as np

from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)
from Extra.minc_filemanip import  update_minchd_json
import pickle





class mincinfoOutput(TraitedSpec):
    output = traits.Str(desc='Mincinfo ouput')

class mincinfoInput(CommandLineInputSpec):
    in_file = File(position=-1, argstr="%s", exists=True, mandatory=True, desc="image to operate on")
    output = traits.Str(desc="Mincinfo output")

    error = traits.Str(argstr="-error %s", position=1, desc="math operations to perform")
    opt_string = traits.Str(argstr="%s", position=2, mandatory=True, desc="Option defining the infos to print out")
      
class mincinfoCommand(CommandLine):
    _cmd="mincinfo"
    input_spec = mincinfoInput
    output_spec = mincinfoOutput

 



class InfoOutput(TraitedSpec):
    out_file = traits.Any(desc='Infos ouput')

class InfoInput(CommandLineInputSpec):
    in_file = File(position=-1, argstr="%s", exists=True, mandatory=True, desc="image to operate on")
    out_file = File(desc="Output Json file")

    opt_string = traits.Str(argstr="%s", mandatory=True, desc="Option defining the infos to print out")
    json_var = traits.Str(mandatory=True, desc="Define the variable name")
    json_attr = traits.Str(mandatory=True, desc="Define the attribute name")
    json_type = traits.Str(mandatory=True, desc="Define the attribute type")
    error = traits.Str(argstr="-error %s", desc="math operations to perform")
      
class InfoCommand(CommandLine):
    _cmd = "mincinfo"
    _suffix = ".info"
    input_spec = InfoInput
    output_spec = InfoOutput


    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        # if not isdefined(self.inputs.out_file):
        #     self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
        if not isdefined(self.inputs.out_file):
            fname, ext = os.path.splitext(self.inputs.in_file)
            self.inputs.out_file = fname + self._suffix

        return super(InfoCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()

        if runtime is None:
            try:
                out_info = load_json(self.inputs.out_file)[self.inputs.json_attr][self.inputs.json_var]
            except IOError:
                return self.run().outputs
        else:
            out_info = []
            for line in runtime.stdout.split('\n'):
                if line:
                    values = line.split()
		
                    if self.inputs.json_type == 'float':
                        if len(values) > 1:
                            #out_info.append([float(val) for val in values])
                            out_info.append([val for val in values])
                        else:
                            #out_info.extend([float(val) for val in values])
                            out_info.extend([val for val in values])

                    elif self.inputs.json_type == 'integer':
                        if len(values) > 1:
                            #out_info.append([int(val) for val in values])
                            out_info.append([val for val in values])
                        else:
                            #out_info.extend([int(val) for val in values])
                            out_info.extend([val for val in values])

                    else:
                        if len(values) > 1:
                            out_info.append([val for val in values])
                        else:
                            out_info.extend([val for val in values])

            if len(out_info) == 1:
                out_info = out_info[0]
            if os.path.exists(self.inputs.out_file):
                update_minchd_json(self.inputs.out_file, out_info, self.inputs.json_var, self.inputs.json_attr)
            else:
                save_json(self.inputs.out_file, dict(((self.inputs.json_var,dict(((self.inputs.json_attr,out_info),))),)))
        
        outputs.out_file = out_info
        return outputs


class StatsOutput(TraitedSpec):
    out_file = traits.Any(desc='Infos ouput')

class StatsInput(CommandLineInputSpec):
    in_file = File(position=-1, argstr="%s", exists=True, mandatory=True, desc="image to operate on")
    out_file = File(desc="Output Json file")

    opt_string = traits.Str(argstr="%s", mandatory=True, desc="Option defining the infos to print out")
    quiet = traits.Bool(argstr="-quiet", usedefault=True, default_value=True, desc="Overwrite output file")
      
class StatsCommand(CommandLine):
    _cmd = "mincstats"
    input_spec = StatsInput
    output_spec = StatsOutput

'''
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        # if not isdefined(self.inputs.out_file):
        #     self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
        if not isdefined(self.inputs.out_file):
            fname, ext = os.path.splitext(self.inputs.in_file)
            self.inputs.out_file = fname + self._suffix

        return super(StatsCommand, self)._parse_inputs(skip=skip)
    
    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()
        outfile = os.path.join(os.getcwd(), 'stat_result.pck')
        # outfile = os.path.join(os.getcwd(), 'stat_result.json')

        if runtime is None:
            try:
                out_stats = load_json(self.inputs.out_file)
            except IOError:
                return self.run().outputs
        else:
            out_stats = []
            for line in runtime.stdout.split('\n'):
                if line:
                    values = line.split()
        
                    if len(values) > 1:
                        out_stats.append([float(val) for val in values])
                    else:
                        out_stats.extend([float(val) for val in values])

            if len(out_stats) == 1:
                out_stats = out_stats[0]

            file = open(outfile, 'w')
            pickle.dump(out_stats, file)
            file.close()

            # save_json(outfile,out_stats)
        
        outputs.out_file = out_stats
        return outputs
        '''
