import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from ...utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)



 
class TraccInput(MINCCommandInputSpec):
    # input_source_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="source volume")
    input_source_file = File(position=0, argstr="%s", mandatory=True, desc="source volume")
    # input_target_file = File(position=1, argstr="%s", exists=True, mandatory=True, desc="target volume")
    input_target_file = File(position=1, argstr="%s", mandatory=True, desc="target volume")
    out_file_xfm = traits.Str(position=2, argstr="%s", exists=True, mandatory=True, desc="transformation matrix")

    input_source_mask = File(position=3, argstr="-source_mask %s", exists=True, desc="Binary source mask file")
    input_target_mask = File(position=4, argstr="-model_mask %s", exists=True, desc="Binary target mask file")

    # transformation = File(position=5, argstr="-transformation %s", exists=True, desc="Initial world transformation")
    transformation = File(argstr="-transformation %s", desc="Initial world transformation")
    _objfunc = ["xcorr", "zscore", "ssc", "vr", "mi", "nmi"]
    objective_func = traits.Enum(*_objfunc, mandatory=True, argstr="-%s", usedefault=True, desc="Linear optimization objective functions")
    step = traits.Str(position=-6, argstr="-step %s", usedefault=True, default_value='4 4 4', desc="Step size along each dimension (X, Y, Z)")
    simplex = traits.Int(position=-5, argstr="-simplex %d", usedefault=True, default_value=20, desc="Radius of simplex volume")
    tolerance = traits.Float(position=-4, argstr="-tol %.3f", usedefault=True, default_value=0.005, desc="Stopping criteria tolerance")
    _objest = ["", "-est_center", "-est_scales", "-est_translations"]
    est = traits.Enum(*_objest, argstr="%s", desc="Estimation from Principal axis trans")
    
    # verbose = traits.Bool(position=-2, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")
    clobber = traits.Bool(position=-1, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")

class TraccOutput(TraitedSpec):
    out_file_xfm = File(exists=True, desc="transformation matrix")

class TraccCommand(MINCCommand, Info):
    _cmd = "minctracc"
    _suffix = "_minctracc"
    input_spec = TraccInput
    output_spec = TraccOutput

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file_xfm"] = self.inputs.out_file_xfm

        # if not isdefined(self.inputs.out_file_xfm):
        #     outputs["out_file_xfm"] = self._gen_fname(self.inputs.input_file, suffix=self._suffix)
        outputs["out_file_xfm"] = os.path.abspath(outputs["out_file_xfm"])
        return outputs

    def _gen_filename(self, name):
        if name == "output_file":
            return self._list_outputs()["output_file"]
        return None
