FROM ubuntu:18.04
MAINTAINER Thomas Funck <thomas.funck@mail.mcgill.ca>


RUN mkdir /opt/bin /opt/lib /opt/include /opt/share
#ENV TZ=America/NewYork
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y g++ build-essential  git  wget openssl cmake cmake-curses-gui vim python3 python3-dev python3-pip zlibc zlib1g-dev libssl-dev zlib1g-dev curl ants

# Add /opt/lib to library path
RUN echo "/opt/lib/" >> /etc/ld.so.conf.d/userLibraries.conf
RUN ldconfig

# Turku
RUN mkdir /opt/turku /opt/turku/build /opt/turku/src &&\
    wget -O  /opt/turku/src.tar.gz https://www.dropbox.com/sh/l22cilo1ze25rj4/AAC96WoMUaigZk8DQJ9mZO1fa/tpcclib-0.7.1-Linux-x64.tar.gz?dl=1 &&\
    tar -zxf /opt/turku/src.tar.gz -C /opt/turku/src/ &&\
    mv  /opt/turku/src/bin/* /opt/bin/ &&\
    rm -rf /opt/turku

# Python packages
RUN pip3  install tensorflow networkx nipype keras nibabel pydot h5py numpy scipy configparser pandas matplotlib nibabel sklearn seaborn wget SimpleITK scikit-image webcolors

# Vim
RUN echo "syntax on" > /root/.vimrc &&\
    echo "set tabstop=4 shiftwidth=4 expandtab smartindent hlsearch " >> /root/.vimrc &&\
    echo set undofile undodir=~/.vim/undodir >> /root/.vimrc


# ANTs Scripts
RUN cd /opt/ &&\
    git clone https://github.com/stnava/ANTs.git &&\
    cp `find ANTs/ -name "*sh"` /opt/bin/ &&\
    pip3 install https://github.com/ANTsX/ANTsPy/releases/download/v0.1.4/antspy-0.1.4-cp36-cp36m-linux_x86_64.whl &&\
    rm -rf /opt/ANTs

# PETPVC
RUN wget https://github.com/UCL/PETPVC/releases/download/v1.2.4/PETPVC-1.2.4-Linux.tar.gz &&\
    tar -zxvf PETPVC-1.2.4-Linux.tar.gz &&\
    cp -r PETPVC-1.2.4/* /opt/ &&\
    rm -r PETPVC* 

#APPIAN
RUN cd /opt &&\
    git clone https://github.com/APPIAN-PET/APPIAN

RUN echo python3 /opt/APPIAN/Launcher.py > /opt/bin/appian.sh

ENV PATH /opt/bin:$PATH
ENV ANTSPATH /opt/bin


