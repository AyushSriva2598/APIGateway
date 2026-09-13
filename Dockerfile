FROM python:3.12-slim

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

COPY gateway/ .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "config.wsgi"]
# CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "config.wsgi"]