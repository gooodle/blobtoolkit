FROM ubuntu:20.04 as base_image

LABEL maintainer="blobtoolkit@genomehubs.org"
LABEL license="MIT"
LABEL version=$VERSION
ARG VERSION
ENV CONTAINER_VERSION=$VERSION

RUN apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get -y --no-install-recommends install \
    aria2 \
    build-essential \
    ca-certificates \
    dbus-x11 \
    firefox \
    firefox-geckodriver \
    git \
    rsync \
    ttf-mscorefonts-installer \
    wget \
    xvfb \
    x11-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /opt

RUN wget -P /usr/local/src https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /usr/local/src/Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda \
    && /opt/conda/bin/conda install -n base conda-libmamba-solver \
    && rm /usr/local/src/Miniconda3-latest-Linux-x86_64.sh

RUN mkdir -p /blobtoolkit \
    && useradd -m blobtoolkit

COPY env.yaml /tmp/env.yaml

COPY blobtoolkit-api-linux /blobtoolkit/blobtoolkit-api
COPY blobtoolkit-viewer-linux /blobtoolkit/blobtoolkit-viewer
COPY *-*-*.whl /tmp

WORKDIR /tmp

RUN chown -R blobtoolkit:blobtoolkit /blobtoolkit \
    && chmod 755 /blobtoolkit/blobtoolkit-api /blobtoolkit/blobtoolkit-viewer \
    && sed -i '/- blobtoolkit/d' /tmp/env.yaml
#    && git clone https://github.com/blobtoolkit/blobtoolkit \

WORKDIR /blobtoolkit

RUN mkdir -p /blobtoolkit/conf \
    && mkdir -p /blobtoolkit/data/assembly \
    && mkdir -p /blobtoolkit/data/reads \
    && mkdir -p /blobtoolkit/data/other \
    && mkdir -p /blobtoolkit/databases/busco \
    && mkdir -p /blobtoolkit/databases/ncbi_db \
    && mkdir -p /blobtoolkit/databases/ncbi_taxdump \
    && mkdir -p /blobtoolkit/databases/uniprot_db \
    && mkdir -p /blobtoolkit/datasets \
    && mkdir -p /blobtoolkit/output \
    && mkdir -p /nfs \
    && mkdir -p /lustre

RUN chown -R blobtoolkit:blobtoolkit /blobtoolkit \
    && chown -R blobtoolkit:blobtoolkit /nfs \
    && chown -R blobtoolkit:blobtoolkit /lustre

ARG CONDA_DIR=/opt/conda

RUN $CONDA_DIR/bin/conda env create --experimental-solver=libmamba -f /tmp/env.yaml \
    && $CONDA_DIR/bin/conda clean --all --yes

COPY setup.sh /blobtoolkit

RUN /blobtoolkit/setup.sh \
    && rm /blobtoolkit/setup.sh \
    && rm -r /tmp/*

USER blobtoolkit


# RUN echo ". $CONDA_DIR/etc/profile.d/conda.sh" >> ~/.bashrc

# RUN $CONDA_DIR/bin/conda install mamba -n base -c conda-forge

# RUN mkdir -p /blobtoolkit/.conda

# WORKDIR /blobtoolkit


ENV CONDA_DEFAULT_ENV $CONDA_DIR/envs/btk_env

ENV PATH /blobtoolkit:$CONDA_DEFAULT_ENV/bin:$PATH

ENV PYTHONPATH $CONDA_DEFAULT_ENV/lib/python3.9/site-packages:$PYTHONPATH

COPY startup.sh /blobtoolkit

EXPOSE 8000 8001 8080

CMD /blobtoolkit/startup.sh