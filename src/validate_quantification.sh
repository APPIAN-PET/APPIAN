#!/bin/bash
dir=ds001705-download/
out=test #out_ds001705-download/
subs="000101" # 000103 000104 000105"
sess="baseline" # displaced"
methods="lp pp suv suvr" # srtm"
appian_path=${1:-"/opt/APPIAN/"}
echo $appian_path ; exit 0

if [[  -f "ds001705-download"  ]]; then
    echo aws s3 sync --no-sign-request s3://openneuro.org/ds001705 ds001705-download/
fi

python3 appian --dashboard  -s $dir -t $out --subjects $subs --sessions $sess  --no-qc --user-ants-command ${appian_path}/src/ants_command_quick.txt  --t1-session displaced

for method in $methods ; do
    for kind in  quant-roi quant-voxel ; do
        ###
        ### RUN APPIAN
        ###
        python3 ${appian_path}/Launcher.py  --dashboard -s $dir -t $out --subjects $subs --sessions $sess  --no-qc --user-ants-command ${appian_path}/src/ants_command_quick.txt --quant-label 2 --quant-method $method --start-time 300 --${kind} --quant-label-name "${method}${kind}" --arterial  --quant-label 8 48 --quant-label-img /opt/APPIAN/atlas/MNI152/dka.nii.gz --quant-label-erosion 5 --t1-session displaced
        exit 0
    done 
    exit 0
    for kind in quant-roi quant-voxel ; do
        python3 ${appian_path}/Launcher.py  -s $dir -t $out --subjects $subs --sessions $sess  --no-qc --user-ants-command ${appian_path}/src/ants_command_quick.txt --quant-label 2 --quant-method $method --start-time 300 --${kind} --quant-label-name "${method}${kind}" --quant-label 8 48 --quant-label-img /opt/APPIAN/atlas/MNI152/dka.nii.gz --quant-label-erosion 5
    done
done


