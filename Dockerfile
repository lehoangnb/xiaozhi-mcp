FROM python:3.14.0-slim-bookworm
WORKDIR /app
COPY requirements.txt .
COPY *.py .
RUN pip install -r requirements.txt
ENV MCP_ENDPOINT=""
ENV SERVER_PATH=""
CMD ["sh", "-c", "python mcp_pipe.py ${SERVER_PATH}"]
