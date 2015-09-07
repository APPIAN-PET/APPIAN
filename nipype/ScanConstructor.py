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
		self.t1_native={}
		self.t1_nuc={}
		self.t1_brainmask={}
		self.t1_headmask={}
		self.tal={}
		self.tal_final={}
		self.tal_nl={}
		self.tal_rhp={}
		self.tal_brainmask={}
		self.tal_skullmask={}
		self.xfm_tal={}
		self.xfm_tal_nl={}
		self.grid_tal_nl={}

		# anatomical masks
		self.tal_animal={}
		self.tal_animal_masked={}
		self.tal_pve_gm={}
		self.tal_pve_wm={}
		self.tal_pve_csf={}
		self.tal_cls={}
		self.tal_ref={}
		self.t1_ref={}
		self.xfm_tal_ref={}
		self.xfm_tal_roi={}
		self.tal_parcel={}

		# pet images
		self.emission_sinogram={}
		self.transmission_sinogram={}
		self.attenuation_map={}
		self.blank_sinogram={}
		self.normalization_file={}
		self.realign_results={}
		self.dynamic_pet_raw={}
		self.dynamic_pet_raw_ecat={}
		self.dynamic_pet_pvc={}
		self.dynamic_rhp_corr={}
		self.dynamic_rhp_ref={}
		self.volume_pet_rhp={}
		self.volume_pet_t1={}
		self.volume_pet_headmask={}
		self.xfm_pet_t1_init={}
		self.xfm_pet_t1={}
		self.xfm_pet_tal={}
		self.xfm_pet_tal_nl={}
		self.dynamic_pet_tal={}
		self.volume_pet_tal={}

		# TAC files
		self.idwc={}
		self.idwc_tal={}
		self.dft_ref={}
		self.dft_ref_bak={}
		self.dft_ref_tal={}
		self.dft_ref_tal_raw={}
		self.dft_r={}
		self.dft_ref_bak={}
		self.dft_ref_tal={}
		self.sif={}
		self.dft_roi={}
		self.tac_fitting_roi={}
		self.dft_roi_tal={}
		self.tac_fitting_roi_tal={}

		# Modelling parameters results
		self.turku_res_roi={}
		self.turku_fit_roi={}
		self.turku_res_roi_tal={}
		self.turku_fit_roi_tal={}
		self.srtm_bp={}
		self.srtm_sdbp={}
		self.srtm_r1={}
		self.srtm_sdr1={}
		self.srtm_k2={}
		self.srtm_sdk2={}
		self.srtm_r1={}
		self.srtm_sdr1={}
		self.srtm_t3={}
		self.srtm_bp_tal={}
		self.srtm_sdbp_tal={}
		self.srtm_r1_tal={}
		self.srtm_sdr1_tal={}
		self.srtm_k2_tal={}
		self.srtm_sdk2_tal={}
		self.srtm_r1_tal={}
		self.srtm_sdr1_tal={}
		self.srtm_t3_tal={}
		self.srtm_bp_tal_nl={}
		self.srtm_sdbp_tal_nl={}
		self.srtm_bp_extract={}
		self.srtm_bp_tal_extract={}


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
		self.t1_native=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"native"+os.sep+opts.prefix+"_"+id+"_"+"t1.mnc"
		self.t1_nuc=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"native"+os.sep+opts.prefix+"_"+id+"_"+"t1_nuc.mnc"
		self.t1_brainmask=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mask"+os.sep+opts.prefix+"_"+id+"_"+"skull_mask_native.mnc"
		self.t1_headmask=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mri"+os.sep+"native"+os.sep+opts.prefix+"_"+id+"_"+"head_mask_native"+'.'+opts.extension
		self.tal=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"final"+os.sep+opts.prefix+"_"+id+"_"+"t1_tal.mnc"
		self.tal_final=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"final"+os.sep+opts.prefix+"_"+id+"_"+"t1_final.mnc"
		self.tal_nl=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"final"+os.sep+opts.prefix+"_"+id+"_"+"t1_nl.mnc"
		self.tal_rhp=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mri"+os.sep+"stereotaxic"+os.sep+opts.prefix+"_"+id+"_"+"t1_final_resh_"+opts.templateROIsuffix+'.'+opts.extension
		self.tal_brainmask=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mask"+os.sep+opts.prefix+"_"+id+"_"+"skull_mask.mnc"
		self.tal_skullmask=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"mask"+os.sep+opts.prefix+"_"+id+"_"+"brain_mask.mnc"
		self.xfm_tal=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms/linear"+os.sep+opts.prefix+"_"+id+"_"+"t1_tal.xfm"
		self.xfm_tal_nl=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms/nonlinear"+os.sep+opts.prefix+"_"+id+"_"+"nlfit_It.xfm"
		self.grid_tal_nl=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms/nonlinear"+os.sep+opts.prefix+"_"+id+"_"+"nlfit_It_grid_0.mnc"

		# anatomical masks
		self.tal_animal=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"segment"+os.sep+opts.prefix+"_"+id+"_"+"stx_labels.mnc"
		self.tal_animal_masked=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"segment"+os.sep+opts.prefix+"_"+id+"_"+"stx_labels_masked.mnc"
		self.tal_pve_gm=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"classify"+os.sep+opts.prefix+"_"+id+"_"+"pve_gm.mnc"
		self.tal_pve_wm=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"classify"+os.sep+opts.prefix+"_"+id+"_"+"pve_wm.mnc"
		self.tal_pve_csf=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"classify"+os.sep+opts.prefix+"_"+id+"_"+"pve_csf.mnc"
		self.tal_cls=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"classify"+os.sep+opts.prefix+"_"+id+"_"+"pve_classify.mnc"
		self.tal_ref=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"regions"+os.sep+opts.prefix+"_"+id+"_"+"reference_tal_mask"+'.'+opts.extension
		self.t1_ref=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"regions"+os.sep+opts.prefix+"_"+id+"_"+"reference_t1_mask"+'.'+opts.extension
		self.xfm_tal_ref=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms"+os.sep+"non-linear"+os.sep+opts.prefix+"_"+id+"_"+"templateRefMri_nl.xfm"
		self.xfm_tal_roi=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"transforms"+os.sep+"non-linear"+os.sep+opts.prefix+"_"+id+"_"+"templateROImri_nl_"+opts.templateROIsuffix+".xfm"
		if opts.ROIsuffix != 'animal':
			self.tal_parcel=opts.targetDir+os.sep+opts.prefix+os.sep+id+os.sep+"regions"+os.sep+opts.prefix+"_"+id+"_"+"labeled_roi_"+opts.ROIsuffix+'.'+opts.extension
		else:
			self.tal_parcel=opts.civetDir+os.sep+opts.prefix+os.sep+id+os.sep+"segment"+os.sep+opts.prefix+"_"+id+"_"+"stx_labels_masked.mnc"


		for condi in list(range(0,len(opts.condiList))):
			
			# pet images
			self.emission_sinogram={}
			self.transmission_sinogram={}
			self.attenuation_map={}
			self.blank_sinogram={}
			self.normalization_file={}
			self.realign_results={}
			self.dynamic_pet_raw={}
			self.dynamic_pet_raw_ecat={}
			self.dynamic_pet_pvc={}
			self.dynamic_rhp_corr={}
			self.dynamic_rhp_ref={}
			self.volume_pet_rhp={}
			self.volume_pet_t1={}
			self.volume_pet_headmask={}
			self.xfm_pet_t1_init={}
			self.xfm_pet_t1={}
			self.xfm_pet_tal={}
			self.xfm_pet_tal_nl={}
			self.dynamic_pet_tal={}
			self.volume_pet_tal={}

			# TAC files
			self.idwc={}
			self.idwc_tal={}
			self.dft_ref={}
			self.dft_ref_bak={}
			self.dft_ref_tal={}
			self.dft_ref_tal_raw={}
			self.dft_r={}
			self.dft_ref_bak={}
			self.dft_ref_tal={}
			self.sif={}
			self.dft_roi={}
			self.tac_fitting_roi={}
			self.dft_roi_tal={}
			self.tac_fitting_roi_tal={}

			# Modelling parameters results
			self.turku_res_roi={}
			self.turku_fit_roi={}
			self.turku_res_roi_tal={}
			self.turku_fit_roi_tal={}
			self.srtm_bp={}
			self.srtm_sdbp={}
			self.srtm_r1={}
			self.srtm_sdr1={}
			self.srtm_k2={}
			self.srtm_sdk2={}
			self.srtm_r1={}
			self.srtm_sdr1={}
			self.srtm_t3={}
			self.srtm_bp_tal={}
			self.srtm_sdbp_tal={}
			self.srtm_r1_tal={}
			self.srtm_sdr1_tal={}
			self.srtm_k2_tal={}
			self.srtm_sdk2_tal={}
			self.srtm_r1_tal={}
			self.srtm_sdr1_tal={}
			self.srtm_t3_tal={}
			self.srtm_bp_tal_nl={}
			self.srtm_sdbp_tal_nl={}
			self.srtm_bp_extract={}
			self.srtm_bp_tal_extract={}
