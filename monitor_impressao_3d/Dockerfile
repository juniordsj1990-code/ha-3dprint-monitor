ARG BUILD_FROM
FROM $BUILD_FROM

RUN pip3 install --no-cache-dir requests

WORKDIR /app
COPY run.sh /
COPY monitor.py /app/monitor.py

RUN chmod +x /run.sh

CMD ["/run.sh"]
