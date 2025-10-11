FROM python:3.13-bookworm

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/app.py

ENTRYPOINT ["/app/app.py"]
CMD ["--help"]

