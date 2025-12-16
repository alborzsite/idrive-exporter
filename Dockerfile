FROM python:3.9-slim

WORKDIR /app

RUN pip install --no-cache-dir boto3==1.34.0 prometheus_client==0.19.0

COPY exporter.py .

EXPOSE 8000

CMD ["python", "-u", "exporter.py"]