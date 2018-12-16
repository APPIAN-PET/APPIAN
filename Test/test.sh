SCRIPTPATH="$( cd "$(dirname "$1")"; cd .. ; pwd -P )"

docker_path="/APPIAN/Launcher.py"

#############
### CIMBI ###
#############
### Minimal Inputs
docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py -s /APPIAN/Test/cimbi -t /APPIAN/Test/out_cimbi ";

### PVC
#docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py --fwhm 3 3 3 --pvc-method 'GTM' --no-results-report -s /APPIAN/Test/cimbi -t /APPIAN/Test/out_cimbi  --sessions 01  01";

### Quantification
#docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py --tka-method lp --tka-label 3 --results-label-erosion 5 --fwhm 3 3 3 --pvc-method 'GTM' --no-results-report -s /APPIAN/Test/cimbi -t /APPIAN/Test/out_cimbi  --sessions 01  01";


