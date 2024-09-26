# Jimo server

This is the server for the [Jimo iOS app](https://apps.apple.com/us/app/jimo-be-the-guide/id1541360118).

## Overview

This is a FastAPI server that uses Firebase for authentication and Postgres as a database. We use the PostGIS extension for geospatial functionality, such as map queries.

## Backend setup

1. Install [Postgres](https://www.postgresql.org/) and [PostGIS](https://postgis.net/) and create a new local database.
2. Take note of the database URL. It’ll be something like "postgresql://user@localhost/database_name".
3. Go to the [Firebase console](https://console.firebase.google.com/project/goodplaces-app/settings/serviceaccounts/adminsdk), click *Generate new private key* and *Generate key*. If you don't have access to the production project, create a new one.
4. Save the JSON file somewhere and optionally rename it. I’ve named mine `service-account-file.json`, and this is already in .gitignore (double check you don’t commit this file).
5. Set the environment variables. Set the `DATABASE_URL` environment variable to the database URL. We use an async db connection so you need to change `postgresql://` to `postgresql+asyncpg://`. Set `GOOGLE_APPLICATION_CREDENTIALS` to the path to the service account file.


## Running the server

1. (Optional) Create a virtual environment using pyenv, venv, or a similar tool, and activate it.
2. Install [Poetry](https://python-poetry.org/) here.
2. Run `poetry install`.
    - If you created a virtual environment, the dependencies will be installed to it; otherwise, poetry will create one for you.
3. Set the environment variables:


| Variable                         | Value|
|----------------------------------|---|
 | `DATABASE_URL`                   | Full database url (w/ credentials).|
 | `GOOGLE_APPLICATION_CREDENTIALS` | Path to the service account JSON file.|
 | `ALLOW_ORIGIN`                   | (Optional) Allow requests from the given host..|
 | `ENABLE_DOCS`                    | (Optional) If set to 1, enable the `/docs`, `/redoc`, and `/openapi.json` endpoints. Disabled by default.|
 | `STORAGE_BUCKET`                 | The Firebase storage bucket to save images to. Defaults to `goodplaces-app.appspot.com`. If you're using your own Firebase project, you need to set this.|

4. Run `python migrate.py` to set up the database tables.
5. Run `export ENABLE_DOCS=1` and then run `python runserver.py`.
6. View the docs at `http://localhost/docs` or `http://localhost/redoc`. OpenAPI definitions are available at `http://localhost/openapi.json`.


## Other commands

| Command                                        | Action|
|------------------------------------------------|---|
 | `flake8 .`                                     | Lint files|
 | `pytest`                                       | Run tests|
 | `alembic revision --autogenerate -m <message>` | Generate database migration (run this after <br /> changing the db schema). **IMPORTANT**: Double <br /> check the generated file (in `alembic/versions/`) <br /> to make sure the migration is correct. Alembic <br /> can't always generate the right migrations.|
 | `alembic upgrade head`                         | Run database migrations.|


## Backend overview

The backend is split up two main folders: `core` and `features`.

For every authenticated request, we receive an `authorization` header, which is a bearer token used to authenticate requests.
We use Firebase for auth and verify the token by checking it with them. If you're testing locally, you can modify this to disable auth.


## Contributing

While the app is no longer officially maintained, issues, feature requests, and contributions are welcome!
