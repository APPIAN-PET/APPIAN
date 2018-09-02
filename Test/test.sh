SCRIPTPATH="$( cd "$(dirname "$0")"; cd .. ; pwd -P )"

i=0

docker run -v "$SCRIPTPATH":"/APPIAN" tffunck/appian:latest bash -c "python2.7 /APPIAN/Launcher.py --sourcedir /APPIAN/Test/test_data --targetdir /APPIAN/Test/out_test_${i} --fwhm 4 4 4 --sessions 01 01";  
 
