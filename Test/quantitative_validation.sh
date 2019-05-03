#!/bin/bash


SCRIPTPATH="$( cd "$(dirname "$0")"; cd .. ; pwd -P )"
version=ds001705 
nrm=${version}-download

####################
# Default Settings #
####################
appian_dir="/opt/APPIAN/"
source_dir="/opt/APPIAN/Test/$nrm"
target_dir="/opt/APPIAN/Test/out_${nrm}"
threads=1
use_docker=0
docker_image="tffunck/appian:latest"

function useage(){
	echo Name :	quantitative_validation.sh
	echo About:	Evaluate quantitative accuracy of APPIAN using NRM2018 Grand Challenge Dataset.
	echo Options:
	echo "		-a 		Set APPIAN directory where Launcher is located (default=$appian_dir)"
	echo "		-s 		Set source directory where NRM2018 data will be downloaded (default=$source_dir)"
	echo "		-t 		Set target directory where results will be saved (default=$target_dir)"
	echo "		-d 		Use docker container (default=False)"
	echo "		-i 		Docker image name (default=$docker_image)"
	echo "		-r 		Number of threads to use (default=$threads)"
	echo "		-h 		Print this help menu"
}

###################
# Parse Arguments #
###################

while getopts "a:s:t:r:i:dh" opt; do
	case $opt in
		a) 
			appian_dir=$OPTARG 1>&2
			;;
		s)
			source_dir=$OPTARG 1>&2
			;;
		t) 
			target_dir=$OPTARG 1>&2
			;;
		r) 
			threads=$OPTARG 1>&2
			;;

		i) 
			docker_image=$OPTARG 1>&2
			;;
		d) 
			use_docker=1
			;;
		h) 
			useage
			exit 0
			;;
		\?)
		  	echo "Warning -- Invalid option: -$OPTARG" 1>&2
			useage
			exit 1
		  	;;
		:)
			echo "Error -- Option -$OPTARG requires argument " 1>&2
			useage
			exit 1
  esac
done

##########################################
# Download data from Amazon Web Services #
##########################################
#	pip install awscli --upgrade --user > /dev/null && export PATH="${PATH}:/root/.local/bin/" > /dev/null
#    aws s3 sync --no-sign-request s3://openneuro.org/$version $source_dir

##################
# Run validation #
##################

echo 
echo Quantitative Validation Settings
echo -------------------------------
echo " APPIAN Directory : $appian_dir"
echo " Source Directory : $source_dir"
echo " Target Directory : $target_dir"
if [[ $use_docker == 1 ]]; then
	echo " Docker image : $docker_image"
fi
echo " Threads : $threads"
echo 

pvcMethods="idSURF VC"
#quantMethods="lp lp-roi suv suvr srtm srtm-bf"
quantMethods="lp  srtm "

#Run Quant
cmd_base="python ${appian_dir}/Launcher.py -s ${source_dir} -t ${target_dir} --start-time 7 --threads $threads --tka-label-img /APPIAN/Atlas/MNI152/dka.nii --quant-label 8 47 --quant-labels-ones-only --quant-label-erosion 3 --pvc-fwhm 2.5 2.5 2.5 "

cmd_quant="$cmd_base --tka-method suvr "
cmd_pvc="$cmd_quant" # --pvc-method VC "
echo docker run -v "$SCRIPTPATH":"/APPIAN" --rm $docker_image bash -c "$cmd_pvc"
docker run -v "$SCRIPTPATH":"/APPIAN" --rm $docker_image bash -c "$cmd_pvc"
exit 0

for quant in $quantMethods; do
	cmd_quant="$cmd_base --tka-method $quant "
	if [[ $use_docker != 0 ]]; then
		docker run -v "$SCRIPTPATH":"/APPIAN" --rm $docker_image bash -c "$cmd_quant"
	else
		bash -c "$cmd"
	fi 
	
	#Run PVC 
	for pvc in $pvcMethods; do
		echo Testing $pvc $quant	
		# Setup command to run APPIAN
		cmd_pvc="$cmd_quant --pvc-method $pvc "
		
		if [[ $use_docker != 0 ]]; then
			# Run command in docker container
			docker run -v "$SCRIPTPATH":"/APPIAN" --rm $docker_image bash -c "$cmd_pvc"
		else
			# Assumes you are already in an environment that can run APPIAN
			bash -c "$cmd_pvc"
		fi 
	done
done
