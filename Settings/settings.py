import os
import numpy as np
import tempfile
import shutil
import pyezminc
import minc
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import (load_json, save_json, update_minchd_json, split_filename, fname_presuffix)
from nipype.interfaces.minc.info import InfoCommand



class PETinfoOutput(TraitedSpec):
    output_file = File(desc="Output file")

class PETinfoInput(BaseInterfaceInputSpec):
    input_file = File(exists=True, mandatory=True, desc="Native dynamic PET image")
    output_file = File(desc="Output file")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETinfoRunning(BaseInterface):
    input_spec = PETinfoInput
    output_spec = PETinfoOutput
    
    # def _parse_inputs(self, skip=None):
    #     if skip is None:
    #         skip = []
    #     if not isdefined(self.inputs.output_file):
    #         fname, ext = os.path.splitext(self.inputs.input_file)
    #         self.inputs.output_file = fname + _suffix

    #     return super(PETinfoRunning, self)._parse_inputs(skip=skip)


    def _run_interface(self, runtime):

        _suffix = ".info"

        if not isdefined(self.inputs.output_file):
            fname, ext = os.path.splitext(self.inputs.input_file)
            self.inputs.output_file = fname + _suffix


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
            run_mincinfo.inputs.input_file = self.inputs.input_file
            run_mincinfo.inputs.output_file = self.inputs.output_file
            run_mincinfo.inputs.opt_string = opt.command
            run_mincinfo.inputs.json_var = opt.variable
            run_mincinfo.inputs.json_attr = opt.attribute
            run_mincinfo.inputs.json_type = opt.type_
            run_mincinfo.inputs.error = 'unknown'

            if self.inputs.verbose:
                print run_mincinfo.cmdline
            if self.inputs.run:
                run_mincinfo.run()


        img = minc.Image(self.inputs.input_file, metadata_only=True)
        hd = img.get_MINC_header()
        for key in hd.keys():
            for subkey in hd[key].keys():
                data_in = hd[key][subkey]
                var = str(key)
                attr = str(subkey)
                update_minchd_json(self.inputs.output_file, data_in, var, attr)

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_file"] = self.inputs.output_file
        return outputs
