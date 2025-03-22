FROM python:3.9-slim

EXPOSE 8501

RUN apt-get update && apt-get install -y build-essential software-properties-common git ssh \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip3 install django pandas

ENTRYPOINT [ "python", "djangobase/manage.py", "runserver", "0.0.0.0:8501" ]
