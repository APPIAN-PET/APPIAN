import os 
import re
import subprocess
from argparse import ArgumentParser

def cmd(command):
    try:
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True ) #,stderr=subprocess.STDOUT, shell=True,)
        while p.poll() is None:
            l = p.stdout.readline() # This blocks until it receives a newline.
            print(l,end="")
        exit(1)
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        exit(1)
    else:
        print("Output: \n{}\n".format(output))


file_dir, fn = os.path.split( os.path.abspath(__file__) )
SCRIPTPATH = '/'.join( file_dir.split('/')[0:-1]  )

version="ds001705" 
nrm=version+"-download"

####################
# Default Settings #
####################
appian_dir=SCRIPTPATH
source_dir=SCRIPTPATH+"/Test/"+nrm
target_dir=SCRIPTPATH+"/Test/out_"+nrm
singularity_image="APPIAN-PET/APPIAN:latest"

def useage():
	print( "Name :	quantitative_validation.sh")
	print( "About:	Evaluate quantitative accuracy of APPIAN using NRM2018 Grand Challenge Dataset.")
	print( "Options:")
	print( "		-a  		Set APPIAN directory where Launcher is located (default=$appian_dir)")
	print( "		-s 		Set source directory where NRM2018 data will be downloaded (default=$source_dir)")
	print( "		-t 		Set target directory where results will be saved (default=$target_dir)")
	print( "		-c 		Use singularity container (default=False)")
	print( "		-i 		Singularity image name (default=$singularity_image)")
	print( "		-r 		Number of threads to use (default=$threads)")
	print( "		-h 		Print this help menu")


if __name__ == '__main__' :
    ###################
    # Parse Arguments #
    ###################
    parser = ArgumentParser(usage="useage: ")
    parser.add_argument("-a","--appian-dir",dest="appian_dir",  help="Path for APPIAN directory file directory (Default="+appian_dir+")", default=appian_dir)
    parser.add_argument("-s","--source-dir",dest="source_dir",  help="Path for input directory file directory (Default="+source_dir+")", default=source_dir )
    parser.add_argument("-t","--target-dir",dest="target_dir",  help="Path for target directory file directory (Default="+target_dir+")", default=target_dir)
    parser.add_argument("-n","--no-container",dest="use_singularity", default=True, action='store_false', help="Path for target directory file directory" )
    parser.add_argument("-i","--singularity-image",dest="singularity_image",  help="Path for target directory file directory", default="APPIAN-PET-APPIAN-master-latest.simg")
    parser.add_argument("-r","--threads",dest="threads", default="1", type=str, help="Number of threads." )
    opts = parser.parse_args() 

    ##########################################
    # Download data from Amazon Web Services #
    ##########################################
    #	pip install awscli --upgrade --user > /dev/null && export PATH="${PATH}:/root/.local/bin/" > /dev/null
    #    aws s3 sync --no-sign-request s3://openneuro.org/$version $source_dir

    ##################
    # Run validation #
    ##################

    print() 
    print("Quantitative Validation Settings")
    print("-------------------------------")
    print(" APPIAN Directory : " + appian_dir)
    print(" Source Directory : " + source_dir)
    print(" Target Directory : " + target_dir)

    if opts.use_singularity :
        print(" Docker image : "+opts.singularity_image)
    else :
        print(" Threads : " + opts.threads)

    pvcMethods="idSURF VC"
    quantMethods="lp  srtm " #"lp lp-roi suv suvr srtm srtm-bf"

    #Run Quant
    #cmd_base="python3.6 ${appian_dir}/Launcher.py -s ${source_dir} -t ${target_dir} --start-time 7 --threads $threads --quant-label-img /opt/APPIAN/Atlas/MNI152/dka.nii.gz --quant-label 8 47 --quant-labels-ones-only --quant-label-erosion 3 --pvc-fwhm 2.5 2.5 2.5 "

    cmd_base="python3.6 "+opts.appian_dir+"/Launcher.py  -s "+opts.source_dir+" -t "+opts.target_dir + " --start-time 5 --threads "+ opts.threads+ " --analysis-space t1 --quant-label 2 --user-ants-command "+SCRIPTPATH+"/src/ants_command_quick.txt "
    cmd_quant=cmd_base + " --quant-method suvr "
    cmd_pvc=cmd_quant # --pvc-method VC "

    print(cmd_pvc)

    cmd("singularity exec -B "+SCRIPTPATH+":"+SCRIPTPATH+ " " + opts.singularity_image +" bash -c \""+ cmd_pvc+"\"")


    '''
    for quant in $quantMethods; do
            cmd_quant="$cmd_base --quant-method $quant "
            if [[ $opts.use_singularity != 0 ]]; then
                    singularity exec -B "$SCRIPTPATH":"/APPIAN" $singularity_image bash -c "$cmd_quant"
            else
                    bash -c "$cmd"
            fi 
            
            #Run PVC 
            for pvc in $pvcMethods; do
                    echo Testing $pvc $quant	
                    # Setup command to run APPIAN
                    cmd_pvc="$cmd_quant --pvc-method $pvc "
                    
                    if [[ $opts.use_singularity != 0 ]]; then
                            # Run command in singularity container
                            singularity exec -B "$SCRIPTPATH":"/APPIAN"  $singularity_image bash -c "$cmd_pvc"
                    else
                            # Assumes you are already in an environment that can run APPIAN
                            bash -c "$cmd_pvc"
                    fi 
            done
    done
    '''
