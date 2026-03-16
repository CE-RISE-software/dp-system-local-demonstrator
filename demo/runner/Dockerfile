FROM alpine:3.21

RUN apk add --no-cache bash curl jq

WORKDIR /demo

COPY run-demo.sh /usr/local/bin/run-demo.sh

RUN chmod +x /usr/local/bin/run-demo.sh

ENTRYPOINT ["run-demo.sh"]
