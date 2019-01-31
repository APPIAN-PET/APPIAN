# vim: set tabstop=4 expandtab shiftwidth=4 softtabstop=4 mouse=a autoindent hlsearch
# vim: filetype plugin indent on
import os
import numpy as np
import tempfile
import shutil
import Extra.resample as rsl
from Test.test_group_qc import myIdent
from os.path import basename

from pyminc.volumes.factory import *
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
#from Extra.compression import gzipResampleCommand
from Extra.modifHeader import FixHeaderCommand, FixHeaderLinkCommand

class PETheadMaskingOutput(TraitedSpec):
    out_file  = File(desc="Headmask from PET volume")

class PETheadMaskingInput(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="PET volume")
    in_json = File(exists=True, mandatory=True, desc="PET json file")
    out_file = File(desc="Head mask")
    slice_factor = traits.Float(usedefault=True, default_value=0.25, desc="Value (between 0. to 1.) that is multiplied by the maximum of the slices of the PET image. Used to threshold slices. Lower value means larger mask")
    total_factor = traits.Float(usedefault=True, default_value=0.333, desc="Value (between 0. to 1.) that is multiplied by the thresholded means of each slice. ")

    clobber = traits.Bool(usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(usedefault=True, default_value=True, desc="Run the commands")
    verbose = traits.Bool(usedefault=True, default_value=True, desc="Write messages indicating progress")

class PETheadMasking(BaseInterface):
    input_spec = PETheadMaskingInput
    output_spec = PETheadMaskingOutput
    _suffix = "_brain_mask"

    # def _parse_inputs(self, skip=None):
    #     if skip is None:
    #         skip = []
    #     if not isdefined(self.inputs.out_file):
    #         self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix)
    #     return super(PETheadMasking, self)._parse_inputs(skip=skip)
    def _run_interface(self, runtime):
        if not isdefined(self.inputs.out_file):
            base = os.path.basename(self.inputs.in_file)
            split = os.path.splitext(base)
            self.inputs.out_file = os.getcwd() +os.sep + split[0] + self._suffix + split[1]
            #Load PET 3D volume
        infile = volumeFromFile(self.inputs.in_file)
        zmax=infile.sizes[infile.dimnames.index("zspace")]
        #Get max slice values and multiply by pet_mask_slice_threshold (0.25 by default)
        slice_thresholds=np.amax(infile.data, axis=(1,2)) * self.inputs.slice_factor
        #Get mean for all values above slice_max
        slice_mean_f=lambda t, d, i: float(np.mean(d[i, d[i,:,:] > t[i]]))
        slice_mean = np.array([ slice_mean_f(slice_thresholds, infile.data, i)  for i in range(zmax) ])
        #Remove nan from slice_mean
        slice_mean =slice_mean[ ~ np.isnan(slice_mean) ]
        #Calculate overall mean from mean of thresholded slices
        overall_mean = np.mean(slice_mean)
        #Calcuate threshold
        threshold = overall_mean * self.inputs.total_factor
        #Apply threshold and create and write outputfile
        run_calc = CalcCommand();
        run_calc.inputs.input_files = self.inputs.in_file
        run_calc.inputs.output_file = self.inputs.out_file
        run_calc.inputs.expression = 'A[0] >= '+str(threshold)+' ? 1 : 0'
        if self.inputs.verbose:
            print run_calc.cmdline
        if self.inputs.run:
            run_calc.run()

        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = fname_presuffix(self.inputs.in_file, suffix=self._suffix)
        outputs["out_file"] = self.inputs.out_file
        return outputs


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
    lsq =  traits.String(desc="Number of parameters to use for transformation")
    metric =  traits.String(desc="Metric for coregistration", default="mi", use_default=True)
    error =  traits.String(desc="Error level by which to mis-register PET image")
    clobber = traits.Bool(position=-5, argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    run = traits.Bool(position=-4, argstr="-run", usedefault=True, default_value=True, desc="Run the commands")
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
            self.inputs.out_file_xfm = os.getcwd()+os.sep+s_base+self._suffix+'.xfm'
        if not isdefined(self.inputs.out_file_xfm_invert):
            self.inputs.out_file_xfm_invert = os.getcwd()+os.sep+t_base+self._suffix+'.xfm'
        if not isdefined(self.inputs.out_file_img):
            self.inputs.out_file_img = os.getcwd()+os.sep+s_base+self._suffix+ '.mnc'

        #print("\n\n\n")
        #print( self.inputs.out_file_img )
        #print("\n\n\n")
        #exit(0)

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
            def __init__(self, type_, est, blur_fwhm_target, blur_fwhm_source, steps, tolerance, simplex, lsq, blur_gradient):
                self.type_=type_
                self.est=est
                self.blur_fwhm_target=blur_fwhm_target
                self.blur_fwhm_source=blur_fwhm_source
                self.steps=steps
                self.tolerance=tolerance
                self.simplex=simplex
                self.lsq=lsq
		self.blur_gradient=blur_gradient

        if isdefined( self.inputs.lsq ) :
            lsq0=self.inputs.lsq
            lsq1=self.inputs.lsq
            lsq2=self.inputs.lsq
            lsq3=self.inputs.lsq
            lsq4=self.inputs.lsq
        else :
            lsq0="lsq6"
            lsq1="lsq6"
            lsq2="lsq7"
            lsq3="lsq9"
            lsq4="lsq12"

        #conf1 = conf("blur", "-est_translations", 10, 6, "8 8 8", 0.01, 8, lsq1)
        #conf2 = conf("blur", "", 6, 6, "4 4 4", 0.004, 6, lsq2)
        #conf3 = conf("blur", "", 4, 4, "2 2 2", 0.002, 4, lsq3)

        conf0 = conf("blur", "-est_translations", 16, 16, "8 8 8", 0.01, 32, lsq0, False)
        conf1 = conf("blur", "", 8, 8, "4 4 4", 0.004, 16, lsq1, False)
        conf2 = conf("blur", "", 4, 4, "4 4 4", 0.004, 8, lsq2, False)
        conf3 = conf("blur", "", 4, 4, "4 4 4", 0.004, 4, lsq3, True)
        conf4 = conf("blur", "", 2, 2, "2 2 2", 0.004, 2, lsq4, True)

        #conf_list = [ conf0 ] #, conf1, conf2, conf3, conf4 ]
        conf_list = [  conf0, conf1, conf2, conf3, conf4 ]

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
            print '       | lsq : \t\t'+ confi.lsq
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
            if confi.blur_gradient :
                run_smooth.inputs.gradient=True

            print run_smooth.cmdline
            run_smooth.run()

            run_smooth = minc.Blur();
            run_smooth.inputs.input_file=source
            run_smooth.inputs.fwhm=confi.blur_fwhm_source
            run_smooth.inputs.output_file_base=tmp_source_blur_base
            if confi.blur_gradient :
                run_smooth.inputs.gradient=True
            run_smooth.inputs.no_apodize=True

            print run_smooth.cmdline
            run_smooth.run()

            run_tracc = TraccCommand();
            run_tracc.inputs.in_source_file=tmp_source_blur
            run_tracc.inputs.in_target_file=tmp_target_blur
            run_tracc.inputs.out_file_xfm=tmp_xfm
            run_tracc.inputs.objective_func=self.inputs.metric
            run_tracc.inputs.steps=confi.steps
            run_tracc.inputs.simplex=confi.simplex
            run_tracc.inputs.tolerance=confi.tolerance
            run_tracc.inputs.est=confi.est
            run_tracc.inputs.lsq=confi.lsq
            if prev_xfm:
                run_tracc.inputs.transformation=prev_xfm
            if self.inputs.in_source_mask:
                run_tracc.inputs.in_source_mask=self.inputs.in_source_mask
            if self.inputs.in_target_mask:
                run_tracc.inputs.in_target_mask=self.inputs.in_target_mask

            print run_tracc.cmdline
            if self.inputs.run:
                run_tracc.run()

            run_resample = minc.Resample();
            run_resample.inputs.keep_real_range=True
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


        #No need for this because the final xfm file includes the initial one
        if isdefined(self.inputs.error):
            ###Create rotation xfm files based on transform error
            transformNode = pe.Node(interface=rsl.param2xfmInterfaceCommand(), name='transformNode')
            transformNode.inputs.error = self.inputs.error

            ###
            run_concat = minc.ConcatCommand();
            run_concat.inputs.in_file=transformNode.inputs.output_file
            run_concat.inputs.in_file_2=tmp_xfm
            run_concat.inputs.out_file=self.inputs.out_file_xfm
            print run_concat.cmdline
            run_concat.run()

            tmp_xfm = self.inputs.out_file_xfm

            misregister_pet = minc.Resample();
            misregister_pet.inputs.keep_real_range=True
            misregister_pet.inputs.input_file=self.inputs.out_file_img
            #misregister_pet.inputs.output_file=tmpDir+os.sep+"temp_pet_4d_misaligned.mnc"
            misregister_pet.inputs.use_input_sampling=True
            misregister_pet.inputs.transformation=self.inputs.out_file_xfm
            shutil.copy(self.inputs.output_file, self.inputs.out_file_img)
        else :
            cmd=' '.join(['cp', tmp_xfm, self.inputs.out_file_xfm])
            print(cmd)
            shutil.copy(tmp_xfm, self.inputs.out_file_xfm)

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
        run_resample.inputs.keep_real_range=True
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
            run_resample.inputs.keep_real_range=True
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
            run_resample.inputs.keep_real_range=True
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

        print '\n-+- creating '+self.inputs.out_file_img+' using '+self.inputs.out_file_xfm+' -+-\n'
        run_resample = minc.Resample();
        run_resample.inputs.keep_real_range=True
        run_resample.inputs.input_file=self.inputs.in_source_file
        run_resample.inputs.output_file=self.inputs.out_file_img
        run_resample.inputs.like=self.inputs.in_target_file
        run_resample.inputs.transformation=self.inputs.out_file_xfm
        if self.inputs.verbose:
            print run_resample.cmdline
        if self.inputs.run:
            run_resample.run()

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
    inputnode = pe.Node(niu.IdentityInterface(fields=["pet_volume","pet_volume_4d","nativeT1nuc","t1_headMask","tka_label_img_t1","results_label_img_t1","pvc_label_img_t1", "t1_brain_mask", "xfmT1MNI", "T1Tal", "error", "header" ]), name='inputnode')
    #Define empty node for output
    outputnode = pe.Node(niu.IdentityInterface(fields=["petmri_img", "pet_img_4d","petmri_xfm","mripet_xfm",'petmni_xfm', 'mnipet_xfm' ]), name='outputnode')

    node_name="pet_brainmask"
    petMasking = pe.Node(interface=PETheadMasking(), name=node_name)
    petMasking.inputs.slice_factor = opts.slice_factor
    petMasking.inputs.total_factor = opts.total_factor
    workflow.connect(inputnode, 'pet_volume', petMasking, 'in_file')
    workflow.connect(inputnode, 'header', petMasking, 'in_json')

    node_name="pet2mri"
    pet2mri = pe.Node(interface=PETtoT1LinRegRunning(), name=node_name)
    pet2mri.inputs.clobber = True
    pet2mri.inputs.verbose = opts.verbose
    pet2mri.inputs.lsq="lsq6"
    pet2mri.inputs.metric="mi"
    final_pet2mri = pet2mri

    if isdefined(inputnode.inputs.error) :
        final_pet2mri.inputs.error = error

    node_name="t1_brain_mask_pet-space"
    t1_brain_mask_rsl = pe.Node(interface=minc.Resample(), name=node_name)
    t1_brain_mask_rsl.inputs.nearest_neighbour_interpolation = True
    t1_brain_mask_rsl.inputs.clobber = True
    t1_brain_mask_img = 'output_file'

    workflow.connect([(inputnode, pet2mri, [('pet_volume', 'in_source_file')]),
                                  (inputnode, pet2mri, [('nativeT1nuc', 'in_target_file')])#,
                                  ])

    workflow.connect([(inputnode, t1_brain_mask_rsl, [('t1_brain_mask', 'input_file' )]),
                        (inputnode, t1_brain_mask_rsl, [('pet_volume', 'like')]),
                        (pet2mri, t1_brain_mask_rsl, [('out_file_xfm_invert', 'transformation')])
                    ])

    if opts.test_group_qc :
        ###Create rotation xfm files based on transform error
        transformNode = pe.Node(interface=rsl.param2xfmInterfaceCommand(), name='transformNode')
        workflow.connect(inputnode, 'error', transformNode, 'transformation')

        ### Concatenate pet2mri and misalignment xfm
        pet2misalign_xfm=pe.Node(interface=ConcatCommand(), name="pet2misalign_xfm")
        workflow.connect(pet2mri,'out_file_xfm', pet2misalign_xfm, 'in_file')
        workflow.connect(transformNode,'out_file', pet2misalign_xfm, 'in_file_2')

        ###Apply transformation to PET file
        transform_resampleNode=pe.Node(interface=rsl.ResampleCommand(),name="transform_resampleNode")
        transform_resampleNode.inputs.use_input_sampling=True;
        workflow.connect(transformNode, 'out_file', transform_resampleNode, 'transformation')
        workflow.connect(pet2mri, 'out_file_img', transform_resampleNode, 'in_file')

        ###Rotate brain mask
        transform_brainmaskNode=pe.Node(interface=rsl.ResampleCommand(), name="transform_brainmaskNode" )
        transform_brainmaskNode.inputs.interpolation='nearest_neighbour'
        workflow.connect(pet2misalign_xfm, 'out_file', transform_brainmaskNode, 'transformation')
        workflow.connect(transform_resampleNode, 'out_file', transform_brainmaskNode, 'model_file')
        workflow.connect(t1_brain_mask_rsl, t1_brain_mask_img, transform_brainmaskNode, 'in_file')

        invert_concat_pet2misalign_xfm=pe.Node(interface=minc.XfmInvert(),name="invert_concat_pet2misalign_xfm")
        workflow.connect(pet2misalign_xfm,'out_file',invert_concat_pet2misalign_xfm,'input_file')
        pet2mri = final_pet2mri = pe.Node(interface=niu.IdentityInterface(fields=["out_file_img", "out_file_xfm", "out_file_xfm_invert"]), name="pet2mri_misaligned")
        workflow.connect(transform_resampleNode, "out_file", final_pet2mri, "out_file_img")
        workflow.connect(pet2misalign_xfm, "out_file", final_pet2mri, "out_file_xfm")
        workflow.connect(invert_concat_pet2misalign_xfm, "output_file", final_pet2mri, "out_file_xfm_invert")
        t1_brain_mask_rsl = transform_brainmaskNode
        t1_brain_mask_img = 'out_file'


    PETMNIXfm_node = pe.Node( interface=ConcatCommand(), name="PETMNIXfm_node")
    workflow.connect(pet2mri, "out_file_xfm", PETMNIXfm_node, "in_file")
    workflow.connect(inputnode, "xfmT1MNI", PETMNIXfm_node, "in_file_2")

    MNIPETXfm_node = pe.Node(interface=minc.XfmInvert(), name="MNIPETXfm_node")
    workflow.connect( PETMNIXfm_node, "out_file", MNIPETXfm_node, 'input_file'  )

    workflow.connect(PETMNIXfm_node, 'out_file', outputnode, 'petmni_xfm' )
    workflow.connect(MNIPETXfm_node, 'output_file', outputnode, 'mnipet_xfm' )

    #Resample 4d PET image to T1 space
    if opts.analysis_space == 't1':
        pettot1_4d = pe.Node(interface=minc.Resample(), name='pettot1_4d')
        pettot1_4d.inputs.keep_real_range=True
        workflow.connect(inputnode, 'pet_volume_4d', pettot1_4d, 'input_file')
        workflow.connect(pet2mri, 'out_file_xfm', pettot1_4d, 'transformation')
        workflow.connect(inputnode, 'nativeT1nuc', pettot1_4d, 'like')
        workflow.connect(pettot1_4d,'output_file', outputnode, 'pet_img_4d')

        workflow.connect(inputnode, 'nativeT1nuc', outputnode, 't1_analysis_space')
    elif opts.analysis_space == "stereo" :
        #Resample 4d PET image to MNI space
        pettomni_4d = pe.Node(interface=minc.Resample(), name='pettomni_4d')
        pettomni_4d.inputs.keep_real_range=True
        workflow.connect(inputnode, 'pet_volume_4d', pettomni_4d, 'input_file')
        workflow.connect(PETMNIXfm_node, "out_file", pettomni_4d, 'transformation')
        workflow.connect(inputnode, 'T1Tal',pettomni_4d, 'like')
        workflow.connect(pettomni_4d,'output_file', outputnode, 'pet_img_4d')
    
    workflow.connect(final_pet2mri, 'out_file_xfm', outputnode, 'petmri_xfm')
    workflow.connect(final_pet2mri, 'out_file_xfm_invert', outputnode, 'mripet_xfm')
    workflow.connect(final_pet2mri, 'out_file_img', outputnode, 'petmri_img')
    workflow.connect(t1_brain_mask_rsl, t1_brain_mask_img, outputnode,'t1_brain_mask' )
    return workflow
