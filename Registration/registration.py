import os
import numpy as np
import tempfile
import shutil

from os.path import basename

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile
from nipype.interfaces.utility import Rename

import nipype.interfaces.minc as minc
from nipype.interfaces.minc.calc import CalcCommand
from nipype.interfaces.minc.smooth import SmoothCommand
from nipype.interfaces.minc.tracc import TraccCommand
from nipype.interfaces.minc.resample import ResampleCommand
from nipype.interfaces.minc.xfmOp import ConcatCommand
from nipype.interfaces.minc.xfmOp import InvertCommand
from nipype.interfaces.minc.inormalize import InormalizeCommand



class PETtoT1LinRegOutput(TraitedSpec):
    out_file_xfm = File(desc="transformation matrix")
    out_file_xfm_invert = File(desc="inverted transformation matrix")
    out_file_img = File(desc="resampled image")

class PETtoT1LinRegInput(BaseInterfaceInputSpec):
    in_target_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="target image")
    in_source_file = File(position=1, argstr="%s", exists=True, mandatory=True, desc="source image")
    in_target_mask = File(position=2, argstr="-source_mask %s", exists=True, desc="target mask")
    in_source_mask = File(position=3, argstr="-target_mask %s", exists=True, desc="source mask")
    init_file_xfm = File(argstr="-init_xfm %s", exists=True, desc="initial transformation (default identity)")
    # out_file_xfm = File(position=-2, argstr="%s", desc="transformation matrix")
    out_file_xfm = File(position=-3, argstr="%s", desc="transformation matrix")
    out_file_xfm_invert = File(position=-2, argstr="%s", desc="inverted transformation matrix")
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
            self.inputs.out_file_xfm = fname_presuffix(os.getcwd()+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'.xfm', use_ext=False)
        if not isdefined(self.inputs.out_file_xfm_invert):
            self.inputs.out_file_xfm_invert = fname_presuffix(os.getcwd()+os.sep+t_base+"_TO_"+s_base, suffix=self._suffix+'.xfm', use_ext=False)
            #self.inputs.out_file_xfm_invert = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+t_base+"_TO_"+s_base, suffix=self._suffix+'.xfm', use_ext=False)
        if not isdefined(self.inputs.out_file_img):
            self.inputs.out_file_img = fname_presuffix(os.getcwd()+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'.mnc', use_ext=False)
            #self.inputs.out_file_img = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'.mnc', use_ext=False)
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
            def __init__(self, type_, est, blur_fwhm_target, blur_fwhm_source, steps, tolerance, simplex):
                self.type_=type_
                self.est=est
                self.blur_fwhm_target=blur_fwhm_target
                self.blur_fwhm_source=blur_fwhm_source
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



            print '-------+------- iteration'+str(i)+' -------+-------'
            print '       | steps : \t\t'+ confi.steps
            print '       | blur_fwhm_mri : \t'+ str(confi.blur_fwhm_target)
            print '       | blur_fwhm_pet : \t'+ str(confi.blur_fwhm_source)
            print '       | simplex : \t\t'+ str(confi.simplex)
            print '       | source : \t\t'+ tmp_source_blur
            print '       | target : \t\t'+ tmp_target_blur
            print '       | xfm : \t\t\t'+ tmp_xfm
            print '       | out : \t\t\t'+ tmp_rspl_vol
            print '\n'

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
            run_tracc.inputs.objective_func='nmi'
            run_tracc.inputs.steps=confi.steps
            run_tracc.inputs.simplex=confi.simplex
            run_tracc.inputs.tolerance=confi.tolerance
            run_tracc.inputs.est=confi.est
            run_tracc.inputs.lsq='lsq6'
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

            prev_xfm = tmp_xfm
            i += 1

            print '\n'


        ''' 
        No need for this because the final xfm file includes the initial one
        if self.inputs.init_file_xfm:
            run_concat = ConcatCommand();
            run_concat.inputs.in_file=self.inputs.init_file_xfm
            run_concat.inputs.in_file_2=tmp_xfm
            run_concat.inputs.out_file=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_concat.cmdline
            if self.inputs.run:
                run_concat.run()
        else:'''
        if self.inputs.verbose:
            cmd=' '.join(['cp', tmp_xfm, self.inputs.out_file_xfm])
            print(cmd)
        if self.inputs.run:
            shutil.copy(tmp_xfm, self.inputs.out_file_xfm)


        #Invert transformation
        run_xfmpetinvert = InvertCommand();
        run_xfmpetinvert.inputs.in_file = self.inputs.out_file_xfm
        run_xfmpetinvert.inputs.out_file = self.inputs.out_file_xfm_invert
        if self.inputs.verbose:
            print run_xfmpetinvert.cmdline
        if self.inputs.run:
            run_xfmpetinvert.run()



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
        outputs["out_file_xfm_invert"] = self.inputs.out_file_xfm_invert
        outputs["out_file_img"] = self.inputs.out_file_img
        
        return outputs





