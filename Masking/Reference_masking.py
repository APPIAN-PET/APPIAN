#!/usr/bin/env python

import os
import argparse
import commands
import shutil
import tempfile
import nipype.interfaces.minc as minc
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
from nipype.interfaces.utility import Rename
import os


# version = "1.0"


tmpdir = tempfile.mkdtemp()

def stage_RefMasking_v1(scan,opts):

	class getRefLabels:
		def __init__(self,label1,label2):
			self.label1=label1
			self.label2=label2


	if not opts.refRegister and opts.refOnTemplate:
		# minc.resample()
		cmd=' '.join(['mincresample',opts.refOnTemplate,scan.tal_ref,'-like',scan.tal,'-clobber'])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	elif opts.templateRef and opts.refOnTemplate:
		cmd=' '.join(['best1stepnlreg.pl','-source_mask',opts.refOnTemplate,'-normalize','-target_mask',scan.t1_brainmask,opts.templateRef,scan.tal,scan.xfm_tal_ref,'-clobber'])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
		cmd=' '.join(['mincresample',opts.refOnTemplate,scan.tal_ref,'-like',scan.tal,'-transformation',scan.talscan.xfm_tal_ref,'-clobber'])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	else:
		mask=tmpdir+os.sep+"mask.mnc"
		animal = getRefLabels(opts.refValueAnimal[0],opts.refValueAnimal[1])
		# expression="if(A[0]=="+animal.label1+" || A[0]=="+animal.label2+"){out=1;}else:{out=0;}"
		expression="'if(A[0]=="+animal.label1+" || A[0]=="+animal.label2+"){out=1;}else{out=0;}'"

		cmd=' '.join(['minccalc','-expression',expression,scan.tal_animal_masked,mask])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)

	maskClean=tmpdir+os.sep+"maskClean.mnc"
	if opts.refClose:
		cmd=' '.join(['mincmorph',mask,maskClean,'-successive',"CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",'-verbose'])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	else:
		maskClean = mask

	maskClassified=tmpdir+os.sep+"maskClassified.mnc"
	if opts.refMatter == 'gm':
		expression="'if(A[0]==0){out=0;}else:{if(A[1]<=1 && A[1]>0){out=1;}else:{out=0}}'"
		cmd=' '.join(['minccalc','-expression',expression,maskClean,scan.tal_pve_gm,maskClassified])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	elif opts.refMatter == 'wm':
		expression='if(A[0]==0){out=0;}else:{if(A[1]<=1 && A[1]>0){out=1;}else:{out=0}}'
		cmd=' '.join(['minccalc','-expression',expression,maskClean,scan.tal_pve_wm,maskClassified])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	else:
		maskClassified = maskClean

	cmd=' '.join(['cp',maskClassified,scan.tal_ref])
	if opts.pfake:
		print(cmd+'\n')
	else:
		commands.getoutput(cmd)



def stage_RefMasking_v2(scan,opts):

	class getRefLabels:
		def __init__(self,label1,label2):
			self.label1=label1
			self.label2=label2


	if not opts.refRegister and opts.refOnTemplate:
		# minc.resample()
		cmd=' '.join(['mincresample',opts.refOnTemplate,scan.tal_ref,'-like',scan.tal,'-clobber'])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	elif opts.templateRef and opts.refOnTemplate:
		# cmd=' '.join(['best1stepnlreg.pl','-source_mask',opts.refOnTemplate,'-normalize','-target_mask',scan.t1_brainmask,opts.templateRef,scan.tal,scan.xfm_tal_ref,'-clobber'])
		cmd=' '.join(['python bestlinreg_pet2mri.py',opts.templateRef,scan.tal,scan.xfm_tal_ref,'-source_mask',opts.refOnTemplate,'-normalize','-target_mask',scan.t1_brainmask,'-clobber'])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
		cmd=' '.join(['mincresample',opts.refOnTemplate,scan.tal_ref,'-like',scan.tal,'-transformation',scan.talscan.xfm_tal_ref,'-clobber'])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	else:
		mask=tmpdir+os.sep+"mask.mnc"
		animal = getRefLabels(opts.refValueAnimal[0],opts.refValueAnimal[1])
		# expression="if(A[0]=="+animal.label1+" || A[0]=="+animal.label2+"){out=1;}else:{out=0;}"
		expression="'if(A[0]=="+animal.label1+" || A[0]=="+animal.label2+"){out=1;}else{out=0;}'"

		cmd=' '.join(['minccalc','-expression',expression,scan.tal_animal_masked,mask])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)

	maskClean=tmpdir+os.sep+"maskClean.mnc"
	if opts.refClose:
		cmd=' '.join(['mincmorph',mask,maskClean,'-successive',"CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",'-verbose'])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	else:
		maskClean = mask

	maskClassified=tmpdir+os.sep+"maskClassified.mnc"
	if opts.refMatter == 'gm':
		expression="'if(A[0]==0){out=0;}else:{if(A[1]<=1 && A[1]>0){out=1;}else:{out=0}}'"
		cmd=' '.join(['minccalc','-expression',expression,maskClean,scan.tal_pve_gm,maskClassified])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	elif opts.refMatter == 'wm':
		expression='if(A[0]==0){out=0;}else:{if(A[1]<=1 && A[1]>0){out=1;}else:{out=0}}'
		cmd=' '.join(['minccalc','-expression',expression,maskClean,scan.tal_pve_wm,maskClassified])
		if opts.pfake:
			print(cmd+'\n')
		else:
			commands.getoutput(cmd)
	else:
		maskClassified = maskClean

	cmd=' '.join(['cp',maskClassified,scan.tal_ref])
	if opts.pfake:
		print(cmd+'\n')
	else:
		commands.getoutput(cmd)




		



# if __name__ == '__main__':
# 	usage = "usage: %prog "

# 	parser = OptionParser(usage=usage,version=version)

# 	# Required options                    
# 	group= OptionGroup(parser,"Required arguments"," ")
# 	group.add_option("-animal", "-animal", dest="animal", help="Use ANIMAL segmentation")
# 	group.add_option("-gm", "-gm", dest="matter", help="Only gray matter")
# 	group.add_option("-wm", "-wm", dest="matter", help="Only white matter")
# 	group.add_option("-linreg", "-linreg", dest="register", help="Non-linear registration based segmentation", action='store_true')
# 	group.add_option("-no-linreg", "-no-linreg", dest="register", help="Don't run any non-linear registration", action='store_false')
# 	group.add_option("-close", "-close", dest="matter", help="Close - erosion(dialtion(X))")

# 	# Others options
# 	group= OptionGroup(parser,"Optional arguments"," ")
# 	group.add_option("-verbose", "-verbose", dest="verbose", help="be verbose", action="store_true")
# 	group.add_option("-clobber", "-clobber", dest="clobber", help='clobber existing check files', action="store_true")
# 	group.add_option("-temp", "-temp", dest="tempDir", help='User temporary directory', type=str)
# 	group.add_option("-fake", "-fake", dest="fake", help='do a dry run, (echo cmds only)', action="store_true")

# 	parser.add_option_group(group)
# 	(opts, args) = parser.parse_args()

# 	id=args

	

# 	if opts.tempDir:
# 		tmpdir = args.tempDir




