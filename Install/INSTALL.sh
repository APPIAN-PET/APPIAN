#!/bin/bash
###Options
Downloads="/home/${USER}/Downloads/"
pip_install="${Downloads}/get-pip.py"
packages="python2.7 python2.7-dev python3.5 python3.5-dev ipython python-numpy
	  python-scipy python-pandas cmake ccmake cmake-curses-gui git
	  perl bison flex libxmu-dev libxmu6 libxmu-headers libxi6 libxi-dev zlibc zlib1g-dev cython graphviz"

##########################
### 1) Ubuntu pacakges ###
##########################
#Install basic ubuntu libraries
#sudo apt-get update
#sudo apt-get upgrade
#sudo apt-get install $packages

#################################
### 2) Setup python libraries ###
#################################
#Install pip
if [ ! -f get-pip.py ]; then
	wget https://bootstrap.pypa.io/get-pip.py  
fi
if [ ! -f `which pip` ]; then
	sudo python2.7 get-pip.py
fi

sudo pip2.7  install nipype nibabel pydot plus


#####################################
### 3) Install Turku PET software ###
#####################################
#Installation directories:
turku_dir="/usr/local/turku"
turku_bin="/usr/local/turku/bin"
turku_lib="/usr/local/turku/lib"
turku_include="/usr/local/turku/include"
#Name of src file:
src="tpcclib-0.6.0-src"
src_tgz="${src}.tar.gz"
build="tpcclib-0.6.0-build"
install="v1_install"
src_dir="${Downloads}/${src}"
build_dir="${Downloads}/${build}"

cd $Downloads
#If compressed source does not exist, download it
if [ ! -f $src_tgz ]; then
	#Download source code
	echo Hello
	wget https://www.dropbox.com/sh/l22cilo1ze25rj4/AACf8gLJ3BXP0A6vAXzAUfX7a/${src_tgz}
fi

#Make directory for source code
if [ ! -d $src_dir ]; then
	mkdir $src_dir
fi

cd $src_dir
#If source has not been unzipped, then unzip it
if [ ! -f $src_dir/"CMakeLists.txt" ]; then
	tar -zxf ${Downloads}/$src_tgz
fi

#If build directory for tccp libraries does not exist, create it
if [ ! -d $build_dir ]; then
	mkdir $build_dir
fi

#Build and compile the turku programs
if [ ! -f "$build_dir/v1/mtga/imgki" ]; then #FIXME: Not a good test to check if make was run
	cd $build_dir
	cmake -D CMAKE_INSTALL_PREFIX:STRING=$turku_dir $src_dir
	make
	sudo make install
fi

#Update PATH environmental variable to add path for Turku binaries
export_line="export PATH=\$PATH:$turku_bin"
export_line_count=`grep -c "$export_line" ~/.bashrc `
if [[ $export_line_count == 0 ]]; then
	cp ~/.bashrc ~/.bashrc_bkp
	echo  $export_line >> ~/.bashrc
	source ~/.bashrc #Also needs to be run outside script or else PATH changes won't stick
fi

##########################################
### 4) Install MINC libraries from Git ###
##########################################
cd $Downloads
minc_dir="$Downloads/minc"
minc_version="minc-toolkit-v2"
minc_src="${minc_dir}/${minc_version}"
minc_build="${minc_dir}/${minc_version}-build"
minc_install="/usr/local/minc"
minc_bin="${minc_install}/bin"

if [ ! -d $minc_dir ]; then
	mkdir $minc_dir
fi

if [ ! -d ${minc_dir}/.git ]; then
	cd $minc_dir
	git init
fi

if [ ! -d $minc_src ]; then
	cd $minc_dir
	git clone  --recursive  https://github.com/BIC-MNI/${minc_version}.git
fi

if [ ! -d $minc_build ]; then
	mkdir $minc_build
fi

if [ ! -d $minc_install ]; then
	sudo mkdir $minc_install
fi


if [ ! -d ${minc_build}/CMakeFiles ]; then
	cd $minc_build
	cmake -D CMAKE_BUILD_TYPE:STRING=Release -D CMAKE_INSTALL_PREFIX:STRING=$minc_install -D LINKER_FLAG:STRING=-lz $minc_src
fi

if [ ! -f ${minc_install}/bin/mincmath ]; then
	make
	sudo make install
fi

#Update PATH environmental variable to add path for Turku binaries
export_line="export PATH=\$PATH:$minc_bin"
export_line_count=`grep -c "$export_line" ~/.bashrc `
if [[ $export_line_count == 0 ]]; then
	cp ~/.bashrc ~/.bashrc_bkp
	echo  $export_line >> ~/.bashrc
	source ~/.bashrc #Also needs to be run outside script or else PATH changes won't stick
fi

####################################
### 5) Install pyezminc from Git ###
####################################
pyezminc_dir="${Downloads}/pyezminc"
pyezminc_build="${Downloads}/pyezminc-build"

if [ ! -d $pyezminc_dir ]; then
	git clone --recursive https://github.com/BIC-MNI/pyezminc.git
	sed -i "s#/opt/minc#/usr/local/minc#" "${pyezminc_dir}/setup.py"
	sed -i "s#'minc_io']#'minc_io','hdf5','netcdf','z','znz', 'niftiio']#" "${pyezminc_dir}/setup.py" 
	cd $pyezminc_dir
	sudo python "${pyezminc_dir}/setup.py" install
fi


#FIXME: have to add library paths to /etc/ld.cond.d



######################################
### 7) Install tka nipype from Git ###
######################################
tka_nipype_dir="${Downloads}/tka_nipype" 
nipype_dir="/usr/local/lib/python2.7/dist-packages/nipype/"
minc_filemanip="${nipype_dir}/utils/minc_filemanip.py"

cd ${Downloads}
if [ ! -d $tka_nipype_dir ]; then
	git clone https://tfunck@bitbucket.org/klarcher/tka_nipype.git
fi

if [ ! -f $minc_filemanip ]; then
	sudo ln -s "${tka_nipype_dir}/minc_filemanip.py" $minc_filemanip
	
fi

if [ ! -f ${nipype_dir}/interfaces/minc/smooth.py ]; then
	sudo mv "${nipype_dir}/interfaces/minc" "${nipype_dir}/interfaces/.minc_bkp"
	sudo ln -s "${tka_nipype_dir}/nipype.bk/interfaces/minc" "${nipype_dir}/interfaces/minc" 
fi







