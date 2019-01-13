FROM python:3.7

ENV PYTHONUNBUFFERED 1

WORKDIR /luovu

ADD . /luovu

RUN pip install -r requirements.txt

CMD [ "python", "manage.py", "runserver"]