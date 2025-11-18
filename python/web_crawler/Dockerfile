FROM python:3.13
WORKDIR /usr/local/app

# Python Environment
COPY . ./web_crawler/
RUN pip install -r ./web_crawler/requirements.txt
RUN pip install -e ./web_crawler
RUN chmod +x ./web_crawler/crawl.py

# Create user
RUN useradd app
USER app

# Arguments
ENV URL=https://www.barrierreef.org/the-reef/animals/manta-ray
ENV DEPTH=1

CMD python ./web_crawler/crawl.py --url ${URL} --depth ${DEPTH}