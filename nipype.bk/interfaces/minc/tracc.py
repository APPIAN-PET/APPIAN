import os
import numpy as np

from base import MINCCommand, MINCCommandInputSpec, Info
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from ...utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)



 
class TraccInput(MINCCommandInputSpec):
    in_source_file = File(position=0, argstr="%s", mandatory=True, desc="source volume")
    in_target_file = File(position=1, argstr="%s", mandatory=True, desc="target volume")
    out_file_xfm = traits.Str(position=2, argstr="%s", exists=True, mandatory=True, desc="transformation matrix")

    in_source_mask = File(position=3, argstr="-source_mask %s", exists=True, desc="Binary source mask file")
    in_target_mask = File(position=4, argstr="-model_mask %s", exists=True, desc="Binary target mask file")

    identity = traits.Bool(argstr="-identity", desc="Use identity transformation for starting point")
    transformation = File(argstr="-transformation %s", desc="Initial world transformation")
    _objest = ["", "-est_center", "-est_scales", "-est_translations"]
    est = traits.Enum(*_objest, argstr="%s", desc="Estimation from Principal axis trans")
    _objfuncNlin = ["xcorr", "diff", "sqdiff", "label", "chamfer", "corrcoeff", "opticalflow"]
    nonlinear = traits.Enum(*_objfuncNlin, argstr="-nonlinear %s", desc="Recover nonlinear deformation field")
    _objfunc = ["xcorr", "zscore", "ssc", "vr", "mi", "nmi"]
    objective_func = traits.Enum(*_objfunc, argstr="-%s", desc="Linear optimization objective functions")
    _transfParam = ["lsq7", "lsq3", "lsq6", "lsq9", "lsq10", "lsq12"]
    lsq = traits.Enum(*_transfParam, argstr="-%s", desc="N parameters transformation")

    steps = traits.Str(argstr="-step %s", default_value='4 4 4', desc="Step size along each dimension (X, Y, Z)")
    sub_lattice = traits.Int(argstr="-sub_lattice %d", default_value=5, desc="Number of nodes along diameter of local sub-lattice")
    lattice = traits.Str(argstr="-lattice_diameter %s", default_value='24 24 24', desc="Widths of sub-lattice along each dimension (X, Y, Z)")
    tolerance = traits.Float(argstr="-tol %.3f", default_value=0.005, desc="Stopping criteria tolerance")
    simplex = traits.Int(argstr="-simplex %d", default_value=20, desc="Radius of simplex volume")
    iterations = traits.Int(argstr="-iterations %d", default_value=4, desc="Number of iterations for non-linear optimization")
    weight = traits.Float(argstr="-weight %.1f", default_value=0.6, desc="Weighting factor for each iteration in nl optimization")
    stiffness = traits.Float(argstr="-stiffness %.1f", default_value=0.005, desc="Weighting factor for smoothing between nl iterations")
    similarity = traits.Float(argstr="-similarity %.1f", default_value=0.5, desc="Weighting factor for  r=similarity*w + cost(1*w)")
    
    # clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    # verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class TraccOutput(TraitedSpec):
    out_file_xfm = File(exists=True, desc="transformation matrix")

class TraccCommand(MINCCommand, Info):
    _cmd = "minctracc"
    _suffix = '_minctracc'
    input_spec = TraccInput
    output_spec = TraccOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file_xfm):
            self.inputs.out_file_xfm = self._gen_fname(self.inputs.in_source_file, suffix=self._suffix)

        return super(TraccCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file_xfm"] = self.inputs.out_file_xfm
        return outputs

