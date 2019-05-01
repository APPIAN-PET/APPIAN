#
# This is a script that essentially runs APPIAN a bunch of different times with varying options. In theory, it should
# be useable with any data set, although in practice it has only been developed using a small test data set of
# simulated PET images and T1 images from the 1000 Connectomes Project.
#
# The purpose of this validatation script is to check that changes made to the APPIAN code do not break the package.
# As such it should be run before pushing any new changes to the Git repository and especially before creating an
# updated Docker container with a new version APPIAN.
#
# More tests will need to be added in the future as the current set are not exhaustive.

# It is therefore a good idea to reuse the output of previous tests to avoid rerunning processing stages unecessarily.
# For example, there is no need to rerun PET-MRI co-registration everytime one wants to test a downstream processing
# stage, like PVC or quantification. The tests are therefore organized such that at least some of the outputs of the
# previous tests can be reused for subsequent ones.
#

validation_qc(){
    qc_dir=${test_dir}/qc
    mkdir -p $qc_dir

    for f in `find ${out_data_path}/output -name "*.mnc"`; do
        var1=`stat $f | grep Modify | awk '{split($0,ar," "); print ar[2] ar[3] }'`
        f2=${qc_dir}/`basename $f | sed "s/.mnc/_${var1}.png/"`
        if [[ ! -f $f2 ]] ; then
            python ${base_path}/Test/validation_qc.py $f $f2 2> /dev/null
        fi
    done

}

run_appian() {
    test_name=$1 #Name of the test command to run on APPIAN
    extra_options=${2:-""} #Options beyond the minimal ones necessary to run APPIAN (e.g., pvc, tka, atlases, etc.)
    log=${test_dir}/test_${test_name}.txt  #Name of the log file where stdout/stderr from test will be saved

    if [[ -f ${test_dir}/test_${test_name}.passed ]]; then
        #If log with ".passed" suffix exists, then do not rerun the test
        printf "Test : $test_name -- already passed for timestamp $ts --> skipping\n"
        return 0
    else
        #Test APPIAN with minimal and extra options
        printf "Test: $test_name -- "

        #Define variable with minimal command to launch APPIAN
        minimal_options="python2.7 $base_path/Launcher.py  --verbose 2 -s ${test_data_path} -t ${out_data_path}/output --threads ${threads}"
        bash -c "$minimal_options $extra_options" &> $log
        errorcode=$?
        #The number of errors produced by the APPIAN run is determined by the number of crash reports with
        # .pklz suffix produced by Nipype in the current directory. This is why any existing crash reports must
        # moved elsewhere before initiating the run

        n_errors=`ls crash-*pklz 2> /dev/null | wc -l`
        if [[ $errorcode != 0 && $n_errors == 0 ]]; then
            n_errors=1
        fi
        printf "Errors = %s -->" "$n_errors"

        if [[ $n_errors != 0 || $errorcode != 0 ]]; then
            #If errors are detected, then the log suffix is set to failed
            printf " failed.\n"
            out_log=${test_dir}/test_${test_name}.failed
            crash_files=`ls crash-*pklz &> /dev/null`
            if [[ $crash_files ]]; then
                mv $crash_files  ${test_dir}/ #Move Nipype crash reports to test directory
            fi
        else
            #If errors are detected, then the log suffix is set to passed
            printf " passed.\n"
            out_log=${test_dir}/test_${test_name}.passed
            rm -f ${test_dir}/test_${test_name}.failed #If there is a previous failed log, remove it

            if [[ $qc == 1 ]]; then
                validation_qc
            fi
        fi
        mv $log $out_log #Move log to version with passed/failed suffix

        if [[ $n_errors != 0 || $errorcode != 0 ]]; then
            if [[ $exit_on_failure == 1 ]] ; then
                exit 0
            fi
        fi
    fi
}

