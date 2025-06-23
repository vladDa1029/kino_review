from logging import getLogger
from fastapi import FastAPI

from settings.loger import set_log

set_log()

app = FastAPI()
log = getLogger(__name__)


@app.get("/", tags=["dev"])
def hell_word():
    return {"message": "hello word"}


if __name__ == "__main__":
    import uvicorn
    log.info("Run app")
    uvicorn.run(app)
    log.info("Stop app")
