FROM arm32v7/python:3

RUN mkdir -p /bidenbot/

ENV VENV /bidenbot/

ADD requirements.txt /bidenbot/requirements.txt

RUN python3 -m venv $VENV && \
    pip3 install --upgrade pip && \
    pip3 install --upgrade setuptools && \
    pip3 install -r /bidenbot/requirements.txt && \
    rm -rf ~/.cache/pip

ENTRYPOINT []
