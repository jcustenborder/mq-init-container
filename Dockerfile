FROM python:3.9-alpine

ADD source /opt/mq-init
WORKDIR /opt/mq-init
RUN pip install -r requirements.txt

ENTRYPOINT /opt/mq-init/entrypoint.sh