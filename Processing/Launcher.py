#!/usr/bin/env python

import os
import sys
import argparse
import commands
import shutil
import tempfile
import time

from optparse import OptionParser
from optparse import OptionGroup

import nipype.interfaces.minc as minc
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
from nipype.interfaces.utility import Rename

from ScanConstructor import * 
import Masking.masking as masking
import Settings.settings as settings

version = "1.0"


sys.path.append('')
sys.path.append('/dagher/dagher1/klarcher/git/tka_nipype/Masking')


def printOptions(opts,args):
	uname = os.system('uname -s -n -r')

	print "\n* Pipeline started at "+time.strftime("%c")+"on "+uname
	print "\n* Command line is:\n  %prog"+str(sys.argv)+"\n"
	print "\n* The source directory is:"+opts.sourceDir+"\n"
	print "\n* Data-set Subject ID(s) is/are:"+args+"\n";
	print "\n* PET conditions :"+opts.condiList+"\n";
	print "\n* ROI labels :"+opts.ROILabels+"\n";

def initPipeline(opts,args):
	if args:
		id_subjs = args
	else:
		print "\n\n*******ERROR********: \n     The subject IDs are not listed in the command-line \n********************\n\n"
		sys.exit(1)

	for id in id_subjs:
		scan.set_filenames(opts,id)

def runPipeline(scan,opts):	
	pet_volume = pe.Node(interface=minc.AverageCommand(), name="pet_volume")
	pet_volume.inputs.input_file = scan.pypet.dynamic_pet_raw_real
	pet_volume.inputs.out_file = scan.pypet.volume_pet
	pet_volume.inputs.avgdim = 'time'
	pet_volume.inputs.width_weighted = True
	pet_volume.inputs.clobber = True;
	pet_volume.inputs.verbose = True;
	pet_volume.inputs.run = False;


	pet_settings = pe.Node(interface=settings.PETinfoRunning(), name="pet_info")
	pet_settings.inputs.input_file = scan.pypet.dynamic_pet_raw_real;
	pet_settings.inputs.output_file = scan.pypet.dynamic_pet_info;
	pet_settings.inputs.verbose = False;
	pet_settings.inputs.run = True;
	pet_settings.inputs.clobber = True;


	pet_headmasking = pe.Node(interface=masking.PETheadMaskingRunning(), name="pet_headmasking")
	pet_headmasking.inputs.input_volume = scan.pypet.volume_pet
	pet_headmasking.inputs.output_file = scan.pypet.volume_pet
	pet_headmasking.inputs.input_json = scan.pypet.dynamic_pet_info;
	pet_headmasking.inputs.verbose = False;
	pet_headmasking.inputs.run = True;


	t1_masking = pe.Node(interface=masking.T1maskingRunning(), name="t1_masking")
	t1_masking.inputs.nativeT1 = scan.civet.t1_native
	t1_masking.inputs.LinT1TalXfm = scan.civet.xfm_tal
	t1_masking.inputs.brainmaskTal = scan.civet.tal_brainmask
	t1_masking.inputs.modelDir = '/data/movement/movement7/klarcher/share/icbm';
	t1_masking.inputs.T1headmask = scan.civet.t1_headmask
	t1_masking.inputs.T1brainmask = scan.civet.t1_brainmask
	t1_masking.inputs.clobber = True;
	t1_masking.inputs.verbose = True;
	t1_masking.inputs.run = False;


	pet2mri_lin = pe.Node(interface=reg.PETtoT1LinRegRunning(), name="pet2mri_lin")
	pet2mri_lin.inputs.input_source_file = scan.pypet.volume_pet
	pet2mri_lin.inputs.input_target_file = scan.civet.t1_native
	pet2mri_lin.inputs.input_source_mask = scan.pypet.volume_pet_headmask
	pet2mri_lin.inputs.input_target_mask = scan.civet.t1_headmask
	pet2mri_lin.inputs.out_file_xfm = scan.pypet.xfm_pet_t1
	pet2mri_lin.inputs.out_file_img = scan.pypet.volume_pet_headmask
	pet2mri_lin.inputs.clobber = True;
	pet2mri_lin.inputs.verbose = True;
	pet2mri_lin.inputs.run = False;


	ref_masking = pe.Node(interface=masking.RefmaskingRunning(), name="ref_masking")
	ref_masking.inputs.nativeT1 = scan.civet.t1_native
	ref_masking.inputs.T1Tal = scan.civet.tal_final
	ref_masking.inputs.LinT1TalXfm = scan.civet.xfm_tal
	ref_masking.inputs.brainmaskTal  = scan.civet.t1_brainmask
	ref_masking.inputs.clsmaskTal  = scan.civet.tal_cls
	ref_masking.inputs.segMaskTal  = scan.civet.tal_animal_masked
	ref_masking.inputs.segLabels = [67, 76];
	ref_masking.inputs.MaskingType = "no-transform"
	ref_masking.inputs.modelDir = '/data/movement/movement7/klarcher/share/icbm';
	# ref_masking.inputs.RefmaskTemplate  = '/dagher/dagher5/klarcher/tvincent/neuroecon/apROI/template/minc/Hammers_mith_atlas_n30r83_SPM5_icbm152_asym_vmPFC.mnc';
	ref_masking.inputs.close = True;
	ref_masking.inputs.refGM = True;
	ref_masking.inputs.refWM = False;
	ref_masking.inputs.RefmaskTal  = scan.pypet.tal_ref
	ref_masking.inputs.RefmaskT1  = scan.pypet.t1_ref
	ref_masking.inputs.clobber = True;
	ref_masking.inputs.verbose = True;
	ref_masking.inputs.run = False;




	workflow = pe.Workflow(name='preproc')
	workflow.base_dir=wkdir


