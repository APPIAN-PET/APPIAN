import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)






class InfoOutput(TraitedSpec):
    out_info = traits.Any(desc='Infos ouput')

class InfoInput(MINCCommandInputSpec):

    input_file = File(position=2, argstr="%s", exists=True, mandatory=True, desc="image to operate on")

    op_string = traits.Str(argstr="%s", mandatory=True, desc="String defining the infos to print out")
    error = traits.Str(argstr="-error %s", desc="math operations to perform")
      
class InfoCommand(MINCCommand):
    _cmd = "mincinfo"
    _suffix = ".info"
    input_spec = InfoInput
    output_spec = InfoOutput
    

    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()

        outfile = os.path.join(os.getcwd(), 'stat_result.json')
        fname, ext = os.path.splitext(self.inputs.input_file)
        # self.inputs.out_file_xfm = self._gen_fname(fname, suffix=self._suffix)
        self.inputs.out_file_xfm = fname + self._suffix


        if runtime is None:
            try:
                out_stat = load_json(outfile)['stat']
            except IOError:
                return self.run().outputs
        else:
            out_stat = []
            for line in runtime.stdout.split('\n'):
                if line:
                    values = line.split()
                    if len(values) > 1:
                        out_stat.append([float(val) for val in values])
                    else:
                        out_stat.extend([float(val) for val in values])
            if len(out_stat) == 1:
                out_stat = out_stat[0]
            save_json(outfile, dict(stat=out_stat))
        outputs.out_stat = out_stat
        return outputs

