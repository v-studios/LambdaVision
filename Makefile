DSTDIR        = lambdavision
VENV          = /tmp/venv3
PIP           = $(VENV)/bin/pip
PYTHON        = $(VENV)/bin/python
SITE_PACKAGES = $(VENV)/lib/python3.6/site-packages

# The `all` target must be done outside the docker box
#
# We map the local `lambdavision` subdir to Docker's default run dir,
# `/var/task`; after the files are built in docker, they are copied to
# `/var/task`, so they will become part of the lambdavision package
# shipped by Serverless to Lambda.

all: $(DSTDIR)
	docker run --rm -v "${PWD}":/var/task lambci/lambda:build-python3.6 make --debug lambda_packages

# The packages below are built in the lambci docker box
#
# The build is done in a virtual environment outside of the
# `/var/task` directory, in Docker's `~` directory (`/root`) to avoid
# polluting the contents we ship to Lambda.
#
# DANGER: Compiling pytorch ran out of memory with Mac docker default
# 2g, increase to 4g with menu bar tool, see
# https://docs.docker.com/docker-for-mac/
#
# TODO:
# - Since this is a throw-away build box we probably don't need a virtualenv

lambda_packages: $(VENV) $(DSTDIR)/PIL $(DSTDIR)/Cython $(DSTDIR)/cython.py $(DSTDIR)/pyximport $(DSTDIR)/numpy-1.13.3-py3.6-linux-x86_64.egg  $(DSTDIR)/torch $(DSTDIR)/torchvision

$(VENV) $(PIP) $(PYTHON): 
	virtualenv $(VENV)

# Yaml is needed to build but not to run
yaml: $(PIP)
	$(PIP) install pyyaml

PIL: $(PIP)
	$(PIP) install Pillow
	cp -r $(SITE_PACKAGES)/PIL $(DSTDIR)/

Cython cython.py pyximport: $(PIP)
	$(PIP) install cython
	cp -r $(SITE_PACKAGES)/Cython    $(DSTDIR)/
	cp -r $(SITE_PACKAGES)/cython.py $(DSTDIR)/
	cp -r $(SITE_PACKAGES)/pyximport $(DSTDIR)/

# git checkout is for latest release
numpy-1.13.3-py3.6-linux-x86_64.egg: $(PYTHON) Cython cython.py pyximport
	cd /tmp && \
	git clone --recursive https://github.com/numpy/numpy.git && \
	cd numpy && \
	git checkout 31465473c491829d636c9104c390062cba005681 && \
	$(PYTHON) setup.py install
	cp -r $(SITE_PACKAGES)/numpy-1.13.3-py3.6-linux-x86_64.egg $(DSTDIR)/

# yum install is for pytorch build dependencies
# turn off && CUD* to reduce size
torch: $(PYTHON) yaml numpy-1.13.3-py3.6-linux-x86_64.egg
	echo NOT DOING YUM IS IT NEEDED yum install cmake make automake gcc gcc-c++ kernel-devel
	cd /tmp && \
	git clone --recursive https://github.com/pytorch/pytorch.git && \
	cd pytorch && \
	git checkout af3964a8725236c78ce969b827fdeee1c5c54110 && \
	export NO_CUDA=1 && \
	export NO_CUDNN=1 && \
	$(PYTHON) setup.py install
	cp -r $(SITE_PACKAGES)/torch $(DSTDIR)/

torchvision: $(PIP) torch
	$(PIP) install torchvision
	cp -r $(SITE_PACKAGES)/torchvision $(DSTDIR)/

