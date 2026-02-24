FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --upgrade pip wheel "poetry==2.1.2"
RUN poetry config virtualenvs.create false

COPY pyproject.toml ./ 
RUN poetry install

COPY ./.env ./
COPY ./app ./app
COPY main.py .