class nLinRegOutput(TraitedSpec):
    out_file_xfm = File(exists=True, desc="transformation matrix")
    out_file_img = File(exists=True, desc="resampled image")

class nLinRegInput(BaseInterfaceInputSpec):
    in_target_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="target image")
    in_source_file = File(position=1, argstr="%s", exists=True, mandatory=True, desc="source image")
    in_target_mask = File(position=2, argstr="-source_mask %s", desc="target mask")
    in_source_mask = File(position=3, argstr="-target_mask %s", desc="source mask")
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
            #self.inputs.out_file_xfm = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'xfm', use_ext=False)
            self.inputs.out_file_xfm = fname_presuffix(os.getcwd()+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'xfm', use_ext=False)
        if not isdefined(self.inputs.out_file_img):
            #self.inputs.out_file_img = fname_presuffix(os.path.dirname(self.inputs.in_source_file)+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix)
            self.inputs.out_file_img = fname_presuffix(os.getcwd()+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix)

        if os.path.exists(self.inputs.out_file_xfm):
            os.remove(self.inputs.out_file_xfm) 
        if os.path.exists(self.inputs.out_file_xfm_invert):
            os.remove(self.inputs.out_file_xfm_invert) 
 
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



            print '-------+------- iteration'+str(i)+' -------+-------'
            print '       | steps : \t\t'+ str(confi.step)
            print '       | blur_fwhm : \t\t'+ str(confi.blur_fwhm)
            print '       | nonlinear : \t\t'+ str(nonlin_tracc_args.nonlinear)
            print '       | weight : \t\t'+ str(nonlin_tracc_args.weight)
            print '       | stiffness : \t\t'+ str(nonlin_tracc_args.stiffness)
            print '       | similarity : \t\t'+ str(nonlin_tracc_args.similarity)
            print '       | sub_lattice : \t\t'+ str(nonlin_tracc_args.sub_lattice)
            print '       | source : \t\t'+ tmp_source_blur
            print '       | target : \t\t'+ tmp_target_blur
            print '       | xfm : \t\t\t'+ tmp_xfm
            print '       | out : \t\t\t'+ tmp_rspl_vol
            print '\n'

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
            run_tracc.inputs.steps=str(confi.step)+' '+str(confi.step)+' '+str(confi.step)
            run_tracc.inputs.iterations=confi.iterations
            run_tracc.inputs.nonlinear=nonlin_tracc_args.nonlinear
            run_tracc.inputs.weight=nonlin_tracc_args.weight
            run_tracc.inputs.stiffness=nonlin_tracc_args.stiffness
            run_tracc.inputs.similarity=nonlin_tracc_args.similarity
            run_tracc.inputs.sub_lattice=nonlin_tracc_args.sub_lattice
            run_tracc.inputs.lattice=str(confi.lattice_diam)+' '+str(confi.lattice_diam)+' '+str(confi.lattice_diam)
            if i == 6:
                run_tracc.inputs.out_file_xfm=self.inputs.out_file_xfm
            else :
                run_tracc.inputs.out_file_xfm=tmp_xfm
            print "\nOutput of minctracc:" +  run_tracc.inputs.out_file_xfm + "\n"
            if i == 1:
                run_tracc.inputs.identity=True
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

            
            if i == 6:
                prev_xfm = self.inputs.out_file_xfm
            else :
                prev_xfm = tmp_xfm
            run_resample = ResampleCommand();
            run_resample.inputs.in_file=source
            run_resample.inputs.out_file=tmp_rspl_vol
            run_resample.inputs.model_file=target
            run_resample.inputs.transformation=run_tracc.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

                # prev_xfm = tmp_xfm

            i += 1


        if self.inputs.init_file_xfm:
            run_concat = ConcatCommand();
            run_concat.inputs.in_file=self.inputs.init_xfm
            run_concat.inputs.in_file_2=prev_xfm
            run_concat.inputs.out_file_xfm=self.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_concat.cmdline
            if self.inputs.run:
                run_concat.run()

        # else:
        #     if self.inputs.verbose:
        #         cmd=' '.join(['cp', prev_xfm, self.inputs.out_file_xfm])
        #         print(cmd)
        #     if self.inputs.run:
        #         shutil.copy(prev_xfm, self.inputs.out_file_xfm)





        if self.inputs.out_file_img:
            print '\n-+- creating '+self.inputs.out_file_img+' using '+self.inputs.out_file_xfm+' -+-\n'
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


