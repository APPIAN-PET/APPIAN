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

import Masking.masking as masking
import Settings.settings as settings

version = "1.0"



def printOptions(opts,args):
	uname = os.popen('uname -s -n -r').read()

	print "\n"
	print "* Pipeline started at "+time.strftime("%c")+"on "+uname
	print "* Command line is : \n "+str(sys.argv)+"\n"
	print "* The source directory is : "+opts.sourceDir
	print "* The target directory is : "+opts.targetDir+"\n"
	print "* The Civet directory is : "+opts.CivetDir+"\n"
	#print "* Data-set Subject ID(s) is/are : "+args+"\n"
	print "* Data-set Subject ID(s) is/are : "+str(', '.join(args))+"\n"
	print "* PET conditions : "+opts.condiList+"\n"
	print "* ROI labels : "+str(', '.join(opts.ROILabels))+"\n"


def create_dirs(opts, id):
	sbjdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep
	logdir=sbjdir+"log"+os.sep
	if not os.path.exists(logdir):
		os.makedirs(logdir)
	tmpdir=sbjdir+"temp"+os.sep
	if not os.path.exists(tmpdir):
		os.makedirs(tmpdir)
	tmptfmdir=sbjdir+"temp"+os.sep+"transforms"+os.sep
	if not os.path.exists(tmptfmdir):
		os.makedirs(tmptfmdir)
	petdir=sbjdir+"pet"+os.sep
	if not os.path.exists(petdir):
		os.makedirs(petdir)
	petdynadir=sbjdir+"pet"+os.sep+"dynamic"+os.sep
	if not os.path.exists(petdynadir):
		os.makedirs(petdynadir)
	petvoldir=sbjdir+"pet"+os.sep+"volume"+os.sep
	if not os.path.exists(petvoldir):
		os.makedirs(petvoldir)
	mrinatdir=sbjdir+"mri"+os.sep+"native"+os.sep
	if not os.path.exists(mrinatdir):
		os.makedirs(mrinatdir)
	mristxdir=sbjdir+"mri"+os.sep+"stereotaxic"+os.sep
	if not os.path.exists(mristxdir):
		os.makedirs(mristxdir)
	lindir=sbjdir+"transforms"+os.sep+"linear"+os.sep
	if not os.path.exists(lindir):
		os.makedirs(lindir)
	nlindir=sbjdir+"transforms"+os.sep+"non-linear"+os.sep
	if not os.path.exists(nlindir):
		os.makedirs(nlindir)
	regdir=sbjdir+"regions"+os.sep
	if not os.path.exists(regdir):
		os.makedirs(regdir)
	tacdir=sbjdir+"TAC"+os.sep
	if not os.path.exists(tacdir):
		os.makedirs(tacdir)
	bpdir=sbjdir+"BP"+os.sep
	if not os.path.exists(bpdir):
		os.makedirs(bpdir)
	bpnatdir=sbjdir+"BP"+os.sep+"native"+os.sep
	if not os.path.exists(bpnatdir):
		os.makedirs(bpnatdir)
	bpstxdir=sbjdir+"BP"+os.sep+"stereotaxic"+os.sep
	if not os.path.exists(bpstxdir):
		os.makedirs(bpstxdir)


def test_get_inputs():
	return 

