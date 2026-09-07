FROM ubuntu:latest
LABEL authors="timyr"

ENTRYPOINT ["top", "-b"]