def get_workflow(name, infosource, datasink, opts):

    workflow = pe.Workflow(name=name)

    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_volume","nativeT1nuc","pet_headMask","t1_headMask","t1_refMask","t1_ROIMask","t1_PVCMask"]), name='inputnode')

    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["petmri_img","petmri_xfm","petmri_xfm_invert","pet_refMask","pet_ROIMask","pet_PVCMask"]), name='outputnode')

    node_name="pet2mri_withMask"
    pet2mri_withMask = pe.Node(interface=PETtoT1LinRegRunning(), name=node_name)
    pet2mri_withMask.inputs.clobber = True
    pet2mri_withMask.inputs.verbose = opts.verbose
    pet2mri_withMask.inputs.run = opts.prun
    rPet2MriImg=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name+"Img")
    rPet2MriXfm=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".xfm"), name="r"+node_name+"Xfm")
    rPet2MriXfmInvert=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"_invert.xfm"), name="r"+node_name+"XfmInvert")

    node_name="pet2mri"
    pet2mri = pe.Node(interface=PETtoT1LinRegRunning(), name=node_name)
    pet2mri.inputs.clobber = True
    pet2mri.inputs.verbose = opts.verbose
    pet2mri.inputs.run = opts.prun
    rPet2MriImg=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name+"Img")
    rPet2MriXfm=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".xfm"), name="r"+node_name+"Xfm")
    rPet2MriXfmInvert=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"_invert.xfm"), name="r"+node_name+"XfmInvert")


    node_name="petRefMask"
    petRefMask = pe.Node(interface=minc.ResampleCommand(), name=node_name)
    petRefMask.inputs.interpolation = 'nearest_neighbour'
    # petRefMask.inputs.invert = 'invert_transformation'
    petRefMask.inputs.clobber = True
    rPetRefMask=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    node_name="petROIMask"
    petROIMask = pe.Node(interface=minc.ResampleCommand(), name=node_name)
    petROIMask.inputs.interpolation = 'nearest_neighbour'
    # petROIMask.inputs.invert = 'invert_transformation'
    petROIMask.inputs.clobber = True
    rPetROIMask=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    node_name="petPVCMask"
    petPVCMask = pe.Node(interface=minc.ResampleCommand(), name=node_name)
    petPVCMask.inputs.interpolation = 'nearest_neighbour'
    # petPVCMask.inputs.invert = 'invert_transformation'
    petPVCMask.inputs.clobber = True
    rPetPVCMask=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)


    workflow.connect([(inputnode, pet2mri_withMask, [('pet_volume', 'in_source_file')]),
                      (inputnode, pet2mri_withMask, [('pet_headMask', 'in_source_mask')]), 
                      (inputnode, pet2mri_withMask, [('t1_headMask',  'in_target_mask')]),
                      (inputnode, pet2mri_withMask, [('nativeT1nuc', 'in_target_file')])
                      ]) 

    workflow.connect([(inputnode, pet2mri, [('pet_volume', 'in_source_file')]),
                      (inputnode, pet2mri, [('nativeT1nuc', 'in_target_file')]),
                      (pet2mri_withMask, pet2mri, [('out_file_xfm', 'init_file_xfm')])
                      ]) 


    workflow.connect([(pet2mri, rPet2MriImg, [('out_file_img', 'in_file')])])
    workflow.connect([(infosource, rPet2MriImg, [('study_prefix', 'study_prefix')]),
                      (infosource, rPet2MriImg, [('sid', 'sid')]),
                      (infosource, rPet2MriImg, [('cid', 'cid')])
                    ])

    workflow.connect([(pet2mri, rPet2MriXfm, [('out_file_xfm_invert', 'in_file')])])
    workflow.connect([(infosource, rPet2MriXfm, [('study_prefix', 'study_prefix')]),
                      (infosource, rPet2MriXfm, [('sid', 'sid')]),
                      (infosource, rPet2MriXfm, [('cid', 'cid')])
                    ])

    workflow.connect([(pet2mri, rPet2MriXfmInvert, [('out_file_xfm_invert', 'in_file')])])
    workflow.connect([(infosource, rPet2MriXfmInvert, [('study_prefix', 'study_prefix')]),
                      (infosource, rPet2MriXfmInvert, [('sid', 'sid')]),
                      (infosource, rPet2MriXfmInvert, [('cid', 'cid')])
                    ])

    workflow.connect(rPet2MriXfmInvert, 'out_file', datasink, pet2mri.name+"XfmInvert")
    workflow.connect(rPet2MriXfm, 'out_file', datasink, pet2mri.name+"Xfm")
    workflow.connect(rPet2MriImg, 'out_file', datasink, pet2mri.name+"Img")







    workflow.connect([(inputnode, petRefMask, [('t1_refMask', 'in_file' )]),
                      (inputnode, petRefMask, [('pet_volume', 'model_file')]), 
                      # (pet2mri, petRefMask, [('out_file_xfm', 'transformation')])
                      (pet2mri, petRefMask, [('out_file_xfm_invert', 'transformation')])
                    ]) 

    workflow.connect([(petRefMask, rPetRefMask, [('out_file', 'in_file')])])
    workflow.connect([(infosource, rPetRefMask, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetRefMask, [('sid', 'sid')]),
                      (infosource, rPetRefMask, [('cid', 'cid')])
                    ])

    workflow.connect(rPetRefMask, 'out_file', datasink, petRefMask.name)

    workflow.connect([(inputnode, petROIMask, [('t1_ROIMask', 'in_file' )]),
                      (inputnode, petROIMask, [('pet_volume', 'model_file')]), 
                      # (pet2mri, petROIMask, [('out_file_xfm', 'transformation')])
                      (pet2mri, petROIMask, [('out_file_xfm_invert', 'transformation')])
                    ]) 

    workflow.connect([(petROIMask, rPetROIMask, [('out_file', 'in_file')])])
    workflow.connect([(infosource, rPetROIMask, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetROIMask, [('sid', 'sid')]),
                      (infosource, rPetROIMask, [('cid', 'cid')])
                    ])

    workflow.connect(rPetROIMask, 'out_file', datasink, petROIMask.name)

    if not opts.pvcrun:
        workflow.connect([(inputnode, petPVCMask, [('t1_PVCMask', 'in_file' )]),
                          (inputnode, petPVCMask, [('pet_volume', 'model_file')]), 
                          # (pet2mri, petPVCMask, [('out_file_xfm', 'transformation')])
                          (pet2mri, petPVCMask, [('out_file_xfm_invert', 'transformation')])
                        ]) 

        workflow.connect([(petPVCMask, rPetPVCMask, [('out_file', 'in_file')])])
        workflow.connect([(infosource, rPetPVCMask, [('study_prefix', 'study_prefix')]),
                          (infosource, rPetPVCMask, [('sid', 'sid')]),
                          (infosource, rPetPVCMask, [('cid', 'cid')])
                        ])

        workflow.connect(rPetPVCMask, 'out_file', datasink, petPVCMask.name)

        workflow.connect(rPetPVCMask, 'out_file', outputnode, 'pet_PVCMask')






    workflow.connect(rPet2MriXfm, 'out_file', outputnode, 'petmri_xfm')
    workflow.connect(rPet2MriXfmInvert, 'out_file', outputnode, 'petmri_xfm_invert')
    workflow.connect(rPet2MriImg, 'out_file', outputnode, 'petmri_img')
    workflow.connect(rPetRefMask, 'out_file', outputnode, 'pet_refMask')
    workflow.connect(rPetROIMask, 'out_file', outputnode, 'pet_ROIMask')

    return(workflow)
