# helper/Dockerfile
FROM docker:27-cli

RUN apk add --no-cache bash jq

COPY update-helper.sh /update-helper.sh
RUN chmod +x /update-helper.sh

ENTRYPOINT ["/update-helper.sh"]
