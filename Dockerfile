FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY frontend/requirements.txt /app/frontend-requirements.txt

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt -r /app/frontend-requirements.txt

COPY . .

RUN mkdir -p /app/outputs

EXPOSE 8000

CMD ["python", "-m", "frontend.server"]
