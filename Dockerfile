FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
# data/ is the small sample the tests and the tour use. data-live/ is the
# real run: project 01's invoices and project 02's scores. The panel serves
# the real one.
COPY data ./data
COPY data-live ./data-live

ENV PYTHONPATH=/app/src
ENV PAYABLES_DATA=/app/data-live

EXPOSE 8000

CMD ["uvicorn", "web:app", "--host", "0.0.0.0", "--port", "8000"]
