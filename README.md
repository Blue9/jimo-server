# jimo

## Backend setup

1. Install [Postgres](https://www.postgresql.org/) and [PostGIS](https://postgis.net/) and create a new local database
    - [This](https://www.postgresql.org/docs/9.1/tutorial-createdb.html) and [this](https://postgis.net/install/) (see *Enabling PostGIS*) should be useful for that.

2. Take note of the database URL. It’ll be something like "postgresql://user@localhost/database_name"
3. Go to the [Firebase console](https://console.firebase.google.com/project/goodplaces-app/settings/serviceaccounts/adminsdk), click *Generate new private key* and *Generate key*,
4. Save the JSON file somewhere and optionally rename it. I’ve named mine `service-account-file.json`, and this is already in .gitignore so you could use that if you save it in the project directory (double check you don’t commit this file).
5. Set the `DATABASE_URL` environment variable to the database URL and `GOOGLE_APPLICATION_CREDENTIALS` to the path to the service account file.

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
 | `ALLOW_ORIGIN`                   | (Optional) Allow requests from the given host. Can be set to `*`.|
 | `ENABLE_DOCS`                    | (Optional) If set to 1, enable the `/docs`, `/redoc`, and `/openapi.json` endpoints. Disabled by default.|
 | `STORAGE_BUCKET`                 | The Firebase storage bucket to save images to. Defaults to `goodplaces-app.appspot.com`.|

4. Run `python migrate.py`.
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

For every request, we receive an `authorization` header and a `db` object. The `authorization` header is a bearer token used to authenticate requests. We use Firebase for auth and verify the token by checking it with them.

We also define a response model for every request (see the `response_model` param for each route). This is usually a Pydantic model, and when you return an object from a route, FastAPI will try to automatically parse it to the given Pydantic type. This is useful because Pydantic lets us define validators on our types, so we can make sure that the data we return to a user is valid. We also do this for some requests, where the body is a Pydantic type so we can easily validate the request.
