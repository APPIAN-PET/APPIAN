
dir=ds001705-download/
out=out_ds001705-download/
subs="000101 000102" # 000103 000104 000105"
sess="baseline" # displaced"
methods="lp pp" #srtm
#container=APPIAN-PET-APPIAN-master-latest.simg
appian_path="/home/t/neuro/projects/APPIAN-PET/APPIAN/"

#if [[ ! -f $container ]]; then
#    singularity pull shub://APPIAN-PET/APPIAN:latest
#fi

if [[ ! -f ds001705-download/  ]]; then
    aws s3 sync --no-sign-request s3://openneuro.org/ds001705 ds001705-download/
fi

for method in $methods ; do
    for kind in "quant-roi " ; do #--quant-roi
        ###
        ### RUN APPIAN
        ###
        singularity exec -B `pwd`/../:`pwd`/../   $container bash -c  "python3 ${appian_path}/Launcher.py  -s $dir -t $out --subjects $subs --sessions $sess  --no-qc --user-ants-command ${appian_path}/src/ants_command_affine.txt"
        exit 0
        singularity exec -B `pwd`/../:`pwd`/../   $container bash -c  "python3 ${appian_path}/Launcher.py  -s $dir -t $out --subjects $subs --sessions $sess  --no-qc --user-ants-command ${appian_path}/src/ants_command_affine.txt --quant-label 2 --quant-method $method --start-time 300 --$kind --quant-label-name "${method}${kind}" --quant-label 8 48 --quant-label-img /opt/APPIAN/atlas/MNI152/dka.nii.gz --quant-label-erosion 5 "
        exit 0

        mkdir -p turku
        for sub in $subs; do
            for ses in $sess; do
                ###
                ### UNZIP NIFTI FILES FOR TURKU TOOLS
                ###
                for pet_gz in `find $dir -name "*${sub}*${ses}*_pet.nii.gz"`; do
                    gunzip -fk $pet_gz
                done

                for roi_gz in `find ${out}/preproc/masking/ -name "*.nii.gz"`; do
                    gunzip -fk $roi_gz
                done
                

                ###
                ### RUN TURKU TOOLS
                ###
                pet=`find $dir -name "*sub-$sub*${ses}*_pet.nii"`
                roi=`find ${out}/preproc/masking/*/resultsLabels -name "*.nii"`
                ref=`find ${out}/preproc/masking/*/quantLabels -name "*.nii"`

                pet_roi=turku/`basename ${pet%.*}_roi.dft`
                pet_ref=turku/`basename ${pet%.*}_ref.dft`

                pet_dvr_dft=turku/`basename ${pet%.*}_dvr.dft`
                pet_dvr_img=turku/`basename ${pet%.*}_dvr.nii`

                pet_ki_dft=turku/`basename ${pet%.*}_ki.dft`
                pet_ki_img=turku/`basename ${pet%.*}_ki.nii`
                 
                python3 ../src/json_to_sif.py $pet ${pet%.*}.json ${pet%.*}.sif
                img2dft $pet $roi $pet_roi
                img2dft $pet $ref $pet_ref
                cat $pet_roi
                cat $pet_ref
                echo $kind
                if [[ $method == "lp" ]]; then
                    logan  -C $pet_roi $pet_ref 5.0 90.0 $pet_dvr_dft
                    if [[ $kind == "quant-roi" ]]; then
                        echo logan $pet_roi $pet_ref 5.0 90.0 $pet_dvr_dft
                    else 
                        echo imgdv $pet_ref $pet 5.0  $pet_dvr_img
                    fi
                elif [[ $method == "pp" ]]; then
                    if [[ $kind == "quant-roi" ]]; then
                        patlak $pet_roi $pet_ref 5.0 90.0 $pet_ki_dft
                    else
                        imgki $pet_ref $pet 5.0  $pet_ki_img
                    fi
                fi
                #register out_ds001705-download/quant/task-.sesbaseline.sid000101./sub-000101_ses-baseline_rec-MLEM_pet_quant-lp.nii.gz turku/sub-000101_ses-baseline_rec-MLEM_pet_dvr.nii
                exit 0
                
           done
        done
    done
done


