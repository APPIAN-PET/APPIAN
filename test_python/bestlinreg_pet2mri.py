#!/usr/bin/env python

# Import required modules
import os
import argparse
import commands
import shutil
import tempfile


# Change to script directory
cwd = os.path.realpath(os.path.curdir)
scriptDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(scriptDir)


tmpdir = tempfile.mkdtemp()
# shutil.rmtree(dirpath)
#-------------------------------------------- PARSER --------------------------------------------#

parser = argparse.ArgumentParser(description='Script to run bestlinreg')

# Required options                    
reqoptions = parser.add_argument_group('Required arguments')
reqoptions.add_argument("source", type=str, help='Source image' )
reqoptions.add_argument("target", type=str, help='Target image' )
reqoptions.add_argument("outxfm", type=str, help='Output xfm' )
reqoptions.add_argument("outfile", type=str, help='Output image' )


# Others options
optoptions = parser.add_argument_group('Optional arguments')
optoptions.add_argument("-verbose", dest="verbose", help="be verbose", action="store_true")
optoptions.add_argument('-clobber', dest="clobber", help='clobber existing check files', action="store_true")
optoptions.add_argument('-temp', dest="tempDir", help='User temporary directory', type=str)
optoptions.add_argument('-fake', dest="fake", help='do a dry run, (echo cmds only)', action="store_true")
optoptions.add_argument('-init_xfm"', dest="init_xfm", help='initial transformation (default identity)', type=str)
optoptions.add_argument('-source_mask"', dest="source_mask", help='PET mask', type=str)
optoptions.add_argument('-target_mask"', dest="target_mask", help='MRI mask', type=str)
optoptions.add_argument('-roi"', dest="roi_mask", help='Regions Of Interest mask', type=str)
optoptions.add_argument('-lsq6', dest="lsqtype", help='use 6-parameter transformation', action='store_const', const="-lsq6", default="-lsq6")
optoptions.add_argument('-lsq9', dest="lsqtype", help='use 9-parameter transformation', action='store_const', const="-lsq9", default="-lsq6")
optoptions.add_argument('-lsq12', dest="lsqtype", help='use 12-parameter transformation', action='store_const', const="-lsq12", default="-lsq6")
optoptions.add_argument('-fwhm_init"', dest="fwhm_init", help='Full Width Half Maximum for initial smoothing (HR PET data)', type=str)


args = parser.parse_args()

source = args.source
target = args.target
outxfm = args.outxfm
outfile = args.outfile

abandon=False
if not source or not target:
	print 'No source and target images specified.'
	abandon=True

if abandon:
	print '\n----------------------------- CANCELED -----------------------------\n'
	exit()
 
if args.tempDir:
	tmpdir = args.tempDir

prev_xfm = None
if args.init_xfm:
	prev_xfm = args.init_xfm



if args.source_mask and args.target_mask:
	if os.path.isfile(args.source_mask):
		source_masked = tmpdir+"/s_base_masked.mnc"
		cmd=' '.join(['minccalc', '-clobber', '-expression', "'if(A[1]>0.5){out=A[0];}else{out=A[1];}'", source, args.source_mask, source_masked])
		if args.verbose:
			print(cmd)
		commands.getoutput(cmd)

	if os.path.isfile(args.target_mask):
		target_masked = tmpdir+"/t_base_masked.mnc"
		cmd=' '.join(['minccalc', '-clobber', '-expression', "'if(A[1]>0.5){out=A[0];}else{out=A[1];}'", target, args.target_mask, target_masked])
		if args.verbose:
			print(cmd)
		commands.getoutput(cmd)





class conf:
	def __init__(self, type_, trans, blur_fwhm_mri, blur_fwhm_pet, steps, tolerance, simplex):
		self.type_=type_
		self.trans=trans
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
	tmp_source=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)
	tmp_source_blur_base=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)
	tmp_source_blur=tmpdir+"/s_base_fwhm"+str(confi.blur_fwhm_mri)+"_"+confi.type_+".mnc"
	tmp_target=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)
	tmp_target_blur_base=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)
	tmp_target_blur=tmpdir+"/t_base_fwhm"+str(confi.blur_fwhm_mri)+"_"+confi.type_+".mnc"
	tmp_xfm = tmpdir+"/t_base_conf"+str(i)+".xfm";
	tmp_rspl_vol = tmpdir+"/s_base_conf"+str(i)+".mnc";

	print '-------+------- iteration'+str(i)+' -------+-------\n'
	cmd=' '.join(['mincblur', '-clobber', '-no_apodize', '-fwhm', str(confi.blur_fwhm_mri), target, tmp_target_blur_base]); #$target_masked
	if args.verbose:
		print(cmd)
	commands.getoutput(cmd)

   	cmd=' '.join(['mincblur', '-clobber', '-no_apodize', '-fwhm', str(confi.blur_fwhm_pet), source, tmp_source_blur_base]); #$sourced_masked
	if args.verbose:
		print(cmd)
	commands.getoutput(cmd)


	cmd=' '.join(['minctracc', '-clobber', '-mi', args.lsqtype, '-step', confi.steps, '-simplex', str(confi.simplex), '-tol', str(confi.tolerance), tmp_source_blur, tmp_target_blur, tmp_xfm]);
	if args.verbose:
		print(cmd)
	commands.getoutput(cmd)

	
	cmd=' '.join(['mincresample', '-clobber', source, '-transformation', tmp_xfm, '-like', target]);
	if prev_xfm:
		cmd = ' '.join([cmd, '-transformation', prev_xfm])
	if args.source_mask:
		cmd = ' '.join([cmd, '-source_mask', args.source_mask])
	if args.target_mask:
		cmd = ' '.join([cmd, '-model_mask', args.target_mask])
	
	cmd = ' '.join([cmd, tmp_rspl_vol])
	
	if args.verbose:
		print(cmd)
	commands.getoutput(cmd)
	
	prev_xfm = tmp_xfm
	i += 1

	print '\n'



if args.init_xfm:
	cmd=' '.join(['xfmconcat', args.init_xfm, prev_xfm, outxfm]);
	if args.verbose:
		print(cmd)
	commands.getoutput(cmd)
else:
	cmd=' '.join(['cp', '-f', prev_xfm, outxfm]);
	if args.verbose:
		print(cmd)
	commands.getoutput(cmd)


if args.outfile:
	print '\n-+- creating $outfile using $outxfm -+-\n'
	cmd=' '.join(['mincresample', '-clobber', '-like', target, '-transformation', outxfm, source, outfile]);
	if args.verbose:
		print(cmd)
	commands.getoutput(cmd)


