FROM python:3.9

RUN mkdir /app

COPY /app /app
COPY pyproject.toml /
COPY poetry.lock /

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

EXPOSE 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
