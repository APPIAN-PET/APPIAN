SCRIPTPATH="$( cd "$(dirname "$0")"; cd .. ; pwd -P )"

i=0


#CIMBI
docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py --no-results-report --user-brainmask  --tka-label-space stereo --tka-method 'lp' --tka-label-img antsAtropos --tka-labels-brain-only --tka-labels-ones-only  --tka-label 3 --tka-label-erosion 5 --results-label-space stereo  --results-labels-brain-only --results-label 2 --results-label-img antsAtropos --sourcedir /APPIAN/Test/test_data --targetdir /APPIAN/Test/out_test_cimbi  --sessions 01  --fwhm 3 3 3  01";

#docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py  --user-brainmask --pvc-label-space stereo  --pvc-label-img antsAtropos  --tka-label-space stereo --tka-method 'lp' --tka-label-img antsAtropos --tka-labels-brain-only --tka-labels-ones-only  --tka-label 3 --tka-label-erosion 5 --results-label-space stereo  --results-labels-brain-only --results-label 2 --results-label-img antsAtropos --sourcedir /APPIAN/Test/test_data --targetdir /APPIAN/Test/out_test_cimbi  --sessions 01  --fwhm 3 3 3  01";


#Flumazenil
#docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py --user-brainmask --user-t1mni  --pvc-label-space stereo  --pvc-label-img antsAtropos  --tka-label-space stereo --tka-method 'lp' --tka-label-img antsAtropos --tka-labels-brain-only --tka-labels-ones-only  --tka-label 3 --tka-label-erosion 5 --results-label-space stereo  --results-labels-brain-only --results-label 2 --results-label-img antsAtropos --sourcedir /APPIAN/Test/test_data_fmz --targetdir /APPIAN/Test/out_test_fmz  --tasks 1 --sessions I  --pet-scanner HRRT  01";

