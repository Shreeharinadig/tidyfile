FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY tidyfile_worker ./tidyfile_worker

CMD ["python", "-m", "tidyfile_worker.main"]
