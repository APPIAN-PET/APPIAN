FROM ubuntu:20.04
MAINTAINER Thomas Funck <t.funck@juelich-fz.de>


RUN mkdir /opt/bin /opt/lib /opt/include /opt/share
#ENV TZ=America/NewYork
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y &&\
    apt-get install -y  g++ curl build-essential liblapack* git  wget openssl cmake cmake-curses-gui vim python3 python3-dev python3-distutils python3-setuptools zlibc zlib1g-dev libssl-dev zlib1g-dev unzip &&\
    echo "/opt/lib/" >> /etc/ld.so.conf.d/userLibraries.conf &&\
    ldconfig &&\
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py &&\
    python3 get-pip.py &&\
    pip3  install  networkx nipype keras nibabel pydot h5py numpy scipy configparser pandas matplotlib nibabel sklearn seaborn wget SimpleITK scikit-image pint webcolors antspyx &&\
    pip3 install --upgrade numpy &&\
    echo "syntax on" > /root/.vimrc &&\
    echo "set tabstop=4 shiftwidth=4 expandtab smartindent hlsearch " >> /root/.vimrc &&\
    echo set undofile undodir=~/.vim/undodir >> /root/.vimrc &&\
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" &&\
    unzip awscliv2.zip &&\
    ./aws/install &&\
    cd /opt/ &&\
    git clone www.github.com/stnava/ANTs.git &&\
    cp `find ANTs/ -name "*sh"` /opt/bin/ &&\
    rm -rf /opt/ANTs &&\
    wget https://github.com/UCL/PETPVC/releases/download/v1.2.4/PETPVC-1.2.4-Linux.tar.gz &&\
    tar -zxvf PETPVC-1.2.4-Linux.tar.gz &&\
    cp -r PETPVC-1.2.4/* /opt/ &&\
    rm -r PETPVC* &&\
    cd /opt &&\
    git clone https://github.com/APPIAN-PET/APPIAN &&\
    useradd -ms /bin/bash user &&\
    chown -R user:user /opt/bin/ && chmod 733 /opt/bin/*

# ENVIRONMENT VARIABLES
ENV APPIAN "python3 /opt/APPIAN/Launcher.py"
ENV PATH /opt/bin:$PATH
ENV ANTSPATH /opt/bin
