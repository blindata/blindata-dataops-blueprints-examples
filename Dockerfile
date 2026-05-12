FROM python:3.12-slim

WORKDIR /app

COPY application/pyproject.toml application/README.md ./
COPY application/src ./src
COPY application/transform_hook.py ./

RUN pip install --no-cache-dir -e .

COPY descriptor/ ./descriptor/

ENV PYTHONPATH=/app
ENV DESCRIPTOR_PATH=/app/descriptor/data-product-descriptor.json

CMD ["python", "-m", "src.main"]
