FROM ubuntu:20.04
MAINTAINER Thomas Funck <t.funck@juelich-fz.de>


RUN mkdir /opt/bin /opt/lib /opt/include /opt/share
#ENV TZ=America/NewYork
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y
RUN apt-get install -y  g++ curl build-essential liblapack* git  wget openssl cmake cmake-curses-gui vim python3 python3-dev python3-distutils python3-setuptools zlibc zlib1g-dev libssl-dev zlib1g-dev unzip

# Add /opt/lib to library path
RUN echo "/opt/lib/" >> /etc/ld.so.conf.d/userLibraries.conf
RUN ldconfig

# Python packages
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py &&\
    python3 get-pip.py &&\
    pip3  install  networkx nipype keras nibabel pydot h5py numpy scipy configparser pandas matplotlib nibabel sklearn seaborn wget SimpleITK scikit-image pint webcolors &&\
    pip3 install --upgrade numpy

# Vim
RUN echo "syntax on" > /root/.vimrc &&\
    echo "set tabstop=4 shiftwidth=4 expandtab smartindent hlsearch " >> /root/.vimrc &&\
    echo set undofile undodir=~/.vim/undodir >> /root/.vimrc

### ANTsPy
#RUN pip3 install https://github.com/ANTsX/ANTsPy/releases/download/v0.1.4/antspy-0.1.4-cp36-cp36m-linux_x86_64.whl
RUN pip3 install webcolors
RUN pip3 install antspyx

# AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" &&\
            unzip awscliv2.zip &&\
            ./aws/install

# ANTs Scripts
RUN cd /opt/ &&\
    git clone https://github.com/stnava/ANTs.git &&\
    cp `find ANTs/ -name "*sh"` /opt/bin/ &&\
    rm -rf /opt/ANTs

# PETPVC
RUN wget https://github.com/UCL/PETPVC/releases/download/v1.2.4/PETPVC-1.2.4-Linux.tar.gz &&\
    tar -zxvf PETPVC-1.2.4-Linux.tar.gz &&\
    cp -r PETPVC-1.2.4/* /opt/ &&\
    rm -r PETPVC* 

#APPIAN
RUN cd /opt &&\
    git clone https://github.com/APPIAN-PET/APPIAN

RUN echo "python3 /opt/APPIAN/Launcher.py" > /opt/bin/appian

RUN useradd -ms /bin/bash user

RUN chown -R user:user /opt/bin/ && chmod 733 /opt/bin/*

USER user
# ENVIRONMENT VARIABLES
ENV PATH /opt/bin:$PATH
ENV ANTSPATH /opt/bin