if [[ $1 == "-help" || $1 == "--help" || $1 == "-h" || $1 == "--h" ]]; then
    echo
    echo 'Name :        appian_validation.sh'
    echo 'Description:  Run validation test suite on current version of APPIAN'
    echo 'Useage :      test.sh <n threads> <path to APPIAN dir> <path to data> <path for outputs> <exit on failure> <timestamp>'
    echo "              n threads :             number of CPU threads to use for testing (default=1, recommended=4)"
    echo "              path to APPIAN dir :    Abs. path to location of APPIAN repository (default=/APPIAN)"
    echo "              path to data :          Path to data to be used to testing (default=/APPIAN/Test/cimbi)"
    echo "              path for outputs :      Path where testing outputs will be saved (default=/APPIAN/Test)"
    echo "              exit on failure :       Exit validation if a test fails. Set to 1 to enable (default=0)"
    echo "              qc :                    Create .png images of output files. Set to 1 to enable (default=0)"
    echo "              timestamp :             Timestamp for validation. Will be set each time scipt is run. "
    echo "                                      However, users that are debugging may wish to continue validation with"
    echo "                                      existing timestamp to prevent rerunning all test. In this case, "
    echo "                                      users can provide timestamp from exisint validation."
    echo "Examples :"
    echo "          1) Run validation defaults"
    echo "             ./validate_appian.sh"
    echo "          2) Run validation with 8 threads in non-default directories. Timestamp genereated at runtime"
    echo "              ./validate_appian.sh 8 /home/APPIAN /data1/projects/cimbi /data1/projects/  "
    echo "          3) Run with 1 thread in default directories with pre-existing timestamp"
    echo "              ./validate_appian.sh 1 /APPIAN /APPIAN/Test/cimbi /APPIAN/Test 20181221-220648"
    echo
    exit 1
fi
echo
echo "     Launching APPIAN validation tests "
echo "   -------------------------------------"
echo Warning: You should have commited latest changes to current git branch

########################
# Setup input vaiables #
########################

#Number of threads to use for running APPIAN. Default=1, recommended is 4 or more.
threads=${1:-1}
base_path=${2:-"/opt/APPIAN"}
test_data_path=${3:-"/opt/APPIAN/Test/test_data"}
out_data_path=${4:-"/opt/APPIAN/Test/"}
#Create a timestamp for testing session.
#Can use existing timestamp if using output files from previous test run
exit_on_failure=${5:-1}
qc=${6:-0}
ts=${7:-`date +"%Y%m%d-%H%M%S"`}
test_dir="${out_data_path}/appian_validation/test_$ts"

################
# Check Inputs #
################
if [[ ! -f $base_path/Launcher.py ]]; then
    echo Error: $base_path/Launcher.py does not exist. Must specify valid path to APPIAN repository.
    exit 1
fi

if [[ ! -d $test_data_path ]]; then
    echo Error: $test_data_path does not exist. Must specify valid path to test data directory.
    exit 1
fi

if [[ ! -d $out_data_path ]]; then
    echo Error: $out_data_path does not exist. Must specify valid path where output data can be stored.
    exit 1
fi

if [[ `ls crash*pklz ` ]]; then
    echo Warning: Moving existin crash .pklz reports to `pwd`/crash_backup
    echo Test script requires that there be no crash reports in the current directory
    mkdir -p nipype_crash_backup
    mv `ls crash*pklz` nipype_crash_backup
fi

#################################
# Create preliminary files/dirs #
#################################

#Create directory to store test results
mkdir -p  ${out_data_path}/appian_validation $test_dir

#Get hash for current git commit

current_git_commit=`cd $base_path; git rev-parse HEAD`

current_docker_container=`cat /etc/hostname`

#Create a .json with some info about the run. Should help keep track of what version of APPIAN was tested
echo "{ "base_path":$base_path, "test_data_path":$test_data_path,"out_data_path":$out_data_path,"git_hash":$current_git_commit,"timestamp":$ts}" > ${test_dir}/info.json

#############
# Run tests #
#############
echo Timestamp: $ts
echo Git Commit : $current_git_commit
echo Docker Container / Hostname: $current_docker_container
echo


#TODO (1) Add surface testing

if [[ "$acq" == "fdg" ]]; then
    echo ____Testing 3D PET Images____
    tag="3D"
else
    echo ____Testing 4D PET Images____
    tag="4D"
fi

