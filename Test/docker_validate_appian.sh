SCRIPTPATH="$( cd "$(dirname "$0")"; cd .. ; pwd -P )"

docker run -v "$SCRIPTPATH":"/opt/APPIAN" tffunck/appian:latest bash -c "/opt/APPIAN/Test/validate_appian.sh $1 $2 $3 $4 $5 $6 $7"
