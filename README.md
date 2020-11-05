# Goodplaces
Goodplaces App

## Backend setup

1. (Optional) Create a virtual environment using pyenv, venv, or a similar tool, and activate it.
2. In `server/`, run `poetry install` (you may need to install [Poetry](https://python-poetry.org/) first).
    - If you created a virtual environment, the dependencies will be installed to it; otherwise, poetry will create one for you.
3. In `server/`, run `poetry run python runserver.py`. This will start the server with hot reloading turned on. If you are using your own virtual environment you can also just run `python runserver.py`.
