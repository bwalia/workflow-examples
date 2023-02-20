FROM alpine:3.14

RUN apk add bash
RUN apk add aws-cli
RUN apk add git
RUN apk add terraform
RUN apk add openssh-keygen

COPY / /

ENTRYPOINT ["bash", "kickstart_tf.sh"]
