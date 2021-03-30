FROM python:3.9

RUN mkdir /app

# App files
COPY /app /app
COPY runserver.py /
COPY migrate.py /

# Poetry files
COPY pyproject.toml /
COPY poetry.lock /

# Database migration files
COPY /alembic /alembic
COPY alembic.ini /

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

EXPOSE 80
CMD ["python", "runserver.py"]
