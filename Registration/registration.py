import os
import numpy as np
import tempfile
import shutil

from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile

from nipype.interfaces.minc.calc import CalcCommand
from nipype.interfaces.minc.smooth import SmoothCommand
from nipype.interfaces.minc.tracc import TraccCommand
from nipype.interfaces.minc.resample import ResampleCommand
from nipype.interfaces.minc.xfmOp import ConcatCommand
from nipype.interfaces.minc.xfmOp import InvertCommand




class PETtoT1LinRegOutput(TraitedSpec):
    out_file_xfm = File(exists=True, desc="transformation matrix")
    out_file_img = File(exists=True, desc="resampled image")

class PETtoT1LinRegInput(BaseInterfaceInputSpec):
    input_target_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="target image")
    input_source_file = File(position=1, argstr="%s", exists=True, mandatory=True, desc="source image")
    input_target_mask = File(position=2, argstr="-source_mask %s", exists=True, desc="target mask")
    input_source_mask = File(position=3, argstr="-target_mask %s", exists=True, desc="source mask")
    init_file_xfm = File(argstr="-init_xfm %s", exists=True, desc="initial transformation (default identity)")
    out_file_xfm = File(position=-2, argstr="%s", mandatory=True, desc="transformation matrix")
    out_file_img = File(position=-1, argstr="%s", mandatory=True, desc="resampled image")

    clobber = traits.Bool(position=-5, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(position=-4, argstr="-run", usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(position=-3, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETtoT1LinRegRunning(BaseInterface):
    input_spec = PETtoT1LinRegInput
    output_spec = PETtoT1LinRegOutput


    def _run_interface(self, runtime):
        tmpdir = tempfile.mkdtemp()

        prev_xfm = None
        if self.inputs.init_file_xfm:
            prev_xfm = self.inputs.init_file_xfm

        source = self.inputs.input_source_file
        target = self.inputs.input_target_file

        if self.inputs.input_source_mask and self.inputs.input_target_mask:
            if os.path.isfile(self.inputs.input_source_mask):
                source = tmpdir+"/s_base_masked.mnc"
                run_calc = CalcCommand();
                run_calc.inputs.input_file = [self.inputs.input_source_file, self.inputs.input_source_mask]
                run_calc.inputs.out_file = source
                # run_calc.inputs.expression='if(A[1]>0.5){out=A[0];}else{out=A[1];}'
                run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                if self.inputs.verbose:
                    print run_calc.cmdline
                if self.inputs.run:
                    run_calc.run()


            if os.path.isfile(self.inputs.input_target_mask):
                target = tmpdir+"/t_base_masked.mnc"
                run_calc.inputs.input_file = [self.inputs.input_target_file, self.inputs.input_target_mask]
                run_calc.inputs.out_file = target
                run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                if self.inputs.verbose:
                    print run_calc.cmdline
                if self.inputs.run:
                    run_calc.run()


        class conf:
            def __init__(self, type_, est, blur_fwhm_mri, blur_fwhm_pet, steps, tolerance, simplex):
                self.type_=type_
                self.est=est
                self.blur_fwhm_mri=blur_fwhm_mri
                self.blur_fwhm_pet=blur_fwhm_pet
                self.steps=steps
                self.tolerance=tolerance
                self.simplex=simplex

        conf1 = conf("blur", "-est_translations", 10, 6, "8 8 8", 0.01, 8)
        conf2 = conf("blur", "", 6, 6, "4 4 4", 0.004, 6)
        conf3 = conf("blur", "", 4, 4, "2 2 2", 0.002, 4)

        conf_list = [ conf1, conf2, conf3 ]

        i=1
        for confi in conf_list:
            tmp_source=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)
            tmp_source_blur_base=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)
            tmp_source_blur=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)+"_"+confi.type_+".mnc"
            tmp_target=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)
            tmp_target_blur_base=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)
            tmp_target_blur=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)+"_"+confi.type_+".mnc"
            tmp_xfm = tmpdir+"/t_base_conf"+str(i)+".xfm";
            tmp_rspl_vol = tmpdir+"/s_base_conf"+str(i)+".mnc";



            print '-------+------- iteration'+str(i)+' -------+-------\n'
            run_smooth = SmoothCommand();
            run_smooth.inputs.input_file=target
            run_smooth.inputs.fwhm=confi.blur_fwhm_mri
            run_smooth.inputs.output_file=tmp_target_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()

            run_smooth = SmoothCommand();
            run_smooth.inputs.input_file=source
            run_smooth.inputs.fwhm=confi.blur_fwhm_pet
            run_smooth.inputs.output_file=tmp_source_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()


            run_tracc = TraccCommand();
            run_tracc.inputs.input_source_file=tmp_source_blur
            run_tracc.inputs.input_target_file=tmp_target_blur
            run_tracc.inputs.out_file_xfm=tmp_xfm
            run_tracc.inputs.objective_func='mi'
            run_tracc.inputs.steps=confi.steps
            run_tracc.inputs.simplex=confi.simplex
            run_tracc.inputs.tolerance=confi.tolerance
            run_tracc.inputs.est=confi.est
            if prev_xfm:
                run_tracc.inputs.transformation=prev_xfm
            if self.inputs.input_source_mask:
                run_tracc.inputs.input_source_mask=self.inputs.input_source_mask
            if self.inputs.input_target_mask:
                run_tracc.inputs.input_target_mask=self.inputs.input_target_mask

            if self.inputs.verbose:
                print run_tracc.cmdline
            if self.inputs.run:
                run_tracc.run()

            

            run_resample = ResampleCommand();
            run_resample.inputs.input_file=source
            run_resample.inputs.out_file=tmp_rspl_vol
            run_resample.inputs.model_file=target
            run_resample.inputs.transformation=tmp_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

            prev_xfm = tmp_xfm
            i += 1

            print '\n'



        if self.inputs.init_file_xfm:
            run_concat = ConcatCommand();
            run_concat.inputs.in_file_xfm=self.inputs.init_xfm
            run_concat.inputs.in_file_xfm2=prev_xfm
            run_concat.inputs.out_file_xfm=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_concat.cmdline
            if self.inputs.run:
                run_concat.run()



        else:
            if self.inputs.verbose:
                cmd=' '.join(['cp', prev_xfm, self.inputs.out_file_xfm])
                print(cmd)
            if self.inputs.run:
                copyfile(prev_xfm, self.inputs.out_file_xfm)


        if self.inputs.out_file_img:
            print '\n-+- creating $outfile using $outxfm -+-\n'
            run_resample = ResampleCommand();
            run_resample.inputs.input_file=self.inputs.input_source_file
            run_resample.inputs.out_file=self.inputs.out_file_img
            run_resample.inputs.model_file=self.inputs.input_target_file
            run_resample.inputs.transformation=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file_xfm"] = self.inputs.out_file_xfm
        outputs["out_file_img"] = self.inputs.out_file_img






