FROM stefancepa995/clario-appian:base
MAINTAINER Thomas Funck <t.funck@juelich-fz.de>

RUN pip3 install --force --upgrade scipy numpy pint nibabel
#APPIAN
RUN cd /opt/APPIAN && git fetch --all && git reset --hard origin/dynamic-pet-integratio



