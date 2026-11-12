# pull official base image
FROM python:3.9-slim-buster

# maintainers info
LABEL maintainer="info@samacontrol.com"

# set work directory
WORKDIR /usr/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip 
COPY ./requirements.txt .
RUN pip install -r requirements.txt 

# copy project
COPY ./core .