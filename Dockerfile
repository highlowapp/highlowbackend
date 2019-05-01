FROM python:latest
RUN apt -y update && apt -y install libffi-dev
ADD ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt
ADD . /app
#ENTRYPOINT ["python3"]
ENV PORT=80
CMD gunicorn -w 4 -b 0.0.0.0:$PORT wsgi
