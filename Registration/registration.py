# vim: set tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
# vim: filetype plugin indent on
import os
import numpy as np
import tempfile
import shutil
import Extra.resample as rsl
from Test.test_group_qc import myIdent
from os.path import basename

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath, 
                                    BaseInterface, OutputMultiPath, BaseInterfaceInputSpec, isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile
from nipype.interfaces.utility import Rename

import nipype.interfaces.minc as minc

from nipype.interfaces.minc import Calc as CalcCommand
from Extra.tracc import TraccCommand

import nipype.interfaces.minc as minc 
from Extra.xfmOp import ConcatCommand
from Extra.inormalize import InormalizeCommand



class PETtoT1LinRegOutput(TraitedSpec):
    out_file_xfm = File(desc="transformation matrix")
    out_file_xfm_invert = File(desc="inverted transformation matrix")
    out_file_img = File(desc="resampled image 3d")

class PETtoT1LinRegInput(BaseInterfaceInputSpec):
    in_target_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="target image")
    in_source_file = File(position=1, argstr="%s", exists=True, mandatory=True, desc="source image")
    in_target_mask = File(position=2, argstr="-source_mask %s", exists=True, desc="target mask")
    in_source_mask = File(position=3, argstr="-target_mask %s", exists=True, desc="source mask")
    init_file_xfm = File(argstr="-init_xfm %s", exists=True, desc="initial transformation (default identity)")
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
        #tmpDir = tempfile.mkdtemp()
        tmpDir = os.getcwd() + os.sep + 'tmp_PETtoT1LinRegRunning'  #tempfile.mkdtemp()
        os.mkdir(tmpDir)
        source = self.inputs.in_source_file
        target = self.inputs.in_target_file
        s_base = basename(os.path.splitext(source)[0])
        t_base = basename(os.path.splitext(target)[0])


        if not isdefined(self.inputs.out_file_xfm):
            self.inputs.out_file_xfm = os.getcwd()+os.sep+s_base+"_TO_"+t_base+"_"+self._suffix+'.xfm'
        if not isdefined(self.inputs.out_file_xfm_invert):
            self.inputs.out_file_xfm_invert = os.getcwd()+os.sep+t_base+"_TO_"+s_base+"_"+self._suffix+'.xfm'
        if not isdefined(self.inputs.out_file_img):
            self.inputs.out_file_img = os.getcwd()+os.sep+s_base+"_TO_"+t_base+"_"+self._suffix+ '.mnc'


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
                #run_calc = CalcCommand();
                run_calc = minc.Calc();
                #MIC run_calc.inputs.in_file = [self.inputs.in_source_file, self.inputs.in_source_mask]
                run_calc.inputs.input_files = [self.inputs.in_source_file, self.inputs.in_source_mask]
                #MIC run_calc.inputs.out_file = source
                run_calc.inputs.output_file = source

                print 'Source Mask:', source
                # run_calc.inputs.expression='if(A[1]>0.5){out=A[0];}else{out=A[1];}'
                run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
                if self.inputs.verbose:
                    print run_calc.cmdline
                if self.inputs.run:
                    run_calc.run()


            if os.path.isfile(self.inputs.in_target_mask):
                target = tmpDir+"/"+t_base+"_masked.mnc"
                run_calc.inputs.input_files = [self.inputs.in_target_file, self.inputs.in_target_mask]
                #run_calc.inputs.out_file = target
                run_calc.inputs.output_file = target

                print 'Target Mask:', target
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

            run_smooth = minc.Blur();
            run_smooth.inputs.input_file=target
            run_smooth.inputs.fwhm=confi.blur_fwhm_target
            run_smooth.inputs.output_file_base=tmp_target_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()

            run_smooth = minc.Blur();
            run_smooth.inputs.input_file=source
            run_smooth.inputs.fwhm=confi.blur_fwhm_source
            run_smooth.inputs.output_file_base=tmp_source_blur_base
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

            run_resample = minc.Resample();
            run_resample.inputs.input_file=source
            run_resample.inputs.output_file=tmp_rspl_vol
            run_resample.inputs.like=target
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
            run_concat = minc.ConcatCommand();
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
        else: print "\n\nNOPE\n\n"; exit(1);

        #Invert transformation
        run_xfmpetinvert = minc.XfmInvert();
        run_xfmpetinvert.inputs.input_file = self.inputs.out_file_xfm
        run_xfmpetinvert.inputs.output_file = self.inputs.out_file_xfm_invert
        if self.inputs.verbose:
            print run_xfmpetinvert.cmdline
        if self.inputs.run:
            run_xfmpetinvert.run()



        #if self.inputs.out_file_img:
        print '\n-+- Resample 3d PET image -+-\n'
        run_resample = minc.Resample();
        run_resample.inputs.input_file=self.inputs.in_source_file
        run_resample.inputs.output_file=self.inputs.out_file_img
        run_resample.inputs.like=self.inputs.in_target_file
        run_resample.inputs.transformation=self.inputs.out_file_xfm

        print '\n\n', self.inputs.out_file_xfm
        print self.inputs.out_file_xfm_invert
        print self.inputs.out_file_img, '\n\n'

        if self.inputs.verbose:
            print run_resample.cmdline
        if self.inputs.run:
            run_resample.run()


        #shutil.rmtree(tmpDir)
        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file_xfm):
            self.inputs.out_file_xfm = os.getcwd()+os.sep+s_base+"_TO_"+t_base+"_"+self._suffix+'.xfm'
        if not isdefined(self.inputs.out_file_xfm_invert):
            self.inputs.out_file_xfm_invert = os.getcwd()+os.sep+t_base+"_TO_"+s_base+"_"+self._suffix+'.xfm'
        if not isdefined(self.inputs.out_file_img):
            self.inputs.out_file_img = os.getcwd()+os.sep+s_base+"_TO_"+t_base+"_"+self._suffix+ '.mnc'

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
    run = traits.Bool(position=-4, argstr="-run", usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Bool(position=-3, argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class nLinRegRunning(BaseInterface):
    input_spec = nLinRegInput
    output_spec = nLinRegOutput
    _suffix = "_NlReg"


    def _run_interface(self, runtime):
        #tmpDir = tempfile.mkdtemp()
        tmpDir = os.getcwd() + os.sep + 'tmp_nLinReg'
        os.mkdir(tmpDir)
        source = self.inputs.in_source_file
        target = self.inputs.in_target_file
        s_base = basename(os.path.splitext(source)[0])
        t_base = basename(os.path.splitext(target)[0])
        if not isdefined(self.inputs.out_file_xfm):
            self.inputs.out_file_xfm = fname_presuffix(os.getcwd()+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'xfm', use_ext=False)
        if not isdefined(self.inputs.out_file_img):
            self.inputs.out_file_img = fname_presuffix(os.getcwd()+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix)

        prev_xfm = None
        if self.inputs.init_file_xfm:
            prev_xfm = self.inputs.init_file_xfm

        if self.inputs.normalize:
            inorm_target = tmpDir+"/"+t_base+"_inorm.mnc"
            inorm_source = tmpDir+"/"+s_base+"_inorm.mnc"

            run_resample = minc.Resample();
            run_resample.inputs.in_file=target
            run_resample.inputs.out_file=inorm_target
            run_resample.inputs.like=source

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
                    run_calc = minc.Calc();
                    run_calc.inputs.input_files = [inorm_source, self.inputs.in_source_mask]
                    run_calc.inputs.output_file = source
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


            run_smooth = minc.Blur();
            run_smooth.inputs.input_file=target
            run_smooth.inputs.fwhm=confi.blur_fwhm
            run_smooth.inputs.output_file_base=tmp_target_blur_base
            if self.inputs.verbose:
                print run_smooth.cmdline
            if self.inputs.run:
                run_smooth.run()

            run_smooth = minc.Blur();
            run_smooth.inputs.input_file=source
            run_smooth.inputs.fwhm=confi.blur_fwhm
            run_smooth.inputs.output_file_base=tmp_source_blur_base
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
            if i == len(conf_list):
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
            run_tracc.run()

            
            if i == len(conf_list):
                prev_xfm = self.inputs.out_file_xfm
            else :
                prev_xfm = tmp_xfm
            
            run_resample = minc.Resample();
            run_resample.inputs.input_file=source
            run_resample.inputs.output_file=tmp_rspl_vol
            run_resample.inputs.like=target
            run_resample.inputs.transformation=run_tracc.inputs.out_file_xfm
            if self.inputs.verbose:
                print run_resample.cmdline
            if self.inputs.run:
                run_resample.run()

            i += 1


        if isdefined(self.inputs.init_file_xfm):
            run_concat = minc.XfmConcat();
            run_concat.inputs.input_files=[ self.inputs.init_xfm, prev_xfm  ]
            run_concat.inputs.output_file=self.inputs.out_file_xfm
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

        print '\n-+- creating '+self.inputs.out_file_img+' using '+self.inputs.out_file_xfm+' -+-\n'
        run_resample = minc.Resample();
        run_resample.inputs.input_file=self.inputs.in_source_file
        run_resample.inputs.output_file=self.inputs.out_file_img
        run_resample.inputs.like=self.inputs.in_target_file
        run_resample.inputs.transformation=self.inputs.out_file_xfm
        if self.inputs.verbose:
            print run_resample.cmdline
        if self.inputs.run:
            run_resample.run()

        #shutil.rmtree(tmpDir)
        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file_xfm):
            self.inputs.out_file_xfm = fname_presuffix(os.getcwd()+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix+'xfm', use_ext=False)
        if not isdefined(self.inputs.out_file_img):
            self.inputs.out_file_img = fname_presuffix(os.getcwd()+os.sep+s_base+"_TO_"+t_base, suffix=self._suffix)

        outputs["out_file_xfm"] = self.inputs.out_file_xfm
        outputs["out_file_img"] = self.inputs.out_file_img
        
        return outputs
"""
.. module:: registration
    :platform: Unix
    :synopsis: Module to perform image registration. 
.. moduleauthor:: Thomas Funck <tffunck@gmail.com>
"""
def get_workflow(name, infosource, opts):
    '''
        Create workflow to perform PET to T1 co-registration.

        1. PET to T1 coregistration with brain masks
        2. PET to T1 coregistration without brain masks (OPTIONAL)
        3. Transform T1 MRI brainmask and headmask from MNI 152 to T1 native
        4. Resample 4d PET image to T1 space
        5. Resample 4d PET image to MNI 152 space

        :param name: Name for workflow
        :param infosource: Infosource for basic variables like subject id (sid) and condition id (cid)
        :param datasink: Node in which output data is sent
        :param opts: User options
        
        :returns: workflow
    '''
    workflow = pe.Workflow(name=name)
    #Define input node that will receive input from outside of workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_volume","pet_volume_4d","nativeT1nuc","pet_headMask","t1_headMask","tka_label_img_t1","results_label_img_t1","pvc_label_img_t1", "t1_brain_mask", "xfmT1MNI", "T1Tal", "error"]), name='inputnode')
    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["petmri_img", "petmri_img_4d","petmni_img_4d","petmri_xfm","petmri_xfm_invert","tka_label_img_pet","results_label_img_pet","pvc_label_img_pet", "pet_brain_mask"]), name='outputnode')

    node_name="pet2mri_withMask"
    pet2mri_withMask = pe.Node(interface=PETtoT1LinRegRunning(), name=node_name)
    pet2mri_withMask.inputs.clobber = True
    pet2mri_withMask.inputs.verbose = opts.verbose
    pet2mri_withMask.inputs.run = opts.prun
    rPet2MriImg=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name+"Img")
    rPet2MriXfm=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+".xfm"), name="r"+node_name+"Xfm")
    rPet2MriXfmInvert=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_"+node_name+"_invert.xfm"), name="r"+node_name+"XfmInvert")

    if opts.no_mask :
        node_name="pet2mri"
        pet2mri = pe.Node(interface=PETtoT1LinRegRunning(), name=node_name)
        pet2mri.inputs.clobber = True
        pet2mri.inputs.verbose = opts.verbose
        pet2mri.inputs.run = opts.prun
    else : 
        pet2mri = pet2mri_withMask
    final_pet2mri = pet2mri

    node_name="pet_brain_mask"
    pet_brain_mask = pe.Node(interface=minc.Resample(), name=node_name)
    pet_brain_mask.inputs.nearest_neighbour_interpolation = True
    pet_brain_mask.inputs.clobber = True
    pet_brain_mask_img = 'output_file'
    rpet_brain_mask=pe.Node(interface=Rename(format_string="sid-%(sid)s_task-%(cid)s_"+node_name+".mnc"), name="r"+node_name)
    workflow.connect([(inputnode, pet_brain_mask, [('t1_brain_mask', 'input_file' )]),
                        (pet2mri, pet_brain_mask, [('out_file_img', 'like')]), 
                        (pet2mri, pet_brain_mask, [('out_file_xfm_invert', 'transformation')])
                    ]) 

    if opts.no_mask :
        workflow.connect([(inputnode, pet2mri, [('pet_volume', 'in_source_file')]),
                          (inputnode, pet2mri, [('nativeT1nuc', 'in_target_file')]),
                          (pet2mri_withMask, pet2mri, [('out_file_xfm', 'init_file_xfm')])
                          ]) 

    rPet2MriImg=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_Pet2MriImg.mnc"), name="rPet2MriImg")
    rPet2MriXfm=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_Pet2MriXfm.xfm"), name="rPet2MriXfm")
    rPet2MriXfmInvert=pe.Node(interface=Rename(format_string="%(sid)s_%(cid)s_Pet2MriXfm_invert.xfm"), name="rPet2MriXfmInvert")

    if not opts.tka_method == None:
        node_name="pet_tka_mask"
        petRefMask = pe.Node(interface=minc.Resample(), name=node_name)
        petRefMask.inputs.nearest_neighbour_interpolation = True
        petRefMask.inputs.clobber = True
        rPetRefMask=pe.Node(interface=Rename(format_string="sid-%(sid)s_task-%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    node_name="pet_results_mask"
    petROIMask = pe.Node(interface=minc.Resample(), name=node_name)
    petROIMask.inputs.nearest_neighbour_interpolation = True
    petROIMask.inputs.clobber = True
    rPetROIMask=pe.Node(interface=Rename(format_string="sid-%(sid)s_task-%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    if not opts.nopvc:
        node_name="pet_pvc_mask"
        petPVCMask = pe.Node(interface=minc.Resample(), name=node_name)
        petPVCMask.inputs.nearest_neighbour_interpolation = True
        petPVCMask.inputs.clobber = True
        rPetPVCMask=pe.Node(interface=Rename(format_string="sid-%(sid)s_task-%(cid)s_"+node_name+".mnc"), name="r"+node_name)

    workflow.connect([(inputnode, pet2mri_withMask, [('pet_volume', 'in_source_file')]),
                      (inputnode, pet2mri_withMask, [('pet_headMask', 'in_source_mask')]), 
                      (inputnode, pet2mri_withMask, [('nativeT1nuc', 'in_target_file')])
                      ]) 

    if opts.coregistration_target_mask == 'skull': 
        workflow.connect(inputnode, 't1_headMask',  pet2mri_withMask, 'in_target_mask')
    elif opts.coregistration_target_mask == 'brain' :
        workflow.connect(inputnode, 't1_brain_mask',  pet2mri_withMask, 'in_target_mask')

    if opts.test_group_qc :
        ###Create rotation xfm files based on transform error
        transformNode = pe.Node(interface=rsl.param2xfmInterfaceCommand(), name='transformNode')
        workflow.connect(inputnode, 'error', transformNode, 'transformation')
        ###Apply transformation to PET file
        transform_resampleNode=pe.Node(interface=rsl.ResampleCommand(),name="transform_resampleNode")
        transform_resampleNode.inputs.use_input_sampling=True;
        workflow.connect(transformNode, 'out_file', transform_resampleNode, 'transformation')
        workflow.connect(pet2mri, 'out_file_img', transform_resampleNode, 'in_file')

        ### Concatenate pet2mri and misalignment xfm
        pet2misalign_xfm=pe.Node(interface=ConcatCommand(), name="pet2misalign_xfm")
        workflow.connect(pet2mri,'out_file_xfm', pet2misalign_xfm, 'in_file')
        workflow.connect(transformNode,'out_file', pet2misalign_xfm, 'in_file_2')

        ###Rotate brain mask
        transform_brainmaskNode=pe.Node(interface=rsl.ResampleCommand(), name="transform_brainmaskNode" )
        transform_brainmaskNode.inputs.interpolation='nearest_neighbour'
        workflow.connect(pet2misalign_xfm, 'out_file', transform_brainmaskNode, 'transformation')
        workflow.connect(transform_resampleNode, 'out_file', transform_brainmaskNode, 'model_file')
        workflow.connect(pet_brain_mask, pet_brain_mask_img, transform_brainmaskNode, 'in_file')   



        invert_concat_pet2misalign_xfm=pe.Node(interface=minc.XfmInvert(),name="invert_concat_pet2misalign_xfm")
        workflow.connect(pet2misalign_xfm,'out_file',invert_concat_pet2misalign_xfm,'input_file') 
        pet2mri = final_pet2mri = pe.Node(interface=niu.IdentityInterface(fields=["out_file_img", "out_file_xfm", "out_file_xfm_invert"]), name="pet2mri_misaligned") 
        workflow.connect(transform_resampleNode, "out_file", final_pet2mri, "out_file_img")
        workflow.connect(pet2misalign_xfm, "out_file", final_pet2mri, "out_file_xfm")
        workflow.connect(invert_concat_pet2misalign_xfm, "output_file", final_pet2mri, "out_file_xfm_invert")
        pet_brain_mask = transform_brainmaskNode
        pet_brain_mask_img = 'out_file'

    if not opts.tka_method == None:
        workflow.connect([  (inputnode, petRefMask, [('tka_label_img_t1', 'input_file' )]),
                            (inputnode, petRefMask, [('pet_volume', 'like')]), 
                            (pet2mri, petRefMask, [('out_file_xfm_invert', 'transformation')]) ])

        workflow.connect([(petRefMask, rPetRefMask, [('output_file', 'in_file')])])
        workflow.connect([(infosource, rPetRefMask, [('sid', 'sid')]),
                          (infosource, rPetRefMask, [('cid', 'cid')])  ])
        workflow.connect(rPetRefMask, 'out_file', outputnode, 'tka_label_img_pet')
    
    
    workflow.connect([(inputnode, petROIMask, [('results_label_img_t1', 'input_file' )]),
                      (inputnode, petROIMask, [('pet_volume', 'like')]), 
                      (pet2mri, petROIMask, [('out_file_xfm_invert', 'transformation')]) ]) 
    workflow.connect([(petROIMask, rPetROIMask, [('output_file', 'in_file')])])
    workflow.connect([(infosource, rPetROIMask, [('sid', 'sid')]),
                      (infosource, rPetROIMask, [('cid', 'cid')]) ])
    if not opts.nopvc:
        workflow.connect(inputnode,'pvc_label_img_t1', petPVCMask, 'input_file'  )
        workflow.connect(inputnode,'pet_volume', petPVCMask, 'like'  )
        workflow.connect(pet2mri, 'out_file_xfm_invert' ,petPVCMask, 'transformation'  )

        workflow.connect([(petPVCMask, rPetPVCMask, [('output_file', 'in_file')])])
        workflow.connect([(infosource, rPetPVCMask, [('sid', 'sid')]), (infosource, rPetPVCMask, [('cid', 'cid')])])
        workflow.connect(rPetPVCMask, 'out_file', outputnode, 'pvc_label_img_pet')



    #Resample 4d PET image to T1 space
    pettot1_4D = pe.Node(interface=minc.Resample(), name='pettot1_4D')
    pettot1_4D.inputs.output_file='pet_space-t1_4d.mnc'
    rpettot1_4D=pe.Node(interface=Rename(format_string="sid-%(sid)s_task-%(cid)s_space-t1_pet.mnc"), name="rpettot1_4D")
    workflow.connect(inputnode, 'pet_volume_4d', pettot1_4D, 'input_file')
    workflow.connect(pet2mri, 'out_file_xfm', pettot1_4D, 'transformation')
    workflow.connect(inputnode, 'nativeT1nuc', pettot1_4D, 'like')
    workflow.connect(pettot1_4D,'output_file', rpettot1_4D, 'in_file' )
    workflow.connect(infosource, 'sid', rpettot1_4D, 'sid' )
    workflow.connect(infosource, 'cid', rpettot1_4D, 'cid' )
      
    #Resample 4d PET image to MNI space
    t1tomni_4D = pe.Node(interface=minc.Resample(), name='t1tomni_4D')
    t1tomni_4D.inputs.output_file='pet_space-mni_4d.mnc'
    rt1tomni_4D=pe.Node(interface=Rename(format_string="sid-%(sid)s_task-%(cid)s_space-mni_pet.mnc"), name="rt1tomni_4D")
    workflow.connect(pettot1_4D, 'output_file', t1tomni_4D, 'input_file')
    workflow.connect(inputnode, "xfmT1MNI", t1tomni_4D, 'transformation')
    workflow.connect(inputnode, 'T1Tal', t1tomni_4D, 'like')
    workflow.connect(t1tomni_4D,'output_file', rt1tomni_4D, 'in_file' )
    workflow.connect(infosource, 'sid', rt1tomni_4D, 'sid' )
    workflow.connect(infosource, 'cid', rt1tomni_4D, 'cid' )


    workflow.connect([(final_pet2mri, rPet2MriImg, [('out_file_img', 'in_file')])])
    workflow.connect([(infosource, rPet2MriImg, [('sid', 'sid')]),
                      (infosource, rPet2MriImg, [('cid', 'cid')]) ])

    workflow.connect([(final_pet2mri, rPet2MriXfm, [('out_file_xfm_invert', 'in_file')])])
    workflow.connect([(infosource, rPet2MriXfm, [('sid', 'sid')]),
                      (infosource, rPet2MriXfm, [('cid', 'cid')])  ])

    workflow.connect([(final_pet2mri, rPet2MriXfmInvert, [('out_file_xfm_invert', 'in_file')])])
    workflow.connect([(infosource, rPet2MriXfmInvert, [('sid', 'sid')]),
                      (infosource, rPet2MriXfmInvert, [('cid', 'cid')])  ])

    workflow.connect([(pet_brain_mask, rpet_brain_mask, [(pet_brain_mask_img, 'in_file')])])
    workflow.connect([(infosource, rpet_brain_mask, [('sid', 'sid')]),
                      (infosource, rpet_brain_mask, [('cid', 'cid')]) ])

    workflow.connect(rpettot1_4D,'out_file', outputnode, 'petmri_img_4d')
    workflow.connect(rt1tomni_4D,'out_file', outputnode, 'petmni_img_4d')
    workflow.connect(rPet2MriXfm, 'out_file', outputnode, 'petmri_xfm')
    workflow.connect(rPet2MriXfmInvert, 'out_file', outputnode, 'petmri_xfm_invert')
    workflow.connect(rPet2MriImg, 'out_file', outputnode, 'petmri_img')
    workflow.connect(rPetROIMask, 'out_file', outputnode, 'results_label_img_pet')
    workflow.connect(rpet_brain_mask, 'out_file', outputnode,'pet_brain_mask' )
    return(workflow)
