FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt frontend/requirements.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt -r frontend/requirements.txt

COPY . .

RUN mkdir -p /app/outputs

EXPOSE 8000

CMD ["python", "-m", "frontend.server"]
