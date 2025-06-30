FROM python:3.11-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --upgrade pip wheel "poetry==2.1.2"

RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

RUN poetry install

COPY ./.env .

COPY ./src ./src

COPY ./migrations ./migrations
CMD ["poetry","run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]