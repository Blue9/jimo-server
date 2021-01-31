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

4. (One-time setup) In `server/`, run `poetry run python init_db.py`. This will set up all the database tables. If you are using your own virtual environment you can also just run `python init_db.py`.
5. In `server/`, run `poetry run python runserver.py`. This will start the server with hot reloading turned on. If you are using your own virtual environment you can also just run `python runserver.py`.


## Running the frontend

1. Run `pod install` in `Jimo/`. You need to install [CocoaPods](https://cocoapods.org/) for this.
2. Open the Xcode project (open the `.xcworkspace` file).
3. Make sure the server is running.
4. In APIClient.swift change `apiURL.host` to your local IP address the server is running on (this should probably be in a plist but this works for now)
5. Run!

## Backend overview

The backend is split up into three parts, `models/`, `routers/`, and `controllers/`. Models include the database tables and request and response types. We use SQLALchemy to define the database types and [Pydantic](https://pydantic-docs.helpmanual.io/) to define the request and response types (this comes with FastAPI). Routers define the endpoints and are handled by FastAPI. Controllers connect models to routers and handle request logic.

For every request, we receive an `authorization` header and a `db` object. The `authorization` header is a bearer token used to authenticate requests. Since we use Firebase for auth we can verify the token by checking it with Firebase (see `controllers/auth.py`). The `db` object is a SQLAlchemy session that lets us interact with the database. For example, if we wanted to get the user with the username `gautam` (or `None` if no such user exists) we could do `db.query(User).filter(User.username == "gautam").first()`.

We also define a response model for every request (see the `response_model` param for each route). This is usually a Pydantic model, and when you return an object from a route, FastAPI will try to automatically parse it to the given Pydantic type. This is useful because Pydantic lets us define validators on our types, so we can make sure that the data we return to a user is valid. We also do this for some requests, where the body is a Pydantic type so we can easily validate the request.