class T1toTalnLinRegOutput(TraitedSpec):
    out_file_xfm = File(exists=True, desc="transformation matrix")
    out_file_img = File(exists=True, desc="resampled image")

class T1toTalnLinRegInput(BaseInterfaceInputSpec):
    input_target_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="target image")
    input_source_file = File(position=1, argstr="%s", exists=True, mandatory=True, desc="source image")
    input_target_mask = File(position=2, argstr="-source_mask %s", exists=True, desc="target mask")
    input_source_mask = File(position=3, argstr="-target_mask %s", exists=True, desc="source mask")
    init_file_xfm = File(argstr="-init_xfm %s", exists=True, desc="initial transformation (default identity)")
    out_file_xfm = File(position=-2, argstr="%s", mandatory=True, desc="transformation matrix")
    out_file_img = File(position=-1, argstr="%s", mandatory=True, desc="resampled image")

    clobber = traits.Bool(position=-5, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(position=-4, argstr="-run", usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(position=-3, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class T1toTalnLinRegRunning(BaseInterface):
    input_spec = T1toTalnLinRegInput
    output_spec = T1toTalnLinRegOutput


    def _run_interface(self, runtime):
        tmpdir = tempfile.mkdtemp()

        prev_xfm = None
        if self.inputs.init_file_xfm:
            prev_xfm = self.inputs.init_file_xfm

        source = self.inputs.input_source_file
        target = self.inputs.input_target_file

        if self.inputs.input_source_mask and self.inputs.input_target_mask:
            if os.path.isfile(self.inputs.input_source_mask):
                source = tmpdir+"/s_base_masked.mnc"
                run_calc = CalcCommand();
                run_calc.inputs.input_file = [self.inputs.input_source_file, self.inputs.input_source_mask]
                run_calc.inputs.out_file = source
                # run_calc.inputs.expression='if(A[1]>0.5){out=A[0];}else{out=A[1];}'
                run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                if self.inputs.verbose:
                    print run_calc.cmdline
                if self.inputs.run:
                    run_calc.run()


            if os.path.isfile(self.inputs.input_target_mask):
                target = tmpdir+"/t_base_masked.mnc"
                run_calc.inputs.input_file = [self.inputs.input_target_file, self.inputs.input_target_mask]
                run_calc.inputs.out_file = target
                run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                if self.inputs.verbose:
                    print run_calc.cmdline
                if self.inputs.run:
                    run_calc.run()


        class tracc_args:
            def __init__(self, clobber, nonlinear, weight, stiffness, similarity, sub_lattice):
                # self.debug=debug
                self.clobber=clobber
                self.nonlinear=nonlinear
                self.weight=weight
                self.stiffness=stiffness
                self.similarity=similarity
                self.sub_lattice=sub_lattice

        class conf:
            def __init__(self, steps, blur_fwhm, iterations):
                self.steps=steps
                self.blur_fwhm=blur_fwhm
                self.iterations=iterations

        conf1 = conf(32,16,20)
        conf2 = conf(16,8,20)
        conf3 = conf(12,6,20)
        conf4 = conf(8,4,20)
        conf5 = conf(6,3,20)
        conf6 = conf(4,2,10)
        conf_list = [ conf1, conf2, conf3, conf4, conf5, conf6 ]

        nonlin_tracc_args = tracc_args(True,'corrcoeff',1.0,1,0.3,6)



        i=1
        for confi in conf_list:
            tmp_source=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)
            tmp_source_blur_base=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)
            tmp_source_blur=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)+"_"+confi.type_+".mnc"
            tmp_target=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)
            tmp_target_blur_base=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)
            tmp_target_blur=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)+"_"+confi.type_+".mnc"
            tmp_xfm = tmpdir+"/t_base_conf"+str(i)+".xfm";
            tmp_rspl_vol = tmpdir+"/s_base_conf"+str(i)+".mnc";



            print '-------+------- iteration'+str(i)+' -------+-------\n'
            run_smooth = SmoothCommand();
            run_smooth.inputs.input_file=target
            run_smooth.inputs.fwhm=confi.blur_fwhm_mri
            run_smooth.inputs.output_file=tmp_target_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()

            run_smooth = SmoothCommand();
            run_smooth.inputs.input_file=source
            run_smooth.inputs.fwhm=confi.blur_fwhm_pet
            run_smooth.inputs.output_file=tmp_source_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()


            run_tracc = TraccCommand();
            run_tracc.inputs.input_source_file=tmp_source_blur
            run_tracc.inputs.input_target_file=tmp_target_blur
            run_tracc.inputs.out_file_xfm=tmp_xfm
            run_tracc.inputs.objective_func='mi'
            run_tracc.inputs.steps=confi.steps
            run_tracc.inputs.simplex=confi.simplex
            run_tracc.inputs.tolerance=confi.tolerance
            if prev_xfm:
                run_tracc.inputs.transformation=prev_xfm
            if self.inputs.input_source_mask:
                run_tracc.inputs.input_source_mask=self.inputs.input_source_mask
            if self.inputs.input_target_mask:
                run_tracc.inputs.input_target_mask=self.inputs.input_target_mask

            if self.inputs.verbose:
                print run_tracc.cmdline
            if self.inputs.run:
                run_tracc.run()

            

            run_resample = ResampleCommand();
            run_resample.inputs.input_file=source
            run_resample.inputs.out_file=tmp_rspl_vol
            run_resample.inputs.model_file=target
            run_resample.inputs.transformation=tmp_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

            prev_xfm = tmp_xfm
            i += 1

            print '\n'



        if self.inputs.init_file_xfm:
            run_concat = ConcatCommand();
            run_concat.inputs.in_file_xfm=self.inputs.init_xfm
            run_concat.inputs.in_file_xfm2=prev_xfm
            run_concat.inputs.out_file_xfm=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_concat.cmdline
            if self.inputs.run:
                run_concat.run()



        else:
            if self.inputs.verbose:
                cmd=' '.join(['cp', prev_xfm, self.inputs.out_file_xfm])
                print(cmd)
            if self.inputs.run:
                copyfile(prev_xfm, self.inputs.out_file_xfm)


        if self.inputs.out_file_img:
            print '\n-+- creating $outfile using $outxfm -+-\n'
            run_resample = ResampleCommand();
            run_resample.inputs.input_file=self.inputs.input_source_file
            run_resample.inputs.out_file=self.inputs.out_file_img
            run_resample.inputs.model_file=self.inputs.input_target_file
            run_resample.inputs.transformation=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file_xfm"] = self.inputs.out_file_xfm
        outputs["out_file_img"] = self.inputs.out_file_img



