FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir .
RUN useradd -m hacknews
USER hacknews
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/healthz').status==200 else 1)" || exit 1
ENTRYPOINT ["hacknews"]
CMD ["serve"]
