#!/bin/bash
subs="000101" # 000103 000104 000105"
sess="baseline" # displaced"
methods="lp pp suv suvr" # srtm"
appian_path=${1:-"/opt/APPIAN/"}
data_path=${2:-"/"}
dir=${data_path}/ds001705-download/
out=${data_path}/test #out_ds001705-download/

if [[ !  -d $data_path  ]]; then
    echo Run following command
    echo aws s3 sync --no-sign-request s3://openneuro.org/ds001705 ds001705-download/
    exit 0
fi

python3 ${appian_path}/Launcher.py  --subjects $subs --sessions $sess -s $dir -t $out --no-qc --user-ants-command ${appian_path}/src/ants_command_quick.txt # --t2-session displaced #  --mri-preprocess-exit

#python3 ${appian_path}/Launcher.py --dashboard  -s $dir -t $out --subjects $subs --sessions $sess  --no-qc --user-ants-command ${appian_path}/src/ants_command_quick.txt  --t1-session displaced

for method in $methods ; do
    for kind in  quant-roi quant-voxel ; do
        ###
        ### RUN APPIAN
        ###
        python3 ${appian_path}/Launcher.py  --dashboard -s $dir -t ${out}_${kind}_${method} --subjects $subs --sessions $sess  --no-qc --user-ants-command ${appian_path}/src/ants_command_quick.txt --quant-label 2 --quant-method $method --start-time 300 --${kind} --quant-label-name "${method}${kind}" --quant-label 8 48 --quant-label-img /opt/APPIAN/atlas/MNI152/dka.nii.gz --quant-label-erosion 5 --t1-session displaced
    done 

    #for kind in quant-roi quant-voxel ; do
    #    python3 ${appian_path}/Launcher.py  -s $dir -t $out --subjects $subs --sessions $sess  --no-qc --user-ants-command ${appian_path}/src/ants_command_quick.txt --quant-label 2 --quant-method $method --start-time 300 --${kind} --quant-label-name "${method}${kind}" --quant-label 8 48 --quant-label-img /opt/APPIAN/atlas/MNI152/dka.nii.gz --quant-label-erosion 5
    #done
done