def runPipeline(opts,args):	
	if args:
		subjects_ids = args
	else:
		print "\n\n*******ERROR********: \n     The subject IDs are not listed in the command-line \n********************\n\n"
		sys.exit(1)

	subjects_ids=["%03d" % subjects_ids[subjects_ids.index(subj)] for subj in subjects_ids]

	printOptions(opts,subjects_ids)

	# for id in subjects_ids:
	#  	create_dirs(opts, id)
	
	conditions_ids=list(range(len(conditions)))


	###Infosource###
	infosource = pe.Node(interface=util.IdentityInterface(fields=['study_prefix', 'subject_id', 'condition_id']), name="infosource")
	infosource.inputs.study_prefix = opts.prefix
	infosource.iterables = [ ('subject_id', subjects_ids), ('condition_id', conditions_ids) ]


	##Datasources###
	datasourceRaw = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'subject_id', 'condition_id'], 
													outfields=['pet', 'mri'], sort_filelist=False), name="datasourceRaw")
	datasourceRaw.inputs.base_directory = opts.sourceDir
	datasourceRaw.inputs.template = '*'
	datasourceRaw.inputs.field_template = dict(pet='pet/%s/%s_%s_%s_real_orig.mnc', 
											   mri='mri/%s/%s_%s_t1.mnc.gz')
	datasourceRaw.inputs.template_args = dict(pet=[['study_prefix', 'study_prefix', 'subject_id', 'condition_id']], 
										   	  mri=[['study_prefix', 'study_prefix', 'subject_id']])	


	datasourceCivet = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'subject_id'], 
														 outfields=['nativeT1', 'nativeT1nuc', 
														 			'talT1', 'xfmT1tal', 
														 			'brainmasktal', 'headmasktal', 'clsmask', 'animalmask'
														 			], 
														 sort_filelist=False), name="datasourceCivet")
	datasourceCivet.inputs.base_directory = opts.CivetDir
	datasourceCivet.inputs.template = '*'
	datasourceCivet.inputs.field_template = dict(nativeT1='%s/native/%s_%s_t1.mnc', 
												 nativeT1nuc='%s/native/%s_%s_t1_nuc.mnc', 
												 talT1='%s/final/%s_%s_t1_tal.mnc',
												 xfmT1tal='%s/transforms/linear/%s_%s_t1_tal.xfm',
												 xfmT1talnl='%s/transforms/nonlinear/%s_%s_nlfit_It.xfm',
												 brainmasktal='%s/mask/%s_%s_brain_mask.mnc',
												 headmasktal='%s/mask/%s_%s_skull_mask.mnc',
												 clsmasktal='%s/classify/%s_%s_pve_classify.mnc',
												 animaltal='%s/segment/%s_%s_stx_labels_masked.mnc',
												 )
	datasourceCivet.inputs.template_args = dict(nativeT1=[['study_prefix', 'study_prefix', 'subject_id']], 
										   		nativeT1nuc=[['study_prefix', 'study_prefix', 'subject_id']], 
										   		talT1=[['study_prefix', 'study_prefix', 'subject_id']], 
										   		xfmT1tal=[['study_prefix', 'study_prefix', 'subject_id']], 
										   		xfmT1talnl=[['study_prefix', 'study_prefix', 'subject_id']], 
										   		brainmasktal=[['study_prefix', 'study_prefix', 'subject_id']], 										   		
										   		headmasktal=[['study_prefix', 'study_prefix', 'subject_id']], 										   		
										   		clsmask=[['study_prefix', 'study_prefix', 'subject_id']], 										   		
										   		animalmask=[['study_prefix', 'study_prefix', 'subject_id']], 										   		
										   		)	


	##Datasink###
	datasink=pe.Node(interface=nio.DataSink(), name="output")
	datasink.inputs.base_directory= opts.sourceDir + '/' +opts.prefix
	datasink.inputs.substitutions = [('_condition_id_', ''), ('subject_id_', '')]


	##Nodes###
	node_name="t1Masking"
	t1Masking = pe.Node(interface=masking.T1maskingRunning(), name=node_name)
	t1Masking.inputs.modelDir = opts.modelDir
	t1Masking.inputs.clobber = True
	t1Masking.inputs.verbose = True
	t1Masking.inputs.run = opts.prun

	rt1Masking=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".mnc"), name="r"+node_name)

	refMasking = pe.Node(interface=masking.RefmaskingRunning(), name="refMasking")
	refMasking.inputs.nativeT1 = scan.civet.t1_native
	refMasking.inputs.T1Tal = scan.civet.tal_final
	refMasking.inputs.LinT1TalXfm = scan.civet.xfm_tal
	refMasking.inputs.brainmaskTal  = scan.civet.t1_brainmask
	refMasking.inputs.clsmaskTal  = scan.civet.tal_cls
	refMasking.inputs.segMaskTal  = scan.civet.tal_animal_masked
	refMasking.inputs.segLabels = opts.RefAtlasValue
	refMasking.inputs.MaskingType = opts.RefMaskType
	refMasking.inputs.modelDir = opts.RefTemplate
	refMasking.inputs.close = opts.RefClose
	refMasking.inputs.refGM = True if opts.RefMatter == 'gm' else False
	refMasking.inputs.refWM = True if opts.RefMatter == 'wm' else False
	refMasking.inputs.RefmaskTal  = scan.pypet.tal_ref
	refMasking.inputs.RefmaskT1  = scan.pypet.t1_ref
	refMasking.inputs.clobber = True
	refMasking.inputs.verbose = True
	refMasking.inputs.run = opts.prun

	pet_volume = pe.Node(interface=minc.AverageCommand(), name="pet_volume")
	pet_volume.inputs.input_file = scan.pypet.dynamic_pet_raw_real
	pet_volume.inputs.out_file = scan.pypet.volume_pet
	pet_volume.inputs.avgdim = 'time'
	pet_volume.inputs.width_weighted = True
	pet_volume.inputs.clobber = True
	pet_volume.inputs.verbose = True

	pet_settings = pe.Node(interface=settings.PETinfoRunning(), name="pet_info")
	pet_settings.inputs.input_file = scan.pypet.dynamic_pet_raw_real
	pet_settings.inputs.output_file = scan.pypet.dynamic_pet_info
	pet_settings.inputs.verbose = True
	pet_settings.inputs.clobber = True
	pet_settings.inputs.run = opts.prun

	pet_headmasking = pe.Node(interface=masking.PETheadMaskingRunning(), name="pet_headmasking")
	pet_headmasking.inputs.input_volume = scan.pypet.volume_pet
	pet_headmasking.inputs.output_file = scan.pypet.volume_pet_headmask
	pet_headmasking.inputs.input_json = scan.pypet.dynamic_pet_info
	pet_headmasking.inputs.verbose = True
	pet_headmasking.inputs.run = opts.prun

	pet2mri_lin = pe.Node(interface=reg.PETtoT1LinRegRunning(), name="pet2mri_lin")
	pet2mri_lin.inputs.input_source_file = scan.pypet.volume_pet
	pet2mri_lin.inputs.input_target_file = scan.civet.t1_native
	pet2mri_lin.inputs.input_source_mask = scan.pypet.volume_pet_headmask
	pet2mri_lin.inputs.input_target_mask = scan.civet.t1_headmask
	pet2mri_lin.inputs.out_file_xfm = scan.pypet.xfm_pet_t1
	pet2mri_lin.inputs.out_file_img = scan.pypet.volume_pet_headmask
	pet2mri_lin.inputs.clobber = True
	pet2mri_lin.inputs.verbose = True
	pet2mri_lin.inputs.run = opts.prun



	workflow = pe.Workflow(name='preproc')
	workflow.base_dir = opts.targetDir

	workflow.connect([(infosource, datasourceRaw, [('subject_id', 'subject_id')]),
                      (infosource, datasourceRaw, [('condition_id', 'condition_id')]),
                      (infosource, datasourceRaw, [('study_prefix', 'study_prefix')]),
                      (infosource, datasourceCivet, [('subject_id', 'subject_id')]),
                      (infosource, datasourceCivet, [('study_prefix', 'study_prefix')])
                	 ])
	workflow.connect(datasourceCivet, ['nativeT1nuc', 'xfmT1tal', 'brainmasktal'], 
					 t1Masking, ['nativeT1', 'LinT1TalXfm', 'brainmaskTal'])
	workflow.connect(t1Masking, ['T1headmask', 'T1brainmask'],
					 rt1Masking, [])


	workflow.connect(node1, 'out_file', rnode1, 'in_file')
	workflow.connect([(infosource, rnode1, [('subject_id', 'subject_id')]),
	                  (infosource, rnode1, [('condition_id', 'condition_id')]),
	                  (infosource, rnode1, [('study_prefix', 'study_prefix')])
	                ])
	workflow.connect(rnode1, 'out_file', datasink, 'node1')
	workflow.connect(infosource, 'subject_id', datasink, 'container')





