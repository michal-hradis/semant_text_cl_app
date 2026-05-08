FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app
EXPOSE 8002
ENV PORT=8002
CMD ["python", "run.py"]