### Minimal Inputs
run_appian "Atlas-AAL" "--subjects 000101 --coreg-method ants --sessions baseline  --results-label-img  ${base_path}/Atlas/COLIN27/ROI_MNI_AAL_V5_UBYTE_round.nii --results-label-template ${base_path}/Atlas/COLIN27/colin27_t1_tal_lin_ubyte.nii  --normalization-type affine  --fwhm 6 6 6 --pvc-method VC --pvc-max-iterations 1 --tka-method suv --start-time 5 --quant-label 3 " #   
exit 0 
#    --pvc-method VC --quant-method suvr --fwhm 5 5 5 # --pvc-label-img ${base_path}/Atlas/COLIN27/ROI_MNI_AAL_V5_UBYTE_round.mnc --pvc-label-template ${base_path}/Atlas/COLIN27/colin27_t1_tal_lin_ubyte.mnc  --tka-label-img ${base_path}/Atlas/COLIN27/ROI_MNI_AAL_V5_UBYTE_round.mnc --tka-label-template ${base_path}/Atlas/COLIN27/colin27_t1_tal_lin_ubyte.mnc

### PVC
pvc_methods="GTM idSURF VC"
for pvc in $pvc_methods; do
    run_appian "PVC-${pvc}" "--subjects 000101 --sessions baseline  --fwhm 6 6 6 --pvc-method ${pvc}"
done

### Analysis Space
## Stereotaxic space
run_appian  "Space-Stereo" "--subjects 000101 --sessions baseline  --analysis-space stereo --tka-method suvr --quant-label 3 --tka-label-erosion 1"

## MRI space
run_appian  "Space-MRI" "--subjects 000101 --sessions baseline  --analysis-space t1 --tka-method suvr --tka-label 3 --tka-label-erosion 1"

### Atlas / Templates
## DKA atlas in MNI 152 space
run_appian "Atlas-DKA" "--subjects 000101 --sessions baseline  --tka-label-img ${base_path}/Atlas/MNI152/dka.mnc --results-label-img ${base_path}/Atlas/MNI152/dka.mnc --tka-label 2 41 --tka-labels-ones-only"

## AAL atlas with Colin 27 template
run_appian "Atlas-AAL" "--subjects 000101 --sessions baseline  --results-label-img  ${base_path}/Atlas/COLIN27/ROI_MNI_AAL_V5_UBYTE_round.mnc --results-label-template ${base_path}/Atlas/COLIN27/colin27_t1_tal_lin_ubyte.mnc "

#TODO: Fix stereotaxic template. Following command does not run
#run_appian "Stereo-Colin27" " --results-label-img  ${base_path}/Atlas/COLIN27/ROI_MNI_AAL_V5_UBYTE_round.mnc --stereotaxic-template  ${base_path}/Atlas/COLIN27/colin27_t1_tal_lin_ubyte.mnc "

## Quantification
quant_methods="lp lp-roi pp pp-roi srtm srtm-bf suvr suv" #suv srtm, roi

for quant in $quant_methods; do
    run_appian "Quant-${quant}" " --subjects 000101 --sessions baseline --start-time 2.5 --tka-method ${quant} --tka-label 3 --tka-labels-ones-only --tka-label-erosion 1"
done
exit 0
# Quantification with arterial
run_appian "Quant-srtm-arterial" " --subjects 000101 --sessions baseline --arterial --start-time 2.5 --tka-method srtm --tka-label 3 --tka-labels-ones-only --tka-label-erosion 1"

run_appian "Quant-idSURF-lp" "--subjects 000101 --sessions baseline --start-time 2.5 --fwhm 6 6 6 --pvc-method idSURF --tka-method lp --tka-label 3 --tka-labels-ones-only --tka-label-erosion 1"

run_appian "Quant-idSURF-suvr" "--subjects 000101 --sessions baseline --start-time 2.5 --fwhm 6 6 6  --pvc-method idSURF --tka-method suvr --tka-label 3 --tka-labels-ones-only --tka-label-erosion 1"

run_appian "Quant-VC-lp" "--subjects 000101 --sessions baseline --start-time 2.5 --fwhm 6 6 6  --pvc-method VC --tka-method lp --tka-label 3 --tka-labels-ones-only --tka-label-erosion 1"

run_appian "Quant-VC-suvr" "--subjects 000101 --sessions baseline --start-time 2.5 --fwhm 6 6 6  --pvc-method VC --tka-method suvr --tka-label 3 --tka-labels-ones-only --tka-label-erosion 1"