workflow.connect([(pet_volume, pet2mri_lin, [('out_file', 'input_target_file')])])

workflow.connect(t1_masking, 'out_file', pet2mri_lin, 'input_file')

workflow.connect(pet2mri_lin, 'out_file', datasink, 'pet2mri_lin')

#run the work flow
workflow.run()




def get_opt_list(option,opt,value,parser):
	setattr(parser.values,option.dest,value.split(','))

# def printStages(scan,opts):


# def printScan(scan,opts):



if __name__ == "__main__":

	usage = "usage: %prog "

	parser = OptionParser(usage=usage,version=version)

	group= OptionGroup(parser,"File options (mandatory)")
	group.add_option("-s","--sourcedir",dest="sourceDir",help="Native pet and mri directory")
	group.add_option("-t","--targetdir",dest="targetDir",help="Directory where output data will be saved in")
	group.add_option("-p","--prefix",dest="prefix",help="Study name")
	group.add_option("-c","--civetdir",dest="civetDir",help="Civet directory")
	parser.add_option_group(group)		

	group= OptionGroup(parser,"Scan options","***if not, only baseline condition***")
	group.add_option("","--condition",dest="condiList",help="comma-separated list of conditions or scans",type='string',action='callback',callback=get_opt_list,default='baseline')
	parser.add_option_group(group)		

	group= OptionGroup(parser,"Registration options")
	parser.add_option_group(group)		

	group= OptionGroup(parser,"PET acquisition options")
	parser.add_option_group(group)
		
	group= OptionGroup(parser,"Masking options","Reference region")
	group.add_option("","--ref-animal",dest="refValueAnimal",help="Label value(s) from ANIMAL segmentation. By default, the values correspond to the cerebellum",type='string',action='callback',callback=get_opt_list,default=['67','76'])
	group.add_option("","--ref-gm",dest="refMatter",help="Gray matter of reference region (if -ref-animal is used)",action='store_const',const='gm',default='gm')
	group.add_option("","--ref-wm",dest="refMatter",help="White matter of reference region (if -ref-animal is used)",action='store_const',const='wm',default='gm')
	group.add_option("","--ref-template",dest="templateRef",help="Template to segment the reference region.",default='/home/klarcher/bic/models/icbm152/mni_icbm152_t1_tal_nlin_sym_09a.mnc')
	group.add_option("","--ref-linreg",dest="refRegister",help="Non-linear registration based segmentation",action='store_true',default=False)
	group.add_option("","--ref-no-linreg",dest="refRegister",help="Don't run any non-linear registration",action='store_false',default=False)
	group.add_option("","--ref-close",dest="refClose",help="Close - erosion(dialtion(X))",action='store_true',default=False)
	group.add_option("","--ref-mask",dest="refOnTemplate",help="Reference mask on the template",default=None)	
	parser.add_option_group(group)
	group= OptionGroup(parser,"Masking options","Region Of Interest")
	group.add_option("","--roi-animal",dest="roiValueAnimal",help="Label value(s) from ANIMAL segmentation.",type='string',action='callback',callback=get_opt_list)
	group.add_option("","--roi-linreg",dest="roiRegister",help="Non-linear registration based segmentation",action='store_true',default=False)
	group.add_option("","--roi-no-linreg",dest="roiRegister",help="Don't run any non-linear registration",action='store_false',default=False)
	group.add_option("","--roi-template",dest="templateROI",help="Template to segment the ROI.",default='/home/klarcher/bic/models/icbm152/mni_icbm152_t1_tal_nlin_sym_09a.mnc')
	group.add_option("","--roi-template-suffix",dest="templateROIsuffix",help="Suffix for the ROI template.",default='icbm152')
	group.add_option("","--roi-mask",dest="ROIOnTemplate",help="ROI mask on the template",default='/home/klarcher/bic/models/icbm152/mni_icbm152_t1_tal_nlin_BG_mask_6lbl.mnc')	
	group.add_option("","--roi-suffix",dest="ROIsuffix",help="ROI suffix",default='striatal_6lbl')	
	group.add_option("","--roi-labels",dest="ROILabels",help="ROI labels",type='string',action='callback',callback=get_opt_list,default=['4','5','6','9','10','11'])
	group.add_option("","--roi-erosion",dest="roiErosion",help="Erode the ROI mask",action='store_true',default=False)
	parser.add_option_group(group)

	group= OptionGroup(parser,"Tracer Kinetic analysis options")
	parser.add_option_group(group)

	group= OptionGroup(parser,"Pipeline control")
	group.add_option("","--run",dest="prun",help="Run the pipeline.",action='store_true',default=False)
	group.add_option("","--fake",dest="pfake",help="do a dry run, (echo cmds only).",action='store_true',default=True)
	group.add_option("","--print-scan",dest="pscan",help="Print the pipeline parameters for the scan.",action='store_true',default=False)
	group.add_option("","--print-stages",dest="pstages",help="Print the pipeline stages.",action='store_true',default=False)
	parser.add_option_group(group)

	(opts, args) = parser.parse_args()

	opts.extension='mnc.gz'

	if not opts.sourceDir or not opts.targetDir or not opts.civetDir or not opts.prefix:
		print "\n\n*******ERROR******** \n     You must specify -sourcedir, -targetdir, -civetdir  and -prefix \n********************\n"
		parser.print_help()
		sys.exit(1)
	
	if opts.refRegister and opts.templateRef:
		print "\n\n*******ERROR******** \n     You can't use the options -ref-no-transf and -ref-template together \n********************\n"
		parser.print_help()
		sys.exit(1)
	
	opts.targetDir = os.path.normpath(opts.targetDir)
	opts.sourceDir = os.path.normpath(opts.sourceDir)
	opts.civetDir = os.path.normpath(opts.civetDir)

	scan = PipelineFiles()
	initPipeline(opts,args)

	if opts.prun or opts.pfake:
		runPipeline(scan,opts)
	elif opts.pscan:
		printScan(scan,opts)
	elif opts.pstages:
		printStages(scan,opts)
	else:
		print "\n\n*******ERROR********: \n    The options -run, -print-scan or print-stages need to be chosen \n********************\n\n"
		parser.print_help()
