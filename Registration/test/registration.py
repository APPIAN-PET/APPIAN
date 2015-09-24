import os
import tempfile

from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile

from nipype.interfaces.minc.calc import CalcCommand
from nipype.interfaces.minc.smooth import SmoothCommand
from nipype.interfaces.minc.tracc import TraccCommand
from nipype.interfaces.minc.resample import ResampleCommand
from nipype.interfaces.minc.xfmOp import ConcatCommand



def run_bestlinreg_pet2mri(input_source_file, input_target_file, input_source_mask, input_target_mask, init_file_xfm, out_file_xfm, out_file_img, verbose, run):

    tmpdir = tempfile.mkdtemp()
    prev_xfm = None
    if init_file_xfm:
    	prev_xfm = init_file_xfm

    source = input_source_file
    target = input_target_file



    if input_source_mask and input_target_mask:
        if os.path.isfile(input_source_mask):
            source = tmpdir+"/s_base_masked.mnc"
            run_calc = CalcCommand();
            run_calc.inputs.input_file = [input_source_file, input_source_mask]
            run_calc.inputs.out_file = source
            # run_calc.inputs.expression='if(A[1]>0.5){out=A[0];}else{out=A[1];}'
            run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
            if verbose:
                print run_calc.cmdline
            if run:
                run_calc.run()


        if os.path.isfile(input_target_mask):
            target = tmpdir+"/t_base_masked.mnc"
            run_calc.inputs.input_file = [input_target_file, input_target_mask]
            run_calc.inputs.out_file = target
            run_calc.inputs.expression='A[1] > 0.5 ? A[0] : A[1]'
            if verbose:
                print run_calc.cmdline
            if run:
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
    	tmp_source=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_pet)
    	tmp_source_blur_base=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_pet)
    	tmp_source_blur=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_pet)+"_"+confi.type_+".mnc"
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
        if verbose:
            print run_smooth.cmdline
        if run:
            run_smooth.run()

        run_smooth = SmoothCommand();
        run_smooth.inputs.input_file=source
        run_smooth.inputs.fwhm=confi.blur_fwhm_pet
        run_smooth.inputs.output_file=tmp_source_blur_base
        if verbose:
            print run_smooth.cmdline
        if run:
            run_smooth.run()


        run_tracc = TraccCommand();
        run_tracc.inputs.input_source_file=tmp_source_blur
        run_tracc.inputs.input_target_file=tmp_target_blur
        run_tracc.inputs.out_file_xfm=tmp_xfm
        run_tracc.inputs.objective_func='mi'
        run_tracc.inputs.step=confi.steps
        run_tracc.inputs.simplex=confi.simplex
        run_tracc.inputs.tolerance=confi.tolerance
        run_tracc.inputs.est=confi.est
        if prev_xfm:
            run_tracc.inputs.transformation=prev_xfm
        if input_source_mask:
            run_tracc.inputs.input_source_mask=input_source_mask
        if input_target_mask:
            run_tracc.inputs.input_target_mask=input_target_mask

        if verbose:
            print run_tracc.cmdline
        if run:
            run_tracc.run()

        

        run_resample = ResampleCommand();
        run_resample.inputs.input_file=source
        run_resample.inputs.out_file=tmp_rspl_vol
        run_resample.inputs.model_file=target
        run_resample.inputs.transformation=tmp_xfm
        if verbose:
            print run_resample.cmdline
        if run:
            run_resample.run()

        prev_xfm = tmp_xfm
        i += 1

        print '\n'


    if init_file_xfm:
    	run_concat = ConcatCommand();
    	run_concat.inputs.in_file_xfm=init_xfm
    	run_concat.inputs.in_file_xfm2=prev_xfm
    	run_concat.inputs.out_file_xfm=out_file_xfm
    	if verbose:
    	    print run_concat.cmdline
    	if run:
    	    run_concat.run()



    else:
    	if verbose:
    	    cmd=' '.join(['cp', prev_xfm, out_file_xfm])
    	    print(cmd)
    	if run:
    	    copyfile(prev_xfm, out_file_xfm)


    if out_file_img:
    	print '\n-+- creating $outfile using $outxfm -+-\n'
    	run_resample = ResampleCommand();
    	run_resample.inputs.input_file=input_source_file
    	run_resample.inputs.out_file=out_file_img
    	run_resample.inputs.model_file=input_target_file
    	run_resample.inputs.transformation=out_file_xfm
    	if verbose:
    	    print run_resample.cmdline
    	if run:
    	    run_resample.run()