def get_opt_list(option,opt,value,parser):
	setattr(parser.values,option.dest,value.split(','))


# def printStages(opts,args):



# def printScan(opts,args):



if __name__ == "__main__":

	usage = "usage: "

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
	group.add_option("","--modelDir",dest="modelDir",help="Models directory")
	parser.add_option_group(group)		

	group= OptionGroup(parser,"PET acquisition options")
	parser.add_option_group(group)
		
	group= OptionGroup(parser,"Masking options","Reference region")
	group.add_option("","--ref-atlas",dest="RefMaskType",help="Use an atlas to make the Reference mask",action='store_const',const='atlas',default='atlas')
	group.add_option("","--ref-nonlinear",dest="RefMaskType",help="Non linear registration based segmentatoin",action='store_const',const='nonlinear',default='atlas')
	group.add_option("","--ref-no-transform",dest="RefMaskType",help="Don't run any non-linear registration",action='store_const',const='no-transform',default='atlas')
	group.add_option("","--ref-atlas_labels",dest="RefAtlasValue",help="Label value(s) from ANIMAL segmentation. By default, the values correspond to the cerebellum",type='string',action='callback',callback=get_opt_list,default=['67','76'])
	group.add_option("","--ref-template",dest="RefTemplate",help="Template to segment the reference region.",default='/home/klarcher/bic/models/icbm152/mni_icbm152_t1_tal_nlin_sym_09a.mnc')
	group.add_option("","--ref-gm",dest="RefMatter",help="Gray matter of reference region (if -ref-animal is used)",action='store_const',const='gm',default='gm')
	group.add_option("","--ref-wm",dest="RefMatter",help="White matter of reference region (if -ref-animal is used)",action='store_const',const='wm',default='gm')
	group.add_option("","--ref-close",dest="RefClose",help="Close - erosion(dialtion(X))",action='store_true',default=False)
	group.add_option("","--ref-mask",dest="RefOnTemplate",help="Reference mask on the template",default=None)	
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

	group= OptionGroup(parser,"Command control")
	group.add_option("","--verbose",dest="verbose",help="Write messages indicating progress.",action='store_true',default=True)
	parser.add_option_group(group)

	group= OptionGroup(parser,"Pipeline control")
	group.add_option("","--run",dest="prun",help="Run the pipeline.",action='store_true')
	group.add_option("","--fake",dest="prun",help="do a dry run, (echo cmds only).",action='store_false')
	group.add_option("","--print-scan",dest="pscan",help="Print the pipeline parameters for the scan.",action='store_true',default=False)
	group.add_option("","--print-stages",dest="pstages",help="Print the pipeline stages.",action='store_true',default=False)
	parser.add_option_group(group)

	(opts, args) = parser.parse_args()

	opts.extension='mnc'

	if not opts.sourceDir or not opts.targetDir or not opts.civetDir or not opts.prefix:
		print "\n\n*******ERROR******** \n     You must specify -sourcedir, -targetdir, -civetdir  and -prefix \n********************\n"
		parser.print_help()
		sys.exit(1)
	
	
	opts.targetDir = os.path.normpath(opts.targetDir)
	opts.sourceDir = os.path.normpath(opts.sourceDir)
	opts.civetDir = os.path.normpath(opts.civetDir)


	if opts.prun:
		runPipeline(opts,args)
	elif opts.pscan:
		printScan(opts,args)
	elif opts.pstages:
		printStages(opts,args)
	else:
		print "\n\n*******ERROR********: \n    The options -run, -print-scan or print-stages need to be chosen \n********************\n\n"
		parser.print_help()


	# if opts.pscan:
	# 	printScan(scan,opts)
	# elif opts.pstages:
	# 	printStages(scan,opts)
	# else:
	# 	runPipeline(scan,opts)