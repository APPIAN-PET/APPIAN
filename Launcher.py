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
import nipype.interfaces.utility as niu
from nipype.interfaces.utility import Rename

from Masking import masking as masking
import Registration.registration as reg
import Initialization.initialization as init
import Partial_Volume_Correction.pvc as pvc 
import Results_Report.results as results
import Tracer_Kinetic.tka as tka
# import nipype.interfaces.minc.results as results
version = "1.0"



def printOptions(opts,args):
	uname = os.popen('uname -s -n -r').read()

	print "\n"
	print "* Pipeline started at "+time.strftime("%c")+"on "+uname
	print "* Command line is : \n "+str(sys.argv)+"\n"
	print "* The source directory is : "+opts.sourceDir
	print "* The target directory is : "+opts.targetDir+"\n"
	print "* The Civet directory is : "+opts.civetDir+"\n"
	print "* Data-set Subject ID(s) is/are : "+str(', '.join(args))+"\n"
	print ["* PET conditions : "]+opts.condiList #+"\n"
	print "* ROI labels : "+str(', '.join(opts.ROIAtlasLabels))+"\n"




def test_get_inputs():
	return 

def runPipeline(opts,args):	
	if args:
		subjects_ids = args
	else:
		print "\n\n*******ERROR********: \n     The subject IDs are not listed in the command-line \n********************\n\n"
		sys.exit(1)

	#
	if isinstance(opts.condiList, str):
		opts.condiList=opts.condiList.split(',')
#	subjects_ids=["%03d" % subjects_ids[subjects_ids.index(subj)] for subj in subjects_ids]
	conditions_ids=opts.condiList
