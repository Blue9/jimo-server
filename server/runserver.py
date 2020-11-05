import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
