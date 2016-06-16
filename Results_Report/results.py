import os

from nipype.interfaces.minc.base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)

class groupstatsInput(MINCCommandInputSpec):   
    image    = traits.File(argstr="-i %s", mandatory=True, desc="Image")  
    vol_roi  = traits.File(argstr="-v %s", desc="Volumetric image containing ROI")  
    surf_roi = traits.File(argstr="-s %s %s", desc="obj and txt files containing surface ROI")

    out_file = traits.File(argstr="-o %s", desc="Output csv file")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class groupstatsOutput(TraitedSpec):
    out_file = File(desc="Extract values from PET images based on ROI")

class groupstatsCommand(MINCCommand, Info):
    _cmd = "mincgroupstats"
    input_spec = groupstatsInput
    output_spec = groupstatsOutput
    _suffix='results'
    
    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = os.getcwd() + os.sep + "results.csv" #fname_presuffix(self.inputs.image, suffix=self._suffix)


        return super(groupstatsCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs

    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None
