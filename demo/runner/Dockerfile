FROM alpine:3.21

RUN apk add --no-cache bash curl jq python3

WORKDIR /demo

COPY run-demo.sh /usr/local/bin/run-demo.sh
COPY see_impacts_demo.py /usr/local/bin/see_impacts_demo.py

RUN chmod +x /usr/local/bin/run-demo.sh

ENTRYPOINT ["run-demo.sh"]
