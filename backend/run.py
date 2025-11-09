import uvicorn
from title_annotator.config import config

if __name__ == "__main__":
    uvicorn.run("title_annotator.main:app", host="0.0.0.0", log_level="info")