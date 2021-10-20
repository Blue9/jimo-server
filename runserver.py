import uvicorn

if __name__ == "__main__":
    print("Running server")
    uvicorn.run("app.main:app", reload=True, host="0.0.0.0", port=80)