#	conditions_ids=opts.condiList


	###Infosource###
	is_fields=['study_prefix', 'sid', 'cid']
	if opts.ROIMaskingType == "roi-user":
		is_fields += ['RoiSuffix']

	infosource = pe.Node(interface=util.IdentityInterface(fields=is_fields), name="infosource")
	infosource.inputs.study_prefix = opts.prefix
	infosource.inputs.RoiSuffix = opts.RoiSuffix
	infosource.iterables = [ ('sid', subjects_ids), ('cid', conditions_ids) ]

	#cid = Condition ID
	#sid = Subject ID
	#sp = Study Prefix

	#################
	###Datasources###
	#################
	#PET datasource
	datasourceRaw = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'sid', 'cid'], outfields=['pet'], sort_filelist=False), name="datasourceRaw")
	datasourceRaw.inputs.base_directory = opts.sourceDir
	datasourceRaw.inputs.template = '*'
	datasourceRaw.inputs.field_template = dict(pet='%s_%s_%s_pet.mnc') #FIXME: No need to have prefix directory
	datasourceRaw.inputs.template_args = dict(pet=[['study_prefix', 'sid', 'cid']])	

	#Subject ROI datasource
	
	if os.path.exists(opts.roi_dir):
		datasourceROI = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'sid', 'RoiSuffix'], 
														   outfields=['subjectROI'], sort_filelist=False), name="datasourceROI")
		datasourceROI.inputs.base_directory = opts.roi_dir
		datasourceROI.inputs.template = '*'
		datasourceROI.inputs.field_template = dict(subjectROI='%s_%s_%s.mnc')
		datasourceROI.inputs.template_args = dict(subjectROI=[['study_prefix', 'sid', 'RoiSuffix']])	

	#CIVET datasource
	datasourceCivet = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'sid', 'cid'], 
														 outfields=['nativeT1', 'nativeT1nuc', 
														 			'T1Tal', 'xfmT1Tal','xfmT1Talnl',
														 			'brainmaskTal', 'headmaskTal', 'clsmask', 'animalmask'], 
														 sort_filelist=False), name="datasourceCivet")
	datasourceCivet.inputs.base_directory = opts.civetDir
	datasourceCivet.inputs.roi_dir = opts.roi_dir
	datasourceCivet.inputs.template = '*'
	datasourceCivet.inputs.field_template = dict(nativeT1='%s_%s/native/%s_%s*t1.mnc', 
												 nativeT1nuc='%s_%s/native/%s_%s*t1_nuc.mnc', 
												 T1Tal='%s_%s/final/%s_%s*t1_tal.mnc',
												 xfmT1Tal='%s_%s/transforms/linear/%s_%s*t1_tal.xfm',
												 xfmT1Talnl='%s_%s/transforms/nonlinear/%s_%s*nlfit_It.xfm',
												 brainmaskTal='%s_%s/mask/%s_%s*brain_mask.mnc',
												 headmaskTal='%s_%s/mask/%s_%s*skull_mask.mnc',
												 clsmask='%s_%s/classify/%s_%s*pve_classify.mnc',
												 animalmask='%s_%s/segment/%s_%s*animal_labels_masked.mnc'
												)
	datasourceCivet.inputs.template_args = dict(nativeT1=[[ 'sid', 'cid', 'study_prefix', 'sid']], 
										   		nativeT1nuc=[['sid', 'cid', 'study_prefix', 'sid']], 
										   		T1Tal=[[ 'sid', 'cid', 'study_prefix', 'sid']], 
										   		xfmT1Tal=[[ 'sid', 'cid', 'study_prefix', 'sid']], 
										   		xfmT1Talnl=[['sid', 'cid', 'study_prefix', 'sid']], 
										   		brainmaskTal=[['sid', 'cid', 'study_prefix', 'sid']], 										   		
										   		headmaskTal=[['sid', 'cid', 'study_prefix', 'sid']], 										   		
										   		clsmask=[['sid', 'cid', 'study_prefix', 'sid']], 										   		
										   		animalmask=[['sid', 'cid', 'study_prefix', 'sid']] 										   		
										   		)	

	##############
	###Datasink###
	##############
	datasink=pe.Node(interface=nio.DataSink(), name="output")
	datasink.inputs.base_directory= opts.targetDir + '/' +opts.prefix
	datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]




	workflow = pe.Workflow(name='preproc')
	workflow.base_dir = opts.targetDir

	workflow.connect([(infosource, datasourceRaw, [('sid', 'sid')]),
                      (infosource, datasourceRaw, [('cid', 'cid')]),
                      (infosource, datasourceRaw, [('study_prefix', 'study_prefix')]),
		      (infosource, datasourceCivet, [('cid', 'cid')]),
                      (infosource, datasourceCivet, [('sid', 'sid')]),
                      (infosource, datasourceCivet, [('study_prefix', 'study_prefix')]),
                	 ])






	###################
	# PET prelimaries #
	###################

	wf_init_pet=init.get_workflow("pet_prelimaries", infosource, datasink, opts)
	workflow.connect(datasourceRaw, 'pet', wf_init_pet, "inputnode.pet")


	out_node_list = [wf_init_pet]
	out_img_list = ['outputnode.pet_center']
	workflow.run(); exit(0)
	###########
	# Masking #
	###########


	wf_masking=masking.get_workflow("masking", infosource, datasink, opts)
	workflow.connect(datasourceCivet, 'nativeT1', wf_masking, "inputnode.nativeT1nuc")
	workflow.connect(datasourceCivet, 'xfmT1Tal', wf_masking, "inputnode.xfmT1Tal")
	workflow.connect(datasourceCivet, 'T1Tal', wf_masking, "inputnode.T1Tal")
	workflow.connect(datasourceCivet, 'brainmaskTal', wf_masking, "inputnode.brainmaskTal")
	workflow.connect(datasourceCivet, 'clsmask', wf_masking, "inputnode.clsmask")
	workflow.connect(datasourceCivet, 'animalmask', wf_masking, "inputnode.animalmask")
	if opts.ROIMaskingType == "roi-user":
		workflow.connect([(infosource, datasourceROI, [('study_prefix', 'study_prefix')]),
                 	  	  (infosource, datasourceROI, [('sid', 'sid')]),
                 	  	  (infosource, datasourceROI, [('RoiSuffix', 'RoiSuffix')])
                 	  	  ])
		workflow.connect(datasourceROI, 'subjectROI', wf_masking, "inputnode.subjectROI")
	workflow.connect(wf_init_pet, 'outputnode.pet_volume', wf_masking, "inputnode.pet_volume")
	workflow.connect(wf_init_pet, 'outputnode.pet_json', wf_masking, "inputnode.pet_json")


	##################
	# Coregistration #
	##################
	wf_pet2mri=reg.get_workflow("to_pet_space", infosource, datasink, opts)
	workflow.connect(wf_init_pet, 'outputnode.pet_volume', wf_pet2mri, "inputnode.pet_volume")
	workflow.connect(datasourceCivet, 'nativeT1nuc', wf_pet2mri, "inputnode.nativeT1nuc")
	workflow.connect(wf_masking, 'outputnode.pet_headMask', wf_pet2mri, "inputnode.pet_headMask")
	workflow.connect(wf_masking, 'outputnode.t1_headMask', wf_pet2mri, "inputnode.t1_headMask")
	workflow.connect(wf_masking, 'outputnode.t1_refMask', wf_pet2mri, "inputnode.t1_refMask")
	workflow.connect(wf_masking, 'outputnode.t1_ROIMask', wf_pet2mri, "inputnode.t1_ROIMask")
	if not opts.pvcrun:
		workflow.connect(wf_masking, 'outputnode.t1_PVCMask', wf_pet2mri, "inputnode.t1_PVCMask")


	if not opts.pvcrun:

		wf_pvc=pvc.get_workflow("PVC", infosource, datasink, opts)
		workflow.connect(wf_init_pet, 'outputnode.pet_center', wf_pvc, "inputnode.pet_center")
		workflow.connect(wf_pet2mri, 'outputnode.pet_PVCMask', wf_pvc, "inputnode.pet_mask")

		out_node_list += [wf_pvc]
		out_img_list += ['outputnode.out_file']



		###########################
		# Tracer kinetic analysis #
		###########################
		if not opts.tka_method == None:
				#Perform TKA on PVC PET
				tka_pvc=tka.get_tka_workflow("tka_pvc", opts)
				workflow.connect(wf_pet2mri, 'outputnode.pet_refMask', tka_pvc, "inputnode.reference")
				workflow.connect(wf_init_pet, 'outputnode.pet_json', tka_pvc, "inputnode.header")
				workflow.connect(wf_pet2mri, 'outputnode.pet_ROIMask', tka_pvc, "inputnode.mask")
				workflow.connect(wf_pvc, 'outputnode.out_file', tka_pvc, "inputnode.in_file")
				workflow.connect(tka_pvc, "outputnode.out_file", datasink, tka_pvc.name)
				if opts.tka_type=="voxel" and opts.tka_method == 'srtm':
					workflow.connect(tka_pve, "outputnode.out_file_t3map", datasink, tka_pve.name+"T3")
				if opts.tka_type=="ROI":
					workflow.connect(tka_pve, "outputnode.out_fit_file", datasink, tka_pve.name+"fit")
				
				out_node_list += [tka_pvc]
				out_img_list += ['outputnode.out_file']

	###########################
	# Tracer kinetic analysis #
	###########################
	else :	
		if not opts.tka_method == None:
			#Perform TKA on uncorrected PET
			tka_pve=tka.get_tka_workflow("tka_pve", opts)
			workflow.connect(wf_pet2mri, 'outputnode.pet_refMask', tka_pve, "inputnode.reference")
			workflow.connect(wf_init_pet, 'outputnode.pet_header', tka_pve, "inputnode.header")
			workflow.connect(wf_pet2mri, 'outputnode.pet_ROIMask', tka_pve, "inputnode.mask")
			workflow.connect(wf_init_pet, 'outputnode.pet_center', tka_pve, "inputnode.in_file")
			workflow.connect(tka_pve, "outputnode.out_file", datasink, tka_pve.name)
			if opts.tka_type=="voxel" and opts.tka_method == 'srtm':
				workflow.connect(tka_pve, "outputnode.out_file_t3map", datasink, tka_pve.name+"T3")
			if opts.tka_type=="ROI":
				workflow.connect(tka_pve, "outputnode.out_fit_file", datasink, tka_pve.name+"fit")
			
			out_node_list += [tka_pve]
			out_img_list += ['outputnode.out_file']






	#######################################
	# Connect nodes for reporting results #
	#######################################
	#Results report for PET
	if opts.tka_type=="voxel":
		for node, img in zip(out_node_list, out_img_list):

			node_name="results_" + node.name + "_" + opts.tka_method
			resultsReport = pe.Node(interface=results.groupstatsCommand(), name=node_name)
			rresultsReport=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".csv"), name="r"+node_name)


			workflow.connect([(node, resultsReport, [(img,'image')]),
							# (roiMasking, resultsReport, [('RegionalMaskPET','vol_roi')])
							(wf_pet2mri, resultsReport, [('outputnode.pet_ROIMask','vol_roi')])
		    				])
			
			workflow.connect([(resultsReport, rresultsReport, [('out_file', 'in_file')])])
			workflow.connect([(infosource, rresultsReport, [('study_prefix', 'study_prefix')]),
		                      (infosource, rresultsReport, [('sid', 'sid')]),
		                      (infosource, rresultsReport, [('cid', 'cid')])
		                    ])
			workflow.connect(rresultsReport, 'out_file', datasink,resultsReport.name )



	printOptions(opts,subjects_ids)
        exit(0)

        ##################
        # Group level QC #
        ##################
        #JoinNode to join together workflows of multiple subjects for group level QC 
        PETtoT1_group_qc = pe.JoinNode(interface=PETtoT1_group_qc(), joinsource="infosource", joinfield=["pet", "t1"], name="PETtoT1_group_qc")
        workflow.connect([(wf_init_pet, PETtoT1_group_qc, [('outputnode.pet_center', 'pet_images')]),
                      (datasourceCivet, PETtoT1_group_qc, [( 'nativeT1', 't1_images')])
                    ])

        

	# #vizualization graph of the workflow
	workflow.write_graph(opts.targetDir+os.sep+"workflow_graph.dot", graph2use = 'exec')
	#run the work flow
	workflow.run()






