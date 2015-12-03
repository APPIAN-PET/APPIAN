import os


#class PipelineFiles(dict):
class PipelineFiles:
	def __init__(self):
		
		# scan features
		self.ext={}
		self.prefix={}
		self.id={}
		self.baseDir={}
		self.src_pet={}
		self.src_mri={}
		self.civetDir={}
		self.conditions={}

		# anatomical images
		self.civet.t1_native={}
		self.civet.t1_nuc={}
		self.civet.t1_brainmask={}
		self.civet.t1_headmask={}
		self.civet.tal={}
		self.civet.tal_final={}
		self.civet.tal_nl={}
		self.pypet.tal_rhp={}
		self.civet.tal_brainmask={}
		self.civet.tal_skullmask={}
		self.civet.xfm_tal={}
		self.civet.xfm_tal_nl={}
		self.civet.grid_tal_nl={}

		# anatomical masks
		self.civet.tal_animal={}
		self.civet.tal_animal_masked={}
		self.civet.tal_pve_gm={}
		self.civet.tal_pve_wm={}
		self.civet.tal_pve_csf={}
		self.civet.tal_cls={}
		self.pypet.tal_ref={}
		self.pypet.t1_ref={}
		self.pypet.xfm_tal_ref={}
		self.pypet.xfm_tal_roi={}
		self.pypet.tal_parcel={}

		# pet images
		self.pypet.emission_sinogram={}
		self.pypet.transmission_sinogram={}
		self.pypet.attenuation_map={}
		self.pypet.blank_sinogram={}
		self.pypet.normalization_file={}
		self.pypet.realign_results={}
		self.pypet.dynamic_pet_raw={}
		self.pypet.dynamic_pet_raw_ecat={}
		self.pypet.dynamic_pet_raw_real={}
		self.pypet.dynamic_pet_raw_real_ecat={}
		self.pypet.dynamic_pet_pvc={}
		self.pypet.dynamic_rhp_corr={}
		self.pypet.dynamic_rhp_ref={}
		self.pypet.volume_pet_rhp={}
		self.pypet.volume_pet_t1={}
		self.pypet.volume_pet_headmask={}
		self.pypet.xfm_pet_t1_init={}
		self.pypet.xfm_pet_t1={}
		self.pypet.xfm_pet_tal={}
		self.pypet.xfm_pet_tal_nl={}
		self.pypet.dynamic_pet_tal={}
		self.pypet.volume_pet_tal={}

		# TAC files
		self.pypet.idwc={}
		self.pypet.idwc_tal={}
		self.pypet.dft_ref={}
		self.pypet.dft_ref_bak={}
		self.pypet.dft_ref_tal={}
		self.pypet.dft_ref_tal_raw={}
		self.pypet.sif={}
		self.pypet.dft_roi={}
		self.pypet.tac_fitting_roi={}
		self.pypet.dft_roi_tal={}
		self.pypet.tac_fitting_roi_tal={}

		# Modelling parameters results
		self.pypet.turku_res_roi={}
		self.pypet.turku_fit_roi={}
		self.pypet.turku_res_roi_tal={}
		self.pypet.turku_fit_roi_tal={}
		self.pypet.srtm_bp={}
		self.pypet.srtm_sdbp={}
		self.pypet.srtm_r1={}
		self.pypet.srtm_sdr1={}
		self.pypet.srtm_k2={}
		self.pypet.srtm_sdk2={}
		self.pypet.srtm_r1={}
		self.pypet.srtm_sdr1={}
		self.pypet.srtm_t3={}
		self.pypet.srtm_bp_tal={}
		self.pypet.srtm_sdbp_tal={}
		self.pypet.srtm_r1_tal={}
		self.pypet.srtm_sdr1_tal={}
		self.pypet.srtm_k2_tal={}
		self.pypet.srtm_sdk2_tal={}
		self.pypet.srtm_r1_tal={}
		self.pypet.srtm_sdr1_tal={}
		self.pypet.srtm_t3_tal={}
		self.pypet.srtm_bp_tal_nl={}
		self.pypet.srtm_sdbp_tal_nl={}
		self.pypet.srtm_bp_extract={}
		self.pypet.srtm_bp_tal_extract={}


	def set_filenames(self, opts, id):
		# scan features
		self.ext=opts.extension
		self.prefix=opts.prefix
		self.id=id
		self.baseDir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep
		self.src_pet=opts.sourceDir+os.sep+"pet"+os.sep+opts.prefix+os.sep
		self.src_mri=opts.sourceDir+os.sep+"mri"+os.sep+opts.prefix+os.sep
		self.civetDir=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep
		self.conditions=opts.condiList

		## Create directories
		logdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"log"+os.sep
		os.makedirs(logdir)
		tmpdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"temp"+os.sep
		os.makedirs(tmpdir)
		tmptfmdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"temp"+os.sep+"transforms"+os.sep
		os.makedirs(tmptfmdir)
		petdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"pet"+os.sep
		os.makedirs(petdir)
		petdynadir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"pet"+os.sep+"dynamic"+os.sep
		os.makedirs(petdynadir)
		petvoldir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"pet"+os.sep+"volume"+os.sep
		os.makedirs(petvoldir)
		mrinatdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mri"+os.sep+"native"+os.sep
		os.makedirs(mrinatdir)
		mristxdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mri"+os.sep+"stereotaxic"+os.sep
		os.makedirs(mristxdir)
		lindir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms"+os.sep+"linear"+os.sep
		os.makedirs(lindir)
		nlindir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms"+os.sep+"non-linear"+os.sep
		os.makedirs(nlindir)
		regdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"regions"+os.sep
		os.makedirs(regdir)
		tacdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"TAC"+os.sep
		os.makedirs(tacdir)
		bpdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"BP"+os.sep
		os.makedirs(bpdir)
		bpnatdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"BP"+os.sep+"native"+os.sep
		os.makedirs(bpnatdir)
		bpstxdir=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"BP"+os.sep+"stereotaxic"+os.sep
		os.makedirs(bpstxdir)

		# anatomical images
		self.civet.t1_native=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"native"+os.sep+opts.prefix+"_"+id+"_"+"t1.mnc"
		self.civet.t1_nuc=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"native"+os.sep+opts.prefix+"_"+id+"_"+"t1_nuc.mnc"
		self.civet.t1_brainmask=mrinatdir+os.sep+opts.prefix+"_"+id+"_"+"t1_skull_mask_native.mnc"+'.'+opts.extension
		self.civet.t1_headmask=mrinatdir+os.sep+opts.prefix+"_"+id+"_"+"t1_head_mask_native"+'.'+opts.extension
		self.civet.tal=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"final"+os.sep+opts.prefix+"_"+id+"_"+"t1_tal.mnc"
		self.civet.tal_final=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"final"+os.sep+opts.prefix+"_"+id+"_"+"t1_final.mnc"
		self.civet.tal_nl=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"final"+os.sep+opts.prefix+"_"+id+"_"+"t1_nl.mnc"
		self.pypet.tal_rhp=mristxdir+os.sep+opts.prefix+"_"+id+"_"+"t1_final_resh_"+opts.templateROIsuffix+'.'+opts.extension
		self.civet.tal_brainmask=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mask"+os.sep+opts.prefix+"_"+id+"_"+"skull_mask.mnc"
		self.civet.tal_skullmask=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mask"+os.sep+opts.prefix+"_"+id+"_"+"brain_mask.mnc"
		self.civet.xfm_tal=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms/linear"+os.sep+opts.prefix+"_"+id+"_"+"t1_tal.xfm"
		self.civet.xfm_tal_nl=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms/nonlinear"+os.sep+opts.prefix+"_"+id+"_"+"nlfit_It.xfm"
		self.civet.grid_tal_nl=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms/nonlinear"+os.sep+opts.prefix+"_"+id+"_"+"nlfit_It_grid_0.mnc"

		# anatomical masks
		self.civet.tal_animal=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"segment"+os.sep+opts.prefix+"_"+id+"_"+"stx_labels.mnc"
		self.civet.tal_animal_masked=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"segment"+os.sep+opts.prefix+"_"+id+"_"+"stx_labels_masked.mnc"
		self.civet.tal_pve_gm=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"classify"+os.sep+opts.prefix+"_"+id+"_"+"pve_gm.mnc"
		self.civet.tal_pve_wm=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"classify"+os.sep+opts.prefix+"_"+id+"_"+"pve_wm.mnc"
		self.civet.tal_pve_csf=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"classify"+os.sep+opts.prefix+"_"+id+"_"+"pve_csf.mnc"
		self.civet.tal_cls=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"classify"+os.sep+opts.prefix+"_"+id+"_"+"pve_classify.mnc"
		self.pypet.tal_ref=regdir+os.sep+opts.prefix+"_"+id+"_"+"reference_tal_mask"+'.'+opts.extension
		self.pypet.t1_ref=regdir+os.sep+opts.prefix+"_"+id+"_"+"reference_t1_mask"+'.'+opts.extension
		self.pypet.xfm_tal_ref=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms"+os.sep+"non-linear"+os.sep+opts.prefix+"_"+id+"_"+"templateRefMri_nl.xfm"
		self.pypet.xfm_tal_roi=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms"+os.sep+"non-linear"+os.sep+opts.prefix+"_"+id+"_"+"templateROImri_nl_"+opts.templateROIsuffix+".xfm"
		if opts.ROIsuffix != 'animal':
			self.pypet.tal_parcel=regdir+os.sep+opts.prefix+"_"+id+"_"+"labeled_roi_"+opts.ROIsuffix+'.'+opts.extension
		else:
			self.pypet.tal_parcel=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"segment"+os.sep+opts.prefix+"_"+id+"_"+"stx_labels_masked.mnc"


		for condi in list(range(0,len(opts.condiList))):
			
			# pet images
			self.pypet.emission_sinogram={}
			self.pypet.transmission_sinogram={}
			self.pypet.attenuation_map={}
			self.pypet.blank_sinogram={}
			self.pypet.normalization_file={}
			self.pypet.realign_results={}
			self.pypet.dynamic_pet_raw=self.src_pet+os.sep+opts.prefix+"_"+id+"_"+condi+"_orig"+'.'+opts.extension
			self.pypet.dynamic_pet_raw_ecat=self.src_pet+os.sep+opts.prefix+"_"+id+"_"+condi+"_orig.v"
			self.pypet.dynamic_pet_raw_real=self.src_pet+os.sep+opts.prefix+"_"+id+"_"+condi+"_real_orig"+'.'+opts.extension
			self.pypet.dynamic_pet_raw_real_ecat=self.src_pet+os.sep+opts.prefix+"_"+id+"_"+condi+"_real_orig.v"
			self.pypet.dynamic_pet_info=petdir+os.sep+opts.prefix+"_"+id+"_"+condi+"_real.info"
			self.pypet.dynamic_pet_pvc={}
			self.pypet.dynamic_rhp_corr={}
			self.pypet.dynamic_rhp_ref={}
			self.pypet.volume_pet=petvoldir+os.sep+opts.prefix+"_"+id+"_"+condi+"_real_sum"+'.'+opts.extension
			self.pypet.volume_pet_rhp={}
			self.pypet.volume_pet_t1=petvoldir+os.sep+opts.prefix+"_"+id+"_"+condi+"_t1_real_sum"+'.'+opts.extension
			self.pypet.volume_pet_headmask=regdir+os.sep+opts.prefix+"_"+id+"_"+condi+"_headmask"+'.'+opts.extension
			self.pypet.xfm_pet_t1_init={}
			self.pypet.xfm_pet_t1=lindir+os.sep+opts.prefix+"_"+id+"_"+condi+"_petmri.xfm"
			self.pypet.xfm_pet_tal={}
			self.pypet.xfm_pet_tal_nl={}
			self.pypet.dynamic_pet_tal={}
			self.pypet.volume_pet_tal={}

			# TAC files
			self.pypet.idwc={}
			self.pypet.idwc_tal={}
			self.pypet.dft_ref={}
			self.pypet.dft_ref_bak={}
			self.pypet.dft_ref_tal={}
			self.pypet.dft_ref_tal_raw={}
			self.pypet.dft_r={}
			self.pypet.dft_ref_bak={}
			self.pypet.dft_ref_tal={}
			self.pypet.sif={}
			self.pypet.dft_roi={}
			self.pypet.tac_fitting_roi={}
			self.pypet.dft_roi_tal={}
			self.pypet.tac_fitting_roi_tal={}

			# Modelling parameters results
			self.pypet.turku_res_roi={}
			self.pypet.turku_fit_roi={}
			self.pypet.turku_res_roi_tal={}
			self.pypet.turku_fit_roi_tal={}
			self.pypet.srtm_bp={}
			self.pypet.srtm_sdbp={}
			self.pypet.srtm_r1={}
			self.pypet.srtm_sdr1={}
			self.pypet.srtm_k2={}
			self.pypet.srtm_sdk2={}
			self.pypet.srtm_r1={}
			self.pypet.srtm_sdr1={}
			self.pypet.srtm_t3={}
			self.pypet.srtm_bp_tal={}
			self.pypet.srtm_sdbp_tal={}
			self.pypet.srtm_r1_tal={}
			self.pypet.srtm_sdr1_tal={}
			self.pypet.srtm_k2_tal={}
			self.pypet.srtm_sdk2_tal={}
			self.pypet.srtm_r1_tal={}
			self.pypet.srtm_sdr1_tal={}
			self.pypet.srtm_t3_tal={}
			self.pypet.srtm_bp_tal_nl={}
			self.pypet.srtm_sdbp_tal_nl={}
			self.pypet.srtm_bp_extract={}
			self.pypet.srtm_bp_tal_extract={}
