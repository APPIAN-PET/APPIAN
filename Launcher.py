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
	print "* PET conditions : "+ ','.join(opts.condiList)+"\n"
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

#	subjects_ids=["%03d" % subjects_ids[subjects_ids.index(subj)] for subj in subjects_ids]
	conditions_ids=list(range(len(opts.condiList)))
	conditions_ids=opts.condiList

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
	datasourceRaw = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'sid', 'cid'], 
													   outfields=['pet'], sort_filelist=False), name="datasourceRaw")
	datasourceRaw.inputs.base_directory = opts.sourceDir
	datasourceRaw.inputs.template = '*'
	datasourceRaw.inputs.field_template = dict(pet='%s/%s_%s_%s_pet.mnc')
	datasourceRaw.inputs.template_args = dict(pet=[['study_prefix', 'study_prefix', 'sid', 'cid']])	

	#Subject ROI datasource
	
	if os.path.exists(opts.roi_dir):
		datasourceROI = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'sid', 'RoiSuffix'], 
														   outfields=['subjectROI'], sort_filelist=False), name="datasourceROI")
		datasourceROI.inputs.base_directory = opts.roi_dir
		datasourceROI.inputs.template = '*'
		datasourceROI.inputs.field_template = dict(subjectROI='%s_%s_%s.mnc')
		datasourceROI.inputs.template_args = dict(subjectROI=[['study_prefix', 'sid', 'RoiSuffix']])	

	#CIVET datasource
	datasourceCivet = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'sid'], 
														 outfields=['nativeT1', 'nativeT1nuc', 
														 			'talT1', 'xfmT1tal','xfmT1talnl',
														 			'brainmasktal', 'headmasktal', 'clsmask', 'animalmask'], 
														 sort_filelist=False), name="datasourceCivet")
	datasourceCivet.inputs.base_directory = opts.civetDir
	datasourceCivet.inputs.roi_dir = opts.roi_dir
	datasourceCivet.inputs.template = '*'
	datasourceCivet.inputs.field_template = dict(nativeT1='%s/%s/native/%s_%s_t1.mnc', 
												 nativeT1nuc='%s/%s/native/%s_%s_t1_nuc.mnc', 
												 talT1='%s/%s/final/%s_%s_t1_tal.mnc',
												 xfmT1tal='%s/%s/transforms/linear/%s_%s_t1_tal.xfm',
												 xfmT1talnl='%s/%s/transforms/nonlinear/%s_%s_nlfit_It.xfm',
												 brainmasktal='%s/%s/mask/%s_%s_brain_mask.mnc',
												 headmasktal='%s/%s/mask/%s_%s_skull_mask.mnc',
												 clsmask='%s/%s/classify/%s_%s_pve_classify.mnc',
												 animalmask='%s/%s/segment/%s_%s_animal_labels_masked.mnc'
												)
	datasourceCivet.inputs.template_args = dict(nativeT1=[['study_prefix', 'sid', 'study_prefix', 'sid']], 
										   		nativeT1nuc=[['study_prefix', 'sid', 'study_prefix', 'sid']], 
										   		talT1=[['study_prefix', 'sid', 'study_prefix', 'sid']], 
										   		xfmT1tal=[['study_prefix', 'sid', 'study_prefix', 'sid']], 
										   		xfmT1talnl=[['study_prefix', 'sid', 'study_prefix', 'sid']], 
										   		brainmasktal=[['study_prefix', 'sid', 'study_prefix', 'sid']], 										   		
										   		headmasktal=[['study_prefix', 'sid', 'study_prefix', 'sid']], 										   		
										   		clsmask=[['study_prefix', 'sid', 'study_prefix', 'sid']], 										   		
										   		animalmask=[['study_prefix', 'sid', 'study_prefix', 'sid']] 										   		
										   		)	

	##############
	###Datasink###
	##############
	datasink=pe.Node(interface=nio.DataSink(), name="output")
	datasink.inputs.base_directory= opts.targetDir + '/' +opts.prefix
	datasink.inputs.substitutions = [('_cid_', ''), ('sid_', '')]

	###########
	###Nodes###
	###########
	node_name="t1Masking"
	t1Masking = pe.Node(interface=masking.T1maskingRunning(), name=node_name)
	t1Masking.inputs.modelDir = opts.modelDir
	t1Masking.inputs.clobber = True
	t1Masking.inputs.verbose = opts.verbose
	t1Masking.inputs.run = opts.prun
	rT1MaskingHead=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"_head.mnc"), name="r"+node_name+"Head")
	rT1MaskingBrain=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"_brain.mnc"), name="r"+node_name+"Brain")

	node_name="refMasking"
	refMasking = pe.Node(interface=masking.RegionalMaskingRunning(), name=node_name)
	refMasking.inputs.MaskingType = opts.RefMaskingType
	# refMasking.inputs.modelDir = opts.RefTemplateDir
	refMasking.inputs.model = opts.RefTemplate
	refMasking.inputs.segLabels = opts.RefAtlasLabels
	refMasking.inputs.close = opts.RefClose
	refMasking.inputs.refGM = True if opts.RefMatter == 'gm' else False
	refMasking.inputs.refWM = True if opts.RefMatter == 'wm' else False
	refMasking.inputs.clobber = True
	refMasking.inputs.verbose = opts.verbose
	refMasking.inputs.run = opts.prun
	rRefMaskingTal=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"Tal.mnc"), name="r"+node_name+"Tal")
	rRefMaskingT1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"T1.mnc"), name="r"+node_name+"T1")
	rRefMaskingPET=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"PET.mnc"), name="r"+node_name+"PET")

	node_name="roiMasking"
	roiMasking = pe.Node(interface=masking.RegionalMaskingRunning(), name=node_name)
	roiMasking.inputs.MaskingType = opts.ROIMaskingType
	roiMasking.inputs.model = opts.ROITemplate
	roiMasking.inputs.segLabels = opts.ROIAtlasLabels
	# roiMasking.inputs.erosion = False
	roiMasking.inputs.clobber = True
	roiMasking.inputs.verbose = opts.verbose
	roiMasking.inputs.run = opts.prun
	rROIMaskingTal=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"Tal.mnc"), name="r"+node_name+"Tal")
	rROIMaskingT1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"T1.mnc"), name="r"+node_name+"T1")
	rROIMaskingPET=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"PET.mnc"), name="r"+node_name+"PET")


	node_name="pvcMasking"
	pvcMasking = pe.Node(interface=masking.RegionalMaskingRunning(), name=node_name)
	pvcMasking.inputs.MaskingType = opts.PVCMaskingType
	pvcMasking.inputs.model = opts.pvcTemplate
	pvcMasking.inputs.segLabels = opts.PVCAtlasLabels
	pvcMasking.inputs.clobber = True
	pvcMasking.inputs.verbose = opts.verbose
	pvcMasking.inputs.run = opts.prun
	rPVCMaskingTal=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"Tal.mnc"), name="r"+node_name+"Tal")
	rPVCMaskingT1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"T1.mnc"), name="r"+node_name+"T1")
	rPVCMaskingPET=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+"PET.mnc"), name="r"+node_name+"PET")


	node_name="petCenter"
	petCenter= pe.Node(interface=init.VolCenteringRunning(), name=node_name)
	petCenter.inputs.verbose = opts.verbose
	petCenter.inputs.run = opts.prun	
	rPetCenter=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petExcludeFr"
	petExFr = pe.Node(interface=init.PETexcludeFrRunning(), name=node_name)
	petExFr.inputs.verbose = opts.verbose	
	petExFr.inputs.run = opts.prun
	rPetExFr=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petVolume"
	petVolume = pe.Node(interface=minc.AverageCommand(), name=node_name)
	petVolume.inputs.avgdim = 'time'
	petVolume.inputs.width_weighted = True
	petVolume.inputs.clobber = True
	petVolume.inputs.verbose = opts.verbose	
	rPetVolume=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petSettings"
	petSettings = pe.Node(interface=init.MincHdrInfoRunning(), name=node_name)
	petSettings.inputs.verbose = opts.verbose
	petSettings.inputs.clobber = True
	petSettings.inputs.run = opts.prun
	rPetSettings=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petCenterSettings"
	petCenterSettings = pe.Node(interface=init.MincHdrInfoRunning(), name=node_name)
	petCenterSettings.inputs.verbose = opts.verbose
	petCenterSettings.inputs.clobber = True
	petCenterSettings.inputs.run = opts.prun
	rPetSettings=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petMasking"
	petMasking = pe.Node(interface=masking.PETheadMaskingRunning(), name=node_name)
	petMasking.inputs.verbose = opts.verbose
	petMasking.inputs.run = opts.prun
	rPetMasking=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="pet2mri"
	pet2mri = pe.Node(interface=reg.PETtoT1LinRegRunning(), name=node_name)
	pet2mri.inputs.clobber = True
	pet2mri.inputs.verbose = opts.verbose
	pet2mri.inputs.run = opts.prun
	rPet2MriImg=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name+"Img")
	rPet2MriXfm=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".xfm"), name="r"+node_name+"Xfm")


	node_name="petRefMask"
	petRefMask = pe.Node(interface=minc.ResampleCommand(), name=node_name)
	petRefMask.inputs.interpolation = 'nearest_neighbour'
	petRefMask.inputs.invert = 'invert_transformation'
	petRefMask.inputs.clobber = True

	rPetRefMask=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="GTM"
	gtmNode = pe.Node(interface=pvc.GTMCommand(), name=node_name)
	gtmNode.inputs.fwhm = opts.scanner_fwhm

	node_name="idSURF"
	idSURFNode = pe.Node(interface=pvc.idSURFCommand(), name=node_name)
	idSURFNode.inputs.fwhm = opts.scanner_fwhm
	idSURFNode.inputs.max_iterations = opts.max_iterations
	idSURFNode.inputs.tolerance = opts.tolerance
	idSURFNode.inputs.denoise_fwhm = opts.denoise_fwhm
	idSURFNode.inputs.lambda_var = opts.lambda_var
	idSURFNode.inputs.nvoxel_to_average=opts.nvoxel_to_average

	#Define list of output files. This will be passed to results report #
	out_node_list = [petCenter]
	out_img_list = ['out_file']



	workflow = pe.Workflow(name='preproc')
	workflow.base_dir = opts.targetDir

	workflow.connect([(infosource, datasourceRaw, [('sid', 'sid')]),
                      (infosource, datasourceRaw, [('cid', 'cid')]),
                      (infosource, datasourceRaw, [('study_prefix', 'study_prefix')]),
                      (infosource, datasourceCivet, [('sid', 'sid')]),
                      (infosource, datasourceCivet, [('study_prefix', 'study_prefix')]),
                	 ])
	if opts.ROIMaskingType == "roi-user":
		workflow.connect([(infosource, datasourceROI, [('study_prefix', 'study_prefix')]),
                 	  	  (infosource, datasourceROI, [('sid', 'sid')]),
                 	  	  (infosource, datasourceROI, [('RoiSuffix', 'RoiSuffix')])
                 	  	  ])


	workflow.connect([(datasourceCivet, t1Masking, [('nativeT1nuc', 'nativeT1')]), 
					  (datasourceCivet, t1Masking, [('xfmT1tal', 'LinT1TalXfm')]), 
					  (datasourceCivet, t1Masking, [('brainmasktal', 'brainmaskTal')])])

	workflow.connect([(t1Masking, rT1MaskingBrain, [('T1brainmask', 'in_file')])])
	workflow.connect([(t1Masking, rT1MaskingHead, [('T1headmask', 'in_file')])])

	workflow.connect([(infosource, rT1MaskingBrain, [('study_prefix', 'study_prefix')]),
					  (infosource, rT1MaskingBrain, [('sid', 'sid')]),
					  (infosource, rT1MaskingBrain, [('cid','cid')])])
	workflow.connect([(infosource, rT1MaskingHead, [('study_prefix', 'study_prefix')]),
	 				  (infosource, rT1MaskingHead, [('sid', 'sid')]),
	 				  (infosource, rT1MaskingHead, [('cid','cid')])])

	workflow.connect(rT1MaskingBrain, 'out_file', datasink, t1Masking.name+"Head")
	workflow.connect(rT1MaskingHead, 'out_file', datasink, t1Masking.name+"Brain")


	############################
	# Connect PET volume nodes #
	############################

    #Connect PET to PET volume
	workflow.connect([(datasourceRaw, petCenter, [('pet', 'in_file')])])

	#Connect pet from petVolume to its rename node
	workflow.connect([(petCenter, rPetCenter, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetCenter, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetCenter, [('sid', 'sid')]),
                      (infosource, rPetCenter, [('cid', 'cid')])
                    ])

	workflow.connect(rPetCenter, 'out_file', datasink, petCenter.name)

	workflow.connect([(petCenter, petCenterSettings, [('out_file', 'in_file')])])

	workflow.connect([(petCenter, petExFr, [('out_file', 'in_file')])])
	
	workflow.connect([(petExFr, rPetExFr, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetExFr, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetExFr, [('sid', 'sid')]),
                      (infosource, rPetExFr, [('cid', 'cid')])
                    ])

	workflow.connect(rPetExFr, 'out_file', datasink, petExFr.name)

	workflow.connect([(petExFr, petVolume, [('out_file', 'in_file')])])

	#Connect pet from petVolume to its rename node
	workflow.connect([(petVolume, rPetVolume, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetVolume, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetVolume, [('sid', 'sid')]),
                      (infosource, rPetVolume, [('cid', 'cid')])
                    ])

	workflow.connect(rPetVolume, 'out_file', datasink, petVolume.name)


    #
	workflow.connect([(datasourceRaw, petSettings, [('pet', 'in_file')])])
	workflow.connect([(petVolume, petMasking, [('out_file', 'in_file')]),
	                  (petSettings, petMasking, [('out_file','in_json')])
                    ])
	


	#
	#
	workflow.connect([(petMasking, rPetMasking, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetMasking, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetMasking, [('sid', 'sid')]),
                      (infosource, rPetMasking, [('cid', 'cid')])
                    ])

	workflow.connect(rPetMasking, 'out_file', datasink, petMasking.name)

    #
	workflow.connect([(petVolume, pet2mri, [('out_file', 'in_source_file' )]),
                      (petMasking, pet2mri, [('out_file', 'in_source_mask')]), 
                      (t1Masking, pet2mri, [('T1headmask',  'in_target_mask')]),
                      (datasourceCivet, pet2mri, [('nativeT1nuc', 'in_target_file')])
                      ]) 
    #
	workflow.connect([(pet2mri, rPet2MriImg, [('out_file_img', 'in_file')])])
	workflow.connect([(infosource, rPet2MriImg, [('study_prefix', 'study_prefix')]),
                      (infosource, rPet2MriImg, [('sid', 'sid')]),
                      (infosource, rPet2MriImg, [('cid', 'cid')])
                    ])

	workflow.connect([(pet2mri, rPet2MriXfm, [('out_file_xfm', 'in_file')])])
	workflow.connect([(infosource, rPet2MriXfm, [('study_prefix', 'study_prefix')]),
                      (infosource, rPet2MriXfm, [('sid', 'sid')]),
                      (infosource, rPet2MriXfm, [('cid', 'cid')])
                    ])

	workflow.connect(rPet2MriXfm, 'out_file', datasink, pet2mri.name+"Xfm")
	workflow.connect(rPet2MriImg, 'out_file', datasink, pet2mri.name+"Img")

	##################################
	# Connect regional masking nodes #
	##################################
	workflow.connect([(datasourceCivet, roiMasking, [('nativeT1nuc','nativeT1')]),
                      (datasourceCivet, roiMasking, [('talT1','T1Tal')]),
                      (datasourceCivet, roiMasking, [('xfmT1tal','LinT1TalXfm')]),
                      (datasourceCivet, roiMasking, [('brainmasktal','brainmaskTal' )]),
                      (datasourceCivet, roiMasking, [('clsmask','clsmaskTal')]),
                      (datasourceCivet, roiMasking, [('animalmask','segMaskTal' )])
                    ])

	if opts.ROIMaskingType == "roi-user":
		workflow.connect([(datasourceROI, roiMasking, [('subjectROI','ROIMask')]) ])	
	elif opts.ROIMaskingType in [ "animal" ]:
		workflow.connect([(datasourceCivet, roiMasking, [('animalmask','ROIMask')]) ]) 
	elif opts.ROIMaskingType in [ "civet" ]:
		workflow.connect([(datasourceCivet, roiMasking, [('clsmask','ROIMask')]) ])
	elif opts.ROIMaskingType in [ "icbm152", "atlas"] :
		roiMasking.inputs.ROIMask=opts.ROIMask


	workflow.connect([(petVolume, roiMasking, [('out_file','PETVolume')]) ])
	workflow.connect([(rPet2MriXfm, roiMasking, [('out_file','pet2mriXfm')]) ])

    #Connect RegionalMaskTal from roiMasking to rename node
	workflow.connect([(roiMasking, rROIMaskingTal, [('RegionalMaskTal', 'in_file')])])
	workflow.connect([(infosource, rROIMaskingTal, [('study_prefix', 'study_prefix')]),
                      (infosource, rROIMaskingTal, [('sid', 'sid')]),
                      (infosource, rROIMaskingTal, [('cid', 'cid')])
                    ])

    #Connect RegionalMaskT1 from roiMasking to rename node
	workflow.connect([(roiMasking, rROIMaskingT1, [('RegionalMaskT1', 'in_file')])])
	workflow.connect([(infosource, rROIMaskingT1, [('study_prefix', 'study_prefix')]),
                      (infosource, rROIMaskingT1, [('sid', 'sid')]),
                      (infosource, rROIMaskingT1, [('cid', 'cid')])
                    ])

    #Connect RegionalMaskPET from roiMasking to rename node
	workflow.connect([(roiMasking, rROIMaskingPET, [('RegionalMaskPET', 'in_file')])])
	workflow.connect([(infosource, rROIMaskingPET, [('study_prefix', 'study_prefix')]),
                      (infosource, rROIMaskingPET, [('sid', 'sid')]),
                      (infosource, rROIMaskingPET, [('cid', 'cid')])
                    ])

	workflow.connect(rROIMaskingT1, 'out_file', datasink, roiMasking.name+"T1")
	workflow.connect(rROIMaskingTal, 'out_file', datasink, roiMasking.name+"Tal")
	workflow.connect(rROIMaskingPET, 'out_file', datasink, roiMasking.name+"PET")

	###################################
	# Connect nodes for reference ROI #
	###################################

 	workflow.connect([(petVolume, refMasking, [('out_file','PETVolume')]) ])
	workflow.connect([(rPet2MriXfm, refMasking, [('out_file','pet2mriXfm')]) ])

	workflow.connect(rRefMaskingT1, 'out_file', datasink, refMasking.name+"T1")
	workflow.connect(rRefMaskingTal, 'out_file', datasink, refMasking.name+"Tal")


	workflow.connect([(datasourceCivet, refMasking, [('nativeT1nuc','nativeT1')]),
                      (datasourceCivet, refMasking, [('talT1','T1Tal')]),
                      (datasourceCivet, refMasking, [('xfmT1tal','LinT1TalXfm')]),
                      (datasourceCivet, refMasking, [('brainmasktal','brainmaskTal' )]),
                      (datasourceCivet, refMasking, [('clsmask','clsmaskTal')]),
                      (datasourceCivet, refMasking, [('animalmask','segMaskTal' )])
                    ])
  
	if opts.RefMaskingType == "roi-user":
		workflow.connect([(datasourceROI, refMasking, [('subjectROI','ROIMask')]) ])	
	elif opts.RefMaskingType in [ "animal" ]:
		workflow.connect([(datasourceCivet, refMasking, [('animalmask','ROIMask')]) ]) 
	elif opts.RefMaskingType in [ "civet" ]:
		workflow.connect([(datasourceCivet, refMasking, [('clsmask','ROIMask')]) ])
	elif opts.RefMaskingType in [ "icbm152", "atlas"] :
		refMasking.inputs.ROIMask=opts.ROIMask

    #Connect RegionalMaskTal from refMasking to rename node
	workflow.connect([(refMasking, rRefMaskingTal, [('RegionalMaskTal', 'in_file')])])
	workflow.connect([(infosource, rRefMaskingTal, [('study_prefix', 'study_prefix')]),
                      (infosource, rRefMaskingTal, [('sid', 'sid')]),
                      (infosource, rRefMaskingTal, [('cid', 'cid')])
                    ])	

  	#Connect RegionalMaskT1 from refMasking to rename node
	workflow.connect([(refMasking, rRefMaskingT1, [('RegionalMaskT1', 'in_file')])])
	workflow.connect([(infosource, rRefMaskingT1, [('study_prefix', 'study_prefix')]),
                      (infosource, rRefMaskingT1, [('sid', 'sid')]),
                      (infosource, rRefMaskingT1, [('cid', 'cid')])
                    ])

  	#Connect RegionalMaskT1 from refMasking to rename node
	workflow.connect([(refMasking, rRefMaskingPET, [('RegionalMaskT1', 'in_file')])])
	workflow.connect([(infosource, rRefMaskingPET, [('study_prefix', 'study_prefix')]),
                      (infosource, rRefMaskingPET, [('sid', 'sid')]),
                      (infosource, rRefMaskingPET, [('cid', 'cid')])
                    ])

                        #
	workflow.connect([(refMasking, petRefMask, [('RegionalMaskT1', 'in_file' )]),
                      (petVolume, petRefMask, [('out_file', 'model_file')]), 
                      (pet2mri, petRefMask, [('out_file_xfm', 'transformation')])
                      ]) 

	workflow.connect([(petRefMask, rPetRefMask, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetRefMask, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetRefMask, [('sid', 'sid')]),
                      (infosource, rPetRefMask, [('cid', 'cid')])
                    ])

	workflow.connect(rPetRefMask, 'out_file', datasink, petRefMask.name)
	#############################
	# Connect nodes for PVC ROI #
	#############################
	workflow.connect([(datasourceCivet, pvcMasking, [('nativeT1nuc','nativeT1')]),
                      (datasourceCivet, pvcMasking, [('talT1','T1Tal')]),
                      (datasourceCivet, pvcMasking, [('xfmT1tal','LinT1TalXfm')]),
                      (datasourceCivet, pvcMasking, [('brainmasktal','brainmaskTal' )]),
                      (datasourceCivet, pvcMasking, [('clsmask','clsmaskTal')]),
                      (datasourceCivet, pvcMasking, [('animalmask','segMaskTal' )])
                    ])


	if opts.PVCMaskingType == "roi-user":
		workflow.connect([(datasourceROI, pvcMasking, [('subjectROI','ROIMask')]) ])	
	elif opts.PVCMaskingType in [ "animal" ]:
		workflow.connect([(datasourceCivet, pvcMasking, [('animalmask','ROIMask')]) ]) 
	elif opts.PVCMaskingType in [ "civet" ]:
		workflow.connect([(datasourceCivet, pvcMasking, [('clsmask','ROIMask')]) ])
	elif opts.PVCMaskingType in [ "icbm152", "atlas"] :
		pvcMasking.inputs.ROIMask=opts.ROIMask

	workflow.connect([(petVolume, pvcMasking, [('out_file','PETVolume')]) ])
	workflow.connect([(rPet2MriXfm, pvcMasking, [('out_file','pet2mriXfm')]) ])

    #Connect RegionalMaskTal from roiMasking to rename node
	workflow.connect([(pvcMasking, rPVCMaskingTal, [('RegionalMaskTal', 'in_file')])])
	workflow.connect([(infosource, rPVCMaskingTal, [('study_prefix', 'study_prefix')]),
                      (infosource, rPVCMaskingTal, [('sid', 'sid')]),
                      (infosource, rPVCMaskingTal, [('cid', 'cid')])
                    ])

    #Connect RegionalMaskT1 from pvcMasking to rename node
	workflow.connect([(pvcMasking, rPVCMaskingT1, [('RegionalMaskT1', 'in_file')])])
	workflow.connect([(infosource, rPVCMaskingT1, [('study_prefix', 'study_prefix')]),
                      (infosource, rPVCMaskingT1, [('sid', 'sid')]),
                      (infosource, rPVCMaskingT1, [('cid', 'cid')])
                    ])

    #Connect RegionalMaskPET from pvcMasking to rename node
	workflow.connect([(pvcMasking, rPVCMaskingPET, [('RegionalMaskPET', 'in_file')])])
	workflow.connect([(infosource, rPVCMaskingPET, [('study_prefix', 'study_prefix')]),
                      (infosource, rPVCMaskingPET, [('sid', 'sid')]),
                      (infosource, rPVCMaskingPET, [('cid', 'cid')])
                    ])
	workflow.connect(rPVCMaskingT1, 'out_file', datasink, pvcMasking.name+"T1")
	workflow.connect(rPVCMaskingTal, 'out_file', datasink, pvcMasking.name+"Tal")
	workflow.connect(rPVCMaskingPET, 'out_file', datasink, pvcMasking.name+"PET")



	#############################
	# Partial-volume correction #
	#############################
	pvcnode = pe.Node(niu.IdentityInterface(fields=["pvc"]), name='pvc')

	workflow.connect([(rPetCenter, gtmNode, [('out_file','input_file')]),
				  (pvcMasking, gtmNode, [('RegionalMaskPET','mask')])
				  ])
	workflow.connect(gtmNode, 'out_file', datasink, gtmNode.name)
	if opts.pvc_method == "GTM":
		workflow.connect(gtmNode, 'out_file', pvcnode, "pvc")
		out_node_list += [gtmNode]
		out_img_list += ['out_file']


	if opts.pvc_method == "idSURF":
		workflow.connect([(gtmNode, idSURFNode, [('out_file','first_guess')]),
						(rPetCenter, idSURFNode, [('out_file','input_file')]),
					  	(pvcMasking, idSURFNode, [('RegionalMaskPET','mask')])
    				  	])
		workflow.connect(idSURFNode, 'out_file', datasink, idSURFNode.name)
		workflow.connect(idSURFNode, 'out_file', pvcnode, "pvc")
		out_node_list += [idSURFNode]
		out_img_list += ['out_file']



	###########################
	# Tracer kinetic analysis #
	###########################
	if not opts.tka_method == None:
		#Perform TKA on uncorrected PET
		#["in_file", "header", "reference", "mask", "out_file"]
		tka_pve=tka.get_tka_workflow("tka_pve", opts)
		workflow.connect(refMasking, 'RegionalMaskPET', tka_pve, "inputnode.reference")
		workflow.connect(petCenterSettings, 'header', tka_pve, "inputnode.header")
		workflow.connect(roiMasking, 'RegionalMaskPET', tka_pve, "inputnode.mask")
		workflow.connect(petCenter, 'out_file', tka_pve, "inputnode.in_file")



		workflow.connect(tka_pve, 'outputnode.out_file', datasink, tka_pve.name)
		out_node_list += [tka_pve]
		out_img_list += ['outputnode.out_file']
		if not opts.pvc_method == None:
			#Perform TKA on PVC PET
			tka_pvc=tka.get_tka_workflow("tka_pvc", opts)
			workflow.connect(refMasking, 'RegionalMaskPET', tka_pvc, "inputnode.reference")
			workflow.connect(petCenterSettings, 'header', tka_pvc, "inputnode.header")
			workflow.connect(roiMasking, 'RegionalMaskPET', tka_pvc, "inputnode.mask")
			workflow.connect(pvcnode, 'pvc', tka_pvc, "inputnode.in_file")
			workflow.connect(tka_pvc, "outputnode.out_file", datasink, tka_pvc.name)
			out_node_list += [tka_pvc]
			out_img_list += ['outputnode.out_file']


	#######################################
	# Connect nodes for reporting results #
	#######################################
	#Results report for PET
	for node, img in zip(out_node_list, out_img_list):

		node_name="results_" + node.name
		resultsReport = pe.Node(interface=results.groupstatsCommand(), name=node_name)

		rresultsReport=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(sid)s_%(cid)s_"+node_name+".csv"), name="r"+node_name)


		workflow.connect([(node, resultsReport, [(img,'image')]),
						  (roiMasking, resultsReport, [('RegionalMaskPET','vol_roi')])
	    				  ])
		
		workflow.connect([(resultsReport, rresultsReport, [('out_file', 'in_file')])])
		workflow.connect([(infosource, rresultsReport, [('study_prefix', 'study_prefix')]),
	                      (infosource, rresultsReport, [('sid', 'sid')]),
	                      (infosource, rresultsReport, [('cid', 'cid')])
	                    ])
		workflow.connect(rresultsReport, 'out_file', datasink,resultsReport.name )

	


	printOptions(opts,subjects_ids)

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
		print "\n\n*******ERROR******** \n     You must specify -sourcedir, -targetdir, -civetdir  and -prefix \n********************\n"
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
		print "\t2) set the PET scanner type using the \"--pet_scanner <string>\" option."
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
