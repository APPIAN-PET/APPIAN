import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from ...utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)






class InfoOutput(TraitedSpec):
    out_info = traits.Any(desc='Infos ouput')

class InfoInput(MINCCommandInputSpec):
    input_file = File(position=-1, argstr="%s", exists=True, mandatory=True, desc="image to operate on")


    atttype = traits.Str(argstr="-atttype %s", mandatory=True, desc="Attribute type to print out")
    attvalue = traits.Str(argstr="%s", mandatory=True, desc="Attribute type to print out")
    opt_string = traits.Str(argstr="%s", mandatory=True, desc="Option defining the infos to print out")
    json_attr = traits.Str(mandatory=True, desc="Define the attribute name")
    json_type = traits.Str(mandatory=True, desc="Define the attribute type")
    
    error = traits.Str(argstr="-error %s", desc="math operations to perform")
      
class InfoCommand(MINCCommand):
    _cmd = "mincinfo"
    _suffix = ".info"
    input_spec = InfoInput
    output_spec = InfoOutput
    

    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()
        fname, ext = os.path.splitext(self.inputs.input_file)
        # outfile = os.path.join(self._gen_fname(fname, suffix=self._suffix))
        outfile = fname + self._suffix

        if runtime is None:
            try:
                out_info = load_json(outfile)[self.inputs.json_attr]
            except IOError:
                return self.run().outputs
        else:
            out_info = []
            for line in runtime.stdout.split('\n'):
                if line:
                    values = line.split()
                    if self.inputs.json_type == 'float':
                        if len(values) > 1:
                            out_info.append([float(val) for val in values])
                        else:
                            out_info.extend([float(val) for val in values])

                    elif self.inputs.json_type == 'integer':
                        if len(values) > 1:
                            out_info.append([float(val) for val in values])
                        else:
                            out_info.extend([float(val) for val in values])

                    else:
                        if len(values) > 1:
                            out_info.append([val for val in values])
                        else:
                            out_info.extend([val for val in values])


            if len(out_info) == 1:
                out_info = out_info[0]
            # save_json(outfile, dict(self.inputs.json_attr=out_info))
            name = self.inputs.json_attr;
            save_json(outfile, dict(((name,out_info),)))
        outputs.out_info = out_info
        return outputs

