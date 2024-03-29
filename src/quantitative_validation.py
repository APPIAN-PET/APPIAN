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
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
    else:
        pass
        #print("Output: \n{}\n".format(exc.output))


file_dir, fn = os.path.split( os.path.abspath(__file__) )
SCRIPTPATH = '/'.join( file_dir.split('/')[0:-1]  )

version="ds001705" 
nrm=version+"-download"

####################
# Default Settings #
####################
appian_dir=SCRIPTPATH
source_dir = os.getcwd() + '/' + nrm
target_dir = os.getcwd() + '/' +"out_"+nrm
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
    
    if not os.path.exists(opts.source_dir) :
        os.makedirs(opts.source_dir)
        #cmd('pip3 install awscli --user') #> /dev/null && export PATH="${PATH}:/root/.local/bin/" > /dev/null]))
        aws_cmd=' '.join(['aws s3 sync --no-sign-request s3://openneuro.org/'+version,opts.source_dir])
        print(aws_cmd)
        cmd( aws_cmd )
    
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

    pvc_methods = ['--pvc-method VC', '--pvc-method GTM']
    quand_methods=['--quant-method suvr', '--quant-method lp', '--quant-method lp-roi',
                    '--quant-method pp', '--quant-method pp-roi']
    subs="000101 000102"
    sess="baseline"

    #Run Quant
    cmd_base="python3 "+opts.appian_dir+"/Launcher.py  -s "+opts.source_dir+" -t "+opts.target_dir + "  --subjects "+subs+" --sessions "+ sess +" --no-qc --user-ants-command "+appian_dir+"/src/ants_command_affine.txt  --start-time 5 --threads "+ opts.threads+ " --analysis-space t1 --quant-label 2 --user-ants-command "+SCRIPTPATH+"/src/ants_command_quick.txt "
    for quant in quand_methods :
        cmd_quant=cmd_base + quant
        print(cmd_quant)
        cmd(cmd_quant)
        print("\n\n\n\n\n\n\n\n")
        
    for pvc in pvc_methods :
        cmd_pvc = f'{cmd_base} --fwhm 2.5 2.5 2.5 --quant-method suvr {pvc}'
        print(cmd_pvc)
        cmd(cmd_pvc)
        print("\n\n\n\n\n\n\n\n")

    cmd_qc="python3 "+opts.appian_dir+"/Launcher.py  -s "+opts.source_dir+" -t "+opts.target_dir + "  --subjects "+subs+" --sessions "+ sess +" --user-ants-command "+appian_dir+"/src/ants_command_affine.txt  --start-time 5 --threads "+ opts.threads+ " --analysis-space t1 --quant-label 2 --user-ants-command "+SCRIPTPATH+"/src/ants_command_quick.txt --pvc-method VC --quant-method lp "
    cmd(cmd_qc)

