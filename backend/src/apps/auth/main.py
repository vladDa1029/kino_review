from fastapi import FastAPI
from app.presentations.api import router as auth_router

if __name__=="__main__":
    app= FastAPI()
    app.include_router(auth_router)