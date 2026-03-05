FROM alpine:3.20
RUN apk add --no-cache bash curl docker-cli jq
COPY scripts/acorn-warden.sh /usr/local/bin/acorn-warden.sh
RUN chmod +x /usr/local/bin/acorn-warden.sh
CMD ["/usr/local/bin/acorn-warden.sh"]
