FROM gcr.io/google-appengine/python

RUN apt-get update && apt-get install -y python-opencv
RUN apt-get install -y poppler-utils
RUN virtualenv /env -p python3

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

ADD . /app

CMD gunicorn -b :$PORT api:app