def get_opt_list(option,opt,value,parser):
	setattr(parser.values,option.dest,value.split(','))


# def printStages(opts,args):

############################################
# Define dictionaries for default settings #
############################################
#Set defaults for labels
roi_labels={} 
roi_labels["ROI"]={	"roi-user":['1'],
			      	"icbm152":['39','53','16','14','25','72'],
					"civet":['1','2','3'],
					"animal":['1','2','3']} #FIXME, these values are not correct for animal
roi_labels["REF"]={	"roi-user":['1'],
		      		"icbm152":['39','53','16','14','25','72'],
					"civet":['3'],
					"animal":['3']} #FIXME, these values are not correct for animal
roi_labels["PVC"]={	"roi-user":['1'],
		      		"icbm152":['39','53','16','14','25','72'],
					"civet":['2','3'],
					"animal":['2','3']} #FIXME, these values are not correct for animal

#Default FWHM for PET scanners
pet_scanners={"HRRT":2.5,"HR+":6.5} #FIXME should be read from a separate .json file and include lists for non-isotropic fwhm

# def printScan(opts,args):
def check_masking_options(ROIMaskingType, roi_dir, RoiSuffix, ROIMask, ROITemplate):
	'''Check to make sure that the user has provided the necessary information for 
	the selected masking type'''
	if ROIMaskingType == "roi-user":
		if not os.path.exists(roi_dir): 
			print "Option \'--roi-user\' requires \'-roi-dir\' "
			exit(1)
		if RoiSuffix == None:
			print "Option \'--roi-user\' requires \'-roi-suffix\' "
			exit(1)

	if ROIMaskingType == "icbm152":
		if not os.path.exists(ROIMask) :
			print "Option \'--icbm152-atlas\' requires \'-roi-mask\' "
			exit(1)

	if ROIMaskingType == "atlas":
		if not os.path.exists(ROIMask) :
			print "Error: recieved " + ROIMask
			print "Option \'--roi-atlas\' requires \'-roi-mask\' "
			exit(1)
		if not os.path.exists(ROITemplate) :
			print "Option \'--roi-atlas\' requires \'-roi-template\' "
			exit(1)


