# Goodplaces
Goodplaces App

## Backend setup

1. (Optional) Create a virtual environment using pyenv, venv, or a similar tool, and activate it.
2. In `server/`, run `poetry install` (you may need to install [Poetry](https://python-poetry.org/) first).
    - If you created a virtual environment, the dependencies will be installed to it; otherwise, poetry will create one for you.
3. Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path to the service account JSON file.
4. In `server/`, run `poetry run python runserver.py`. This will start the server with hot reloading turned on. If you are using your own virtual environment you can also just run `python runserver.py`.
5. If you want to generate test tokens, set the environment variable `FIREBASE_API_KEY`.