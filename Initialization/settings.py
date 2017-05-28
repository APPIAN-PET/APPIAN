import os
import numpy as np
import tempfile
import shutil
import nipype.interfaces.minc as minc
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)
from nipype.utils.minc_filemanip import update_minchd_json
from nipype.interfaces.minc.info import InfoCommand



class PETinfoOutput(TraitedSpec):
    out_file = File(desc="Output file")

class PETinfoInput(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="Native dynamic PET image")
    out_file = File(desc="Output file")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETinfoRunning(BaseInterface):
    input_spec = PETinfoInput
    output_spec = PETinfoOutput
    _suffix = ".info"
   
    # def _parse_inputs(self, skip=None):
    #     if skip is None:
    #         skip = []
    #     if not isdefined(self.inputs.out_file):
    #         fname, ext = os.path.splitext(self.inputs.in_file)
    #         self.inputs.out_file = fname + _suffix

    #     return super(PETinfoRunning, self)._parse_inputs(skip=skip)


    def _run_interface(self, runtime):

        if not isdefined(self.inputs.out_file):
            fname, ext = os.path.splitext(self.inputs.in_file)
            self.inputs.out_file = fname + self._suffix

        # if os.path.exists(self.inputs.out_file):
        #     os.remove(self.inputs.out_file)
        try:
            os.remove(self.inputs.out_file)
        except OSError:
            pass

        class InfoOptions:
            def __init__(self, command, variable, attribute, type_):
                self.command = command
                self.variable = variable
                self.attribute = attribute
                self.type_ = type_

        options = [ InfoOptions('-dimnames','time','dimnames','string'),
                    InfoOptions('-varvalue time','time','frames-time','integer'),
                    InfoOptions('-varvalue time-width','time','frames-length','integer') ]

        for opt in options:
            run_mincinfo=InfoCommand()
            run_mincinfo.inputs.in_file = self.inputs.in_file
            run_mincinfo.inputs.out_file = self.inputs.out_file
            run_mincinfo.inputs.opt_string = opt.command
            run_mincinfo.inputs.json_var = opt.variable
            run_mincinfo.inputs.json_attr = opt.attribute
            run_mincinfo.inputs.json_type = opt.type_
            run_mincinfo.inputs.error = 'unknown'

            if self.inputs.verbose:
                print run_mincinfo.cmdline
            if self.inputs.run:
                run_mincinfo.run()


        img = minc.Image(self.inputs.in_file, metadata_only=True)
        hd = img.get_MINC_header()
        for key in hd.keys():
            for subkey in hd[key].keys():
                data_in = hd[key][subkey]
                var = str(key)
                attr = str(subkey)
                print key, subkey, var, attr
                update_minchd_json(self.inputs.out_file, data_in, var, attr)

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs
