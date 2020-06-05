FROM gcr.io/google-appengine/python

RUN apt-get update && apt-get install -y python-opencv
RUN virtualenv -p python3 /env 

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

ADD . /app
RUN pip install -r /app/requirements.txt


