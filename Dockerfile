from ubuntu:focal

RUN apt-get update && apt-get install locales git python3.8 python3-pip -qy && \
pip3 install --upgrade pip setuptools && \
if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
if [ ! -e /usr/bin/python ]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
rm -rf /var/lib/apt/lists/*

# Set the locale
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

WORKDIR /edx/app/hermes
ADD . /edx/app/hermes

RUN pip install -r requirements/pip_tools.txt
RUN pip install -r requirements/base.txt
