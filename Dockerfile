from ubuntu:bionic

RUN apt-get update && apt-get install locales=2.27-3ubuntu1 git python3.6 python3-pip -qy && \
pip3 install --upgrade pip setuptools && \
if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
if [ ! -e /usr/bin/python ]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
rm -rf /var/lib/apt/lists/*

RUN pip install pip-tools

# Set the locale
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

WORKDIR /edx/app/hermes
ADD requirements.txt /edx/app/hermes/requirements.txt
RUN pip install -r /edx/app/hermes/requirements.txt

ADD . /edx/app/hermes
