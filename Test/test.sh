run_appian(){
    test_name=$1
    test_dir=$2
    extra_options=${3:-""}
    log=${test_dir}/test_${test_name}.txt
    printf "Test: $test_name -- Errors = "
    minimal_options="python2.7 $base_path/Launcher.py -s ${test_data_path} -t ${out_data_path} --threads ${threads}"
    bash -c "$minimal_options $extra_options" &> $log
    
    n_errors="`grep "Error" $log | wc -l`" 
    
    printf "%s -->" "$n_errors"
    
    if [[ "$n_errors" != "0" ]]; then
        printf " FAILED."
        out_log=${test_dir}/test_${test_name}.failed
    else
        printf " PASSED."
        out_log=${test_dir}/test_${test_name}.passed
    fi
    
    mv $log $out_log
}

#Number of threads to use for running APPIAN. Default=1, recommended is 4 or more.
threads=${1:-1} 
base_path=${2:-"/APPIAN"}
test_data_path=${3:-"/APPIAN/Test/cimbi"}
out_data_path=${4:-"/APPIAN/Test"}


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


echo Running test suite on current version of APPIAN
echo Warning: You should have commited latest changes to current git branch
echo "          --> git commit -a -m \"your message here\""
#sleep 3

#Create a timestamp for testing session
ts=`date +"%Y-%m-%d_%H-%M-%S"`
test_dir="test_logs/test_$ts"

#Create directory to store test results
mkdir -p archive $dir

current_git_commit=`git rev-parse HEAD`
echo "{ "base_path":$base_path, "test_data_path":$test_data_path,"out_data_path":$out_data_path,"git_hash":$current_git_commit,"timestamp":$ts}" > ${dir}/info.json

### Minimal Inputs
run_appian "Mininimum" ${dir} 
exit 0
### PVC
# GTM
run_appian "PVC-GTM" ${dir}" --fwhm 3 3 3 --pvc-method \'GTM\'" 

# idSURF
run_appian "PVC-idSURF" ${dir}" --fwhm 3 3 3 --pvc-method \'idSURF\'"  

### Quantification
# Logan Plot
run_appian "Quant-LP" ${dir}" --tka-method lp --tka-label 3 --results-label-erosion 1" 

# Patlak-Gjedde Plot
run_appian "Quant-PP" ${dir}" --tka-method pp --tka-label 3 --results-label-erosion 1" 

# SUVR
run_appian "Quant-SUVR" ${dir}" --tka-method pp --tka-label 3 --results-label-erosion 1 -s /APPIAN/Test/cimbi -t /APPIAN/Test/out_cimbi"

# SUV
#run_appian "--tka-method suv" 

### Atlas / Templates
## DKA atlas in MNI 152 space
run_appian "Atlas-DKA" ${dir}"--tka-label-img  /APPIAN/Atlas/MNI152/dka.mnc --tka-labels 2,41 --tka-label-ones-only"  

## AAL atlas with Colin 27 template
run_appian "mininimum" ${dir}  "--results-label-img  /APPIAN/Atlas/ROI_MNI_AAL_V5_UBYTE_round.mnc /APPIAN/Atlas/colin27_t1_tal_lin_ubyte.mnc  --threads ${threads}"  

