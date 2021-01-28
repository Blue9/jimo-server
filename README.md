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
2. In `server/`, run `poetry install` (you may need to install [Poetry](https://python-poetry.org/) first).
    - If you created a virtual environment, the dependencies will be installed to it; otherwise, poetry will create one for you.
3. Set the environment variables:

Variable | Value
---|---
`DATABASE_URL` | Full database url (w/ credentials)
`GOOGLE_APPLICATION_CREDENTIALS` | path to the service account JSON file
`FIREBASE_API_KEY` | (Optional) Firebase API key (only required if you need to generate test tokens)


4. In `server/`, run `poetry run python runserver.py`. This will start the server with hot reloading turned on. If you are using your own virtual environment you can also just run `python runserver.py`.


## Running the frontend

1. Open the Xcode project.
2. Make sure the server is running.
3. In APIClient.swift change `apiURL.host` to your local IP address the server is running on (this should probably be in a plist but this works for now)
3. Run!
