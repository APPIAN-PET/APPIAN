import os
import numpy as np
import tempfile
import shutil

from os.path import basename

from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile

from nipype.interfaces.minc.calc import CalcCommand
from nipype.interfaces.minc.smooth import SmoothCommand
from nipype.interfaces.minc.tracc import TraccCommand
from nipype.interfaces.minc.resample import ResampleCommand
from nipype.interfaces.minc.xfmOp import ConcatCommand
from nipype.interfaces.minc.xfmOp import InvertCommand
from nipype.interfaces.minc.inormalize import InormalizeCommand




class PETtoT1LinRegOutput(TraitedSpec):
    out_file_xfm = File(desc="transformation matrix")
    out_file_img = File(desc="resampled image")

class PETtoT1LinRegInput(BaseInterfaceInputSpec):
    in_target_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="target image")
    in_source_file = File(position=1, argstr="%s", exists=True, mandatory=True, desc="source image")
    in_target_mask = File(position=2, argstr="-source_mask %s", exists=True, desc="target mask")
    in_source_mask = File(position=3, argstr="-target_mask %s", exists=True, desc="source mask")
    init_file_xfm = File(argstr="-init_xfm %s", exists=True, desc="initial transformation (default identity)")
    out_file_xfm = File(position=-2, argstr="%s", desc="transformation matrix")
    out_file_img = File(position=-1, argstr="%s", desc="resampled image")

    clobber = traits.Bool(position=-5, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(position=-4, argstr="-run", usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(position=-3, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETtoT1LinRegRunning(BaseInterface):
    input_spec = PETtoT1LinRegInput
    output_spec = PETtoT1LinRegOutput
    _suffix = "_LinReg"


    def _run_interface(self, runtime):
        tmpDir = tempfile.mkdtemp()


        source = self.inputs.in_source_file
        target = self.inputs.in_target_file
        s_base = basename(os.path.splitext(source)[0])
        t_base = basename(os.path.splitext(target)[0])
        if not isdefined(self.inputs.out_file_xfm):
            self.inputs.out_file_xfm = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'.xfm', use_ext=False)
        if not isdefined(self.inputs.out_file_img):
            self.inputs.out_file_img = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'.mnc', use_ext=False)
            # self.inputs.out_file_img = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+Info.ftypes['MINC'], use_ext=False)


        prev_xfm = None
        if self.inputs.init_file_xfm:
            prev_xfm = self.inputs.init_file_xfm

        source = self.inputs.in_source_file
        target = self.inputs.in_target_file
        s_base = basename(os.path.splitext(source)[0])
        t_base = basename(os.path.splitext(target)[0])

        if self.inputs.in_source_mask and self.inputs.in_target_mask:
            if os.path.isfile(self.inputs.in_source_mask):
                source = tmpDir+"/"+s_base+"_masked.mnc"
                run_calc = CalcCommand();
                run_calc.inputs.in_file = [self.inputs.in_source_file, self.inputs.in_source_mask]
                run_calc.inputs.out_file = source
                # run_calc.inputs.expression='if(A[1]>0.5){out=A[0];}else{out=A[1];}'
                run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                if self.inputs.verbose:
                    print run_calc.cmdline
                if self.inputs.run:
                    run_calc.run()


            if os.path.isfile(self.inputs.in_target_mask):
                target = tmpDir+"/"+t_base+"_masked.mnc"
                run_calc.inputs.in_file = [self.inputs.in_target_file, self.inputs.in_target_mask]
                run_calc.inputs.out_file = target
                run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                if self.inputs.verbose:
                    print run_calc.cmdline
                if self.inputs.run:
                    run_calc.run()


        class conf:
            def __init__(self, type_, est, blur_fwhm_source, blur_fwhm_target, steps, tolerance, simplex):
                self.type_=type_
                self.est=est
                self.blur_fwhm_source=blur_fwhm_source
                self.blur_fwhm_target=blur_fwhm_target
                self.steps=steps
                self.tolerance=tolerance
                self.simplex=simplex

        conf1 = conf("blur", "-est_translations", 10, 6, "8 8 8", 0.01, 8)
        conf2 = conf("blur", "", 6, 6, "4 4 4", 0.004, 6)
        conf3 = conf("blur", "", 4, 4, "2 2 2", 0.002, 4)

        conf_list = [ conf1, conf2, conf3 ]

        i=1
        for confi in conf_list:
            tmp_source=tmpDir+"/"+s_base+"_fwhm"+str(confi.blur_fwhm_source)
            tmp_source_blur_base=tmpDir+"/"+s_base+"_fwhm"+str(confi.blur_fwhm_source)
            tmp_source_blur=tmpDir+"/"+s_base+"_fwhm"+str(confi.blur_fwhm_source)+"_"+confi.type_+".mnc"
            tmp_target=tmpDir+"/"+t_base+"_fwhm"+str(confi.blur_fwhm_target)
            tmp_target_blur_base=tmpDir+"/"+t_base+"_fwhm"+str(confi.blur_fwhm_target)
            tmp_target_blur=tmpDir+"/"+t_base+"_fwhm"+str(confi.blur_fwhm_target)+"_"+confi.type_+".mnc"
            tmp_xfm = tmpDir+"/"+t_base+"_conf"+str(i)+".xfm";
            tmp_rspl_vol = tmpDir+"/"+s_base+"_conf"+str(i)+".mnc";



            print '-------+------- iteration'+str(i)+' -------+-------\n'
            run_smooth = SmoothCommand();
            run_smooth.inputs.in_file=target
            run_smooth.inputs.fwhm=confi.blur_fwhm_target
            run_smooth.inputs.out_file=tmp_target_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()

            run_smooth = SmoothCommand();
            run_smooth.inputs.in_file=source
            run_smooth.inputs.fwhm=confi.blur_fwhm_source
            run_smooth.inputs.out_file=tmp_source_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()


            run_tracc = TraccCommand();
            run_tracc.inputs.in_source_file=tmp_source_blur
            run_tracc.inputs.in_target_file=tmp_target_blur
            run_tracc.inputs.out_file_xfm=tmp_xfm
            run_tracc.inputs.objective_func='mi'
            run_tracc.inputs.steps=confi.steps
            run_tracc.inputs.simplex=confi.simplex
            run_tracc.inputs.tolerance=confi.tolerance
            run_tracc.inputs.est=confi.est
            if prev_xfm:
                run_tracc.inputs.transformation=prev_xfm
            if self.inputs.in_source_mask:
                run_tracc.inputs.in_source_mask=self.inputs.in_source_mask
            if self.inputs.in_target_mask:
                run_tracc.inputs.in_target_mask=self.inputs.in_target_mask

            if self.inputs.verbose:
                print run_tracc.cmdline
            if self.inputs.run:
                run_tracc.run()

            

            run_resample = ResampleCommand();
            run_resample.inputs.in_file=source
            run_resample.inputs.out_file=tmp_rspl_vol
            run_resample.inputs.model_file=target
            run_resample.inputs.transformation=tmp_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

            # prev_xfm = tmp_xfm
            i += 1

            print '\n'



        if self.inputs.init_file_xfm:
            run_concat = ConcatCommand();
            run_concat.inputs.in_file=self.inputs.init_xfm
            run_concat.inputs.in_file_2=tmp_xfm
            run_concat.inputs.out_file_xfm=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_concat.cmdline
            if self.inputs.run:
                run_concat.run()



        else:
            if self.inputs.verbose:
                cmd=' '.join(['cp', tmp_xfm, self.inputs.out_file_xfm])
                print(cmd)
            if self.inputs.run:
                shutil.copy(tmp_xfm, self.inputs.out_file_xfm)


        if self.inputs.out_file_img:
            print '\n-+- creating $outfile using $outxfm -+-\n'
            run_resample = ResampleCommand();
            run_resample.inputs.in_file=self.inputs.in_source_file
            run_resample.inputs.out_file=self.inputs.out_file_img
            run_resample.inputs.model_file=self.inputs.in_target_file
            run_resample.inputs.transformation=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

        # shutil.rmtree(tmpDir)
        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file_xfm"] = self.inputs.out_file_xfm
        outputs["out_file_img"] = self.inputs.out_file_img
        
        return outputs





class nLinRegOutput(TraitedSpec):
    out_file_xfm = File(exists=True, desc="transformation matrix")
    out_file_img = File(exists=True, desc="resampled image")

class nLinRegInput(BaseInterfaceInputSpec):
    in_target_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="target image")
    in_source_file = File(position=1, argstr="%s", exists=True, mandatory=True, desc="source image")
    in_target_mask = File(position=2, argstr="-source_mask %s", exists=True, desc="target mask")
    in_source_mask = File(position=3, argstr="-target_mask %s", exists=True, desc="source mask")
    init_file_xfm = File(argstr="-init_xfm %s", exists=True, desc="initial transformation (default identity)")
    normalize = traits.Bool(argstr="-normalize", usedefault=True, default_value=False, desc="Do intensity normalization on source to match intensity of target")
    out_file_xfm = File(position=-2, argstr="%s", mandatory=True, desc="transformation matrix")
    out_file_img = File(position=-1, argstr="%s", desc="resampled image")

    clobber = traits.Bool(position=-5, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(position=-4, argstr="-run", usedefault=False, default_value=False, desc="Run the commands")
    verbose = traits.Bool(position=-3, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class nLinRegRunning(BaseInterface):
    input_spec = nLinRegInput
    output_spec = nLinRegOutput
    _suffix = "_NlReg"


    def _run_interface(self, runtime):
        tmpDir = tempfile.mkdtemp()

        source = self.inputs.in_source_file
        target = self.inputs.in_target_file
        s_base = basename(os.path.splitext(source)[0])
        t_base = basename(os.path.splitext(target)[0])
        if not isdefined(self.inputs.out_file_xfm):
            self.inputs.out_file_xfm = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'xfm', use_ext=False)
        if not isdefined(self.inputs.out_file_img):
            self.inputs.out_file_img = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix)

        if os.path.exists(self.inputs.out_file_xfm):
            os.remove(self.inputs.out_file_xfm) 
 
        prev_xfm = None
        if self.inputs.init_file_xfm:
            prev_xfm = self.inputs.init_file_xfm

        if self.inputs.normalize:
            inorm_target = tmpDir+"/"+t_base+"_inorm.mnc"
            inorm_source = tmpDir+"/"+s_base+"_inorm.mnc"

            run_resample = ResampleCommand();
            run_resample.inputs.in_file=target
            run_resample.inputs.out_file=inorm_target
            run_resample.inputs.model_file=source
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

            run_inormalize = InormalizeCommand();
            run_inormalize.inputs.in_file=source
            run_inormalize.inputs.out_file=inorm_source
            run_inormalize.inputs.model_file=inorm_target
            if self.inputs.verbose:
                print run_inormalize.cmdline
            if self.inputs.run:
                run_inormalize.run()


        else:
            inorm_target = target
            inorm_source = source 


        class tracc_args:
            def __init__(self, nonlinear, weight, stiffness, similarity, sub_lattice):
                # self.debug=debug
                self.nonlinear=nonlinear
                self.weight=weight
                self.stiffness=stiffness
                self.similarity=similarity
                self.sub_lattice=sub_lattice

        class conf:
            def __init__(self, step, blur_fwhm, iterations, lattice_diam):
                self.step=step
                self.blur_fwhm=blur_fwhm
                self.iterations=iterations
                self.lattice_diam=lattice_diam

        conf1 = conf(32,16,20,96)
        conf2 = conf(16,8,20,48)
        conf3 = conf(12,6,20,36)
        conf4 = conf(8,4,20,24)
        conf5 = conf(6,3,20,18)
        conf6 = conf(4,2,10,12)
        conf_list = [ conf1, conf2, conf3, conf4, conf5, conf6 ]

        nonlin_tracc_args = tracc_args('corrcoeff',1.0,1,0.3,6)


        i=1
        for confi in conf_list:
            tmp_source=tmpDir+"/"+s_base+"_fwhm.mnc"
            tmp_source_blur_base=tmpDir+"/"+s_base+"_fwhm"+str(confi.blur_fwhm)
            tmp_source_blur=tmpDir+"/"+s_base+"_fwhm"+str(confi.blur_fwhm)+"_blur.mnc"
            tmp_target=tmpDir+"/"+t_base+"_fwhm.mnc"
            tmp_target_blur_base=tmpDir+"/"+t_base+"_fwhm"+str(confi.blur_fwhm)
            tmp_target_blur=tmpDir+"/"+t_base+"_fwhm"+str(confi.blur_fwhm)+"_blur.mnc"
            tmp_xfm = tmpDir+"/"+t_base+"_conf"+str(i)+".xfm";
            tmp_rspl_vol = tmpDir+"/"+s_base+"_conf"+str(i)+".mnc";



            print '-------+------- iteration'+str(i)+' -------+-------\n'

            if self.inputs.in_source_mask and self.inputs.in_target_mask:
                if os.path.isfile(self.inputs.in_source_mask) and not os.path.exists(tmpDir+"/"+s_base+"_masked.mnc"):
                    source = tmpDir+"/"+s_base+"_masked.mnc"
                    run_calc = CalcCommand();
                    run_calc.inputs.in_file = [inorm_source, self.inputs.in_source_mask]
                    run_calc.inputs.out_file = source
                    # run_calc.inputs.expression='if(A[1]>0.5){out=A[0];}else{out=A[1];}'
                    run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                    if self.inputs.verbose:
                        print run_calc.cmdline
                    if self.inputs.run:
                        run_calc.run()

                if os.path.isfile(self.inputs.in_target_mask) and not os.path.exists(tmpDir+"/"+t_base+"_masked.mnc"):
                    target = tmpDir+"/"+t_base+"_masked.mnc"
                    run_calc.inputs.in_file = [inorm_target, self.inputs.in_target_mask]
                    run_calc.inputs.out_file = target
                    run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                    if self.inputs.verbose:
                        print run_calc.cmdline
                    if self.inputs.run:
                        run_calc.run()
            else:
                source = inorm_source
                target = inorm_target



            run_smooth = SmoothCommand();
            run_smooth.inputs.in_file=target
            run_smooth.inputs.fwhm=confi.blur_fwhm
            run_smooth.inputs.out_file=tmp_target_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()

            run_smooth = SmoothCommand();
            run_smooth.inputs.in_file=source
            run_smooth.inputs.fwhm=confi.blur_fwhm
            run_smooth.inputs.out_file=tmp_source_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()


            run_tracc = TraccCommand();
            run_tracc.inputs.in_source_file=tmp_source_blur
            run_tracc.inputs.in_target_file=tmp_target_blur
            if i == 6:
                run_tracc.inputs.out_file_xfm=self.inputs.out_file_xfm
            else :
                run_tracc.inputs.out_file_xfm=tmp_xfm
            run_tracc.inputs.steps=str(confi.step)+' '+str(confi.step)+' '+str(confi.step)
            run_tracc.inputs.iterations=confi.iterations
            run_tracc.inputs.nonlinear=nonlin_tracc_args.nonlinear
            run_tracc.inputs.weight=nonlin_tracc_args.weight
            run_tracc.inputs.stiffness=nonlin_tracc_args.stiffness
            run_tracc.inputs.similarity=nonlin_tracc_args.similarity
            run_tracc.inputs.sub_lattice=nonlin_tracc_args.sub_lattice
            run_tracc.inputs.lattice=str(confi.lattice_diam)+' '+str(confi.lattice_diam)+' '+str(confi.lattice_diam)
            if i == 1:
	    	run_tracc.inputs.identity=True
		
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

            
            if i == 6:
                prev_xfm = self.inputs.out_file_xfm
            else :
                run_resample = ResampleCommand();
                run_resample.inputs.input_file=source
                run_resample.inputs.out_file=tmp_rspl_vol
                run_resample.inputs.model_file=target
                run_resample.inputs.transformation=tmp_xfm
                if self.inputs.verbose:
                    print run_resample.cmdline
                if self.inputs.run:
                    run_resample.run()

                # prev_xfm = tmp_xfm

            i += 1

            print '\n'



        if self.inputs.init_file_xfm:
            run_concat = ConcatCommand();
            run_concat.inputs.in_file=self.inputs.init_xfm
            run_concat.inputs.in_file_2=tmp_xfm
            run_concat.inputs.out_file_xfm=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_concat.cmdline
            if self.inputs.run:
                run_concat.run()

        else:
            if self.inputs.verbose:
                cmd=' '.join(['cp', tmp_xfm, self.inputs.out_file_xfm])
                print(cmd)
            if self.inputs.run:
                shutil.copy(tmp_xfm, self.inputs.out_file_xfm)


        if self.inputs.out_file_img:
            print '\n-+- creating '+self.inputs.out_file_img+' using '+self.inputs.out_file_xfm+' -+-\n'
            run_resample = ResampleCommand();
            run_resample.inputs.input_file=self.inputs.in_source_file
            run_resample.inputs.out_file=self.inputs.out_file_img
            run_resample.inputs.model_file=self.inputs.in_target_file
            run_resample.inputs.transformation=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

        # shutil.rmtree(tmpDir)

        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file_xfm"] = self.inputs.out_file_xfm
        outputs["out_file_img"] = self.inputs.out_file_img
        
        return outputs