if __name__ == "__main__":

	usage = "usage: "

	file_dir = os.path.dirname(os.path.realpath(__file__))
	atlas_dir = file_dir + "/Atlas/MNI152/"
	icbm152=atlas_dir+'mni_icbm152_t1_tal_nlin_sym_09a.mnc'
	default_atlas = atlas_dir + "mni_icbm152_t1_tal_nlin_sym_09a_atlas/AtlasGrey.mnc"


	parser = OptionParser(usage=usage,version=version)

	group= OptionGroup(parser,"File options (mandatory)")
	group.add_option("-s","--petdir",dest="sourceDir",  help="Native PET directory")
	group.add_option("-t","--targetdir",dest="targetDir",type='string', help="Directory where output data will be saved in")
	group.add_option("-p","--prefix",dest="prefix",type='string',help="Study name")
	group.add_option("-c","--civetdir",dest="civetDir",  help="Civet directory")
	parser.add_option_group(group)		

	group= OptionGroup(parser,"Scan options","***if not, only baseline condition***")
	group.add_option("","--condition",dest="condiList",help="comma-separated list of conditions or scans",type='string',action='callback',callback=get_opt_list,default='baseline')
	parser.add_option_group(group)		

	group= OptionGroup(parser,"Registration options")
	group.add_option("","--modelDir",dest="modelDir",help="Models directory",default=atlas_dir)
	parser.add_option_group(group)		

	group= OptionGroup(parser,"PET acquisition options")


	#Parse user options
	group= OptionGroup(parser,"Masking options","Reference region")
	group.add_option("","--ref-user",dest="RefMaskingType",help="User defined ROI for each subject",action='store_const',const='no-transform',default='civet')	
	group.add_option("","--ref-animal",dest="RefMaskingType",help="Use ANIMAL segmentation",action='store_const',const='animal',default='civet')	
	group.add_option("","--ref-civet",dest="RefMaskingType",help="Use PVE tissue classification from CIVET",action='store_const',const='civet',default='civet')
	group.add_option("","--ref-icbm152-atlas",dest="RefMaskingType",help="Use an atlas defined on ICBM152 template",action='store_const',const='icbm152',default='civet')
	group.add_option("","--ref-atlas",dest="RefMaskingType",help="Use atlas based on template, both provided by user",action='store_const',const='atlas',default='civet')
	group.add_option("","--ref-labels",dest="RefAtlasLabels",help="Label value(s) for segmentation.",type='string',action='callback',callback=get_opt_list,default=None)
	group.add_option("","--ref-template",dest="RefTemplate",help="Template to segment the reference region.",default=icbm152)

	group.add_option("","--ref-suffix",dest="refSuffix",help="ROI suffix",default='striatal_6lbl')	
	group.add_option("","--ref-gm",dest="RefMatter",help="Gray matter of reference region (if -ref-animal is used)",action='store_const',const='gm',default='gm')
	group.add_option("","--ref-wm",dest="RefMatter",help="White matter of reference region (if -ref-animal is used)",action='store_const',const='wm',default='gm')
	group.add_option("","--ref-close",dest="RefClose",help="Close - erosion(dialtion(X))",action='store_true',default=False)
	group.add_option("","--ref-erosion",dest="RoiErosion",help="Erode the ROI mask",action='store_true',default=False)
	group.add_option("","--ref-dir",dest="ref_dir",help="ID of the subject REF masks",type='string', default=None)
	group.add_option("","--ref-template-suffix",dest="templateRefSuffix",help="Suffix for the Ref template.",default='icbm152')
	group.add_option("","--ref-mask",dest="refMask",help="Ref mask on the template",type='string',default=default_atlas)
	parser.add_option_group(group)

	group= OptionGroup(parser,"Masking options","Region Of Interest")
	group.add_option("","--roi-user",dest="ROIMaskingType",help="User defined ROI for each subject",action='store_const',const='roi-user',default='icbm152')	
	group.add_option("","--roi-animal",dest="ROIMaskingType",help="Use ANIMAL segmentation",action='store_const',const='animal',default='icbm152')	
	group.add_option("","--roi-civet",dest="ROIMaskingType",help="Use PVE tissue classification from CIVET",action='store_const',const='civet',default='icbm152')
	group.add_option("","--roi-icbm152",dest="ROIMaskingType",help="Use an atlas defined on ICBM152 template",action='store_const',const='icbm152',default='icbm152')
	group.add_option("","--roi-atlas",dest="ROIMaskingType",help="Use atlas based on template, both provided by user",action='store_const',const='atlas',default='icbm152')	
	group.add_option("","--roi-labels",dest="ROIAtlasLabels",help="Label value(s) for segmentation.",type='string',action='callback',callback=get_opt_list,default=None)

	group.add_option("","--roi-template",dest="ROITemplate",help="Template to segment the ROI.",default=icbm152)
	group.add_option("","--roi-mask",dest="ROIMask",help="ROI mask on the template",default=default_atlas)	
	group.add_option("","--roi-template-suffix",dest="templateRoiSuffix",help="Suffix for the ROI template.",default='icbm152')
	group.add_option("","--roi-suffix",dest="RoiSuffix",help="ROI suffix",default='striatal_6lbl')	
	group.add_option("","--roi-erosion",dest="RoiErosion",help="Erode the ROI mask",action='store_true',default=False)
	group.add_option("","--roi-dir",dest="roi_dir",help="ID of the subject ROI masks",type='string', default="")
	parser.add_option_group(group)

	#PVC options
	group= OptionGroup(parser,"Masking options","ROI for PVC")
	group.add_option("","--no-pvc",dest="pvcrun",help="Don't run PVC.",action='store_true',default=False)
	group.add_option("","--pvc-roi-user",dest="PVCMaskingType",help="User defined ROI for each subject",action='store_const',const='roi-user',default='civet')	
	group.add_option("","--pvc-roi-animal",dest="PVCMaskingType",help="Use ANIMAL segmentation",action='store_const',const='animal',default='animal')	
	group.add_option("","--pvc-roi-civet",dest="PVCMaskingType",help="Use PVE tissue classification from CIVET",action='store_const',const='civet',default='civet')
	group.add_option("","--pvc-roi-icbm152",dest="PVCMaskingType",help="Use an atlas defined on ICBM152 template",action='store_const',const='icbm152',default='icbm152')
	group.add_option("","--pvc-roi-atlas",dest="PVCMaskingType",help="Use atlas based on template, both provided by user",action='store_const',const='atlas',default='civet')	
	group.add_option("","--pvc-roi-labels",dest="PVCAtlasLabels",help="Label value(s) for segmentation.",type='string',action='callback',callback=get_opt_list,default=None)

	group.add_option("","--pvc-roi-template",dest="pvcTemplate",help="Template to segment the ROI.",default=icbm152)
	group.add_option("","--pvc-roi-mask",dest="pvcMask",help="ROI mask on the template",default=default_atlas)	
	group.add_option("","--pvc-roi-template-suffix",dest="templatePVCSuffix",help="Suffix for the ROI template.",default='icbm152')
	group.add_option("","--pvc-roi-suffix",dest="pvcSuffix",help="PVC suffix",default='striatal_6lbl')	
	group.add_option("","--pvc-roi-dir",dest="pvc_roi_dir",help="ID of the subject ROI masks",type='string', default="")

	group.add_option("","--pvc-method",dest="pvc_method",help="Method for PVC.",type='string', default="GTM")
	group.add_option("","--pet-scanner",dest="pet_scanner",help="FWHM of PET scanner.",type='str', default=None)
	group.add_option("","--pvc-fwhm",dest="scanner_fwhm",help="FWHM of PET scanner.",type='float', default=None)
	group.add_option("","--pvc-max-iterations",dest="max_iterations",help="Maximum iterations for PVC method.",type='int', default=10)
	group.add_option("","--pvc-tolerance",dest="tolerance",help="Tolerance for PVC algorithm.",type='float', default=0.001)
	group.add_option("","--pvc-lambda",dest="lambda_var",help="Lambda for PVC algorithm (smoothing parameter for anisotropic diffusion)",type='float', default=1)
	group.add_option("","--pvc-denoise-fwhm",dest="denoise_fwhm",help="FWHM of smoothing filter.",type='float', default=1)
	group.add_option("","--pvc-nvoxel-to-average",dest="nvoxel_to_average",help="Number of voxels to average over.",type='int', default=64)
	parser.add_option_group(group)

	#TKA Options
	group= OptionGroup(parser,"Tracer Kinetic analysis options")
	group.add_option("","--tka-method",dest="tka_method",help="Method for performing tracer kinetic analysis (TKA): lp, pp, srtm.",type='string', default=None)
	group.add_option("","--k2",dest="tka_k2",help="With reference region input it may be necessary to specify also the population average for regerence region k2",type='float', default=None)
	group.add_option("","--thr",dest="tka_thr",help="Pixels with AUC less than (threshold/100 x max AUC) are set to zero. Default is 0%",type='float', default=None)
	group.add_option("","--max",dest="tka_max",help="Upper limit for Vt or DVR values; by default max is set pixel-wise to 10 times the AUC ratio.",type='float', default=None)
	group.add_option("","--min",dest="tka_min",help="Lower limit for Vt or DVR values, 0 by default",type='float', default=None)
	group.add_option("","--t3max",dest="tka_t3max",help="Upper limit for theta3, 0.01 by default",type='float', default=0.01)
	group.add_option("","--t3min",dest="tka_t3min",help="Lower limit for theta3, 0.001 by default",type='float', default=0.001)
	group.add_option("","--nBF",dest="tka_nBF",help="Number of basis functions.",type='int', default=100)
	group.add_option("","--filter",dest="tka_filter",help="Remove parametric pixel values that over 4x higher than their closest neighbours.",action='store_const',const=True, default=None)
	group.add_option("","--reg-end",dest="tka_end",help="By default line is fit to the end of data. Use this option to enter the fit end time (in min).",type='float', default=None)
	group.add_option("","--y-int",dest="tka_v",help="Y-axis intercepts time -1 are written as an image to specified file.",type='string', default=None)
	group.add_option("","--num",dest="tka_n",help="Numbers of selected plot data points are written as an image.",type='string', default=None)
	group.add_option("","--Ca",dest="tka_Ca",help="Concentration of native substrate in arterial plasma (mM).",type='float', default=None)
	group.add_option("","--LC",dest="tka_LC",help="Lumped constant in MR calculation; default is 1.0.",type='float', default=None)
	group.add_option("","--density",dest="tka_density",help="Tissue density in MR calculation; default is 1.0 g/ml.",type='float', default=None)
	group.add_option("","--arterial",dest="tka_arterial",help="Use arterial input input.",action='store_const', const=True, default=False)
	group.add_option("","--start-time",dest="tka_start_time",help="Start time for regression in MTGA.",type='float', default=None)
	group.add_option("","--tka-type",dest="tka_type",help="Type of tka analysis: voxel or ROI.",type='string', default=None)
	parser.add_option_group(group)

	group= OptionGroup(parser,"Command control")
	group.add_option("-v","--verbose",dest="verbose",help="Write messages indicating progress.",action='store_true',default=False)
	parser.add_option_group(group)

	group= OptionGroup(parser,"Pipeline control")
	group.add_option("","--run",dest="prun",help="Run the pipeline.",action='store_true',default=False)
	group.add_option("","--fake",dest="prun",help="do a dry run, (echo cmds only).",action='store_false',default=False)
	group.add_option("","--print-scan",dest="pscan",help="Print the pipeline parameters for the scan.",action='store_true',default=False)
	group.add_option("","--print-stages",dest="pstages",help="Print the pipeline stages.",action='store_true',default=False)
	parser.add_option_group(group)

	(opts, args) = parser.parse_args()

	opts.extension='mnc'

	
	##########################################################
	# Check inputs to make sure there are no inconsistencies #
	##########################################################

	if not opts.sourceDir or not opts.targetDir or not opts.civetDir or not opts.prefix:
		print "\n\n*******ERROR******** \n     You must specify --sourcedir, --targetdir, --civetdir  and --prefix \n********************\n"
		parser.print_help()
		sys.exit(1)

	#Check inputs for ROI masking
	check_masking_options(opts.ROIMaskingType, opts.roi_dir, opts.RoiSuffix, opts.ROIMask, opts.ROITemplate)
	#Check inputs for REF masking
	check_masking_options(opts.RefMaskingType, opts.ref_dir, opts.refSuffix, opts.refMask, opts.RefTemplate)
	#Check inputs for PVC masking
	check_masking_options(opts.PVCMaskingType, opts.pvc_roi_dir, opts.pvcSuffix, opts.pvcMask, opts.pvcTemplate)

	#Set default labels for ROI mask
	if(opts.ROIAtlasLabels ==None): opts.ROIAtlasLabels=roi_labels["ROI"][opts.ROIMaskingType]
	#If no labels given by user, set default labels for Ref mask
	if(opts.RefAtlasLabels ==None): opts.RefAtlasLabels=roi_labels["REF"][opts.RefMaskingType]
	#If no labels given by user, set default labels for PVC mask
	if(opts.PVCAtlasLabels ==None): opts.PVCAtlasLabels=roi_labels["PVC"][opts.PVCMaskingType]


	
    ###Check PVC options and set defaults if necessary
	if opts.scanner_fwhm == None and opts.pet_scanner == None:
		print "Error: You must either\n\t1) set the desired FWHM of the PET scanner using the \"--scanner_fwhm <float>\" option, or"
		print "\t2) set the PET scanner type using the \"--pet-scanner <string>\" option."
		print "\tSupported PET scanners to date are the " + ', '.join(pet_scanners.keys())
		exit(1)
	if not opts.pet_scanner == None:
		if opts.pet_scanner in pet_scanners.keys():
			opts.scanner_fwhm = pet_scanners[opts.pet_scanner]
		else:
			print "Error: The PET scanner \"" + opts.pet_scanner + "\"is not supported. You can"
			print "\t1) add this PET scanner to the \"PET_scanner.json\" file, or"
			print "\t2) set the FWHM of the scanner manually using the \"--scanner_fwhm <float>\" option."
			exit(1)

	opts.targetDir = os.path.normpath(opts.targetDir)
	opts.sourceDir = os.path.normpath(opts.sourceDir)
	opts.civetDir = os.path.normpath(opts.civetDir)


#	if opts.prun:
#		runPipeline(opts,args)
#	elif opts.pscan:
#		printScan(opts,args)
#	elif opts.pstages:
#		printStages(opts,args)
#	else:
#		print "\n\n*******ERROR********: \n    The options -run, -print-scan or print-stages need to be chosen \n********************\n\n"
#		parser.print_help()
#		sys.exit(1)

	if opts.pscan:
		printScan(opts,args)
	elif opts.pstages:
		printStages(opts,args)
	else:
		runPipeline(opts,args)
