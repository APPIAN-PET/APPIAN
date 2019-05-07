target_dir=$1
qc_dir=$2
mkdir -p $qc_dir

for f in `find ${out_data_path}/validation_output -name "*.mnc"`; do
	var1=`stat $f | grep Modify | awk '{split($0,ar," "); print ar[2] ar[3] }'`
	f2=${qc_dir}/`basename $f | sed "s/.mnc/_${var1}.png/"`
	if [[ ! -f $f2 ]] ; then
		python ${base_path}/Test/validation_qc.py $f $f2 2> /dev/null
	fi
done


