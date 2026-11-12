# pull official base image
FROM python:3.9-slim-buster 

# maintainers info
LABEL maintainer="info@samacontrol.com"

# installing dependencies
# RUN apk add --update --virtual .build-deps \
#     build-base \
#     postgresql-dev \
#     python3-dev \
#     libpq


# install dependencies
RUN pip install  --upgrade pip 
COPY ./requirements.txt .
RUN pip install  -r requirements.txt 

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# copy project
COPY ./core .

# running project
CMD python3 manage.py collectstatic --no-input 