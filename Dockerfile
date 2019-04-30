FROM python:rc-stretch
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN apt -y update && apt -y install git
ENTRYPOINT ["python"]
ENV PORT=80
CMD gunicorn -w 4 -b 0.0.0.0:$PORT wsgi