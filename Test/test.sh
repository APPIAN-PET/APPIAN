SCRIPTPATH="$( cd "$(dirname "$0")"; cd .. ; pwd -P )"

i=0

#docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py --sourcedir /APPIAN/Test/test_data_fmz --targetdir /APPIAN/Test/out_test_fmz --user-brainmask --user-t1mni --fwhm 2.5 2.5 2.5 --tasks 1 --sessions I 01";


docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py  --user-brainmas --user-t1mni  --pvc-label-space stereo  --pvc-label-img "cls"  --tka-label-space stereo --tka-method 'lp' --tka-label-img "cls" --tka-labels-brain-only --tka-labels-ones-only  --tka-label 3 --tka-label-erosion 5 --results-label-space stereo  --results-labels-brain-only --results-label 2 --results-label-img "cls" --sourcedir /APPIAN/Test/test_data_fmz --targetdir /APPIAN/Test/out_test_fmz  --tasks 1 --sessions I  --pet-scanner HRRT  01";


exit 0
# T1 Brain Mask
register Test/out_test_0/preproc/mri_normalize/_args_task.ses01.sid01/t1_mni_brain_mask/sub-01_ses-01_T1w_TO_mni_icbm152_t1_tal_nlin_sym_09a__LinReg_brain_mask.mnc Test/out_test_0/preproc/mri_normalize/_args_task.ses01.sid01/minctracc_registration/sub-01_ses-01_T1w_TO_mni_icbm152_t1_tal_nlin_sym_09a__LinReg.mnc

# PET T1 Coregistration
register Test/out_test_0/preproc/pet-coregistration/_args_task.ses01.sid01/pet2mri/01_01__petVolume_TO_sub-01_ses-01_T1w__LinReg.mnc Test/test_data/sub-01/ses-01/anat/sub-01_ses-01_T1w.mnc

# PVC Labels
register Test/out_test_0/preproc/pet-coregistration/_args_task.ses01.sid01/pet2mri/01_01__petVolume_TO_sub-01_ses-01_T1w__LinReg.mnc Test/out_test_0/preproc/masking/_args_task.ses01.sid01/pvcLabels/sub-01_ses-01_T1w_labeled_space-pet.mnc

# Results Labels
register Test/out_test_0/preproc/pet-coregistration/_args_task.ses01.sid01/pet2mri/01_01__petVolume_TO_sub-01_ses-01_T1w__LinReg.mnc Test/out_test_0/preproc/masking/_args_task.ses01.sid01/resultsLabels/sub-01_ses-01_T1w_labeled_space-pet.mnc
