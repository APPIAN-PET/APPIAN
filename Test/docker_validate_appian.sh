SCRIPTPATH="$( cd "$(dirname "$0")"; cd .. ; pwd -P )"

threads=${1:-1}
base_path=${2:-"/APPIAN"}
test_data_path=${3:-"/APPIAN/Test/test_data"}
out_data_path=${4:-"/APPIAN/Test/"}
#Create a timestamp for testing session.
#Can use existing timestamp if using output files from previous test run
exit_on_failure=${5:-1}
qc=${6:-0}
ts=${7:-`date +"%Y%m%d-%H%M%S"`}
test_dir="${out_data_path}/appian_validation/test_$ts"

docker run -v "$SCRIPTPATH":"/APPIAN" --rm tffunck/appian:latest-dev bash -c "/APPIAN/Test/validate_appian.sh $threads $base_path $test_data_path $out_data_path $exit_on_failure $qc $ts $test_dir"
