# ------------------------------------------------------------
# StudyBuddy — container image (concept demonstrated: DEPLOYABILITY)
#
# Build:
#   docker build -t studybuddy .
#
# Run (pass your API key at runtime — it is NEVER baked into the image):
#   docker run -p 8000:8000 -e GOOGLE_API_KEY=your_key_here studybuddy
#
# Then open http://localhost:8000 for the ADK dev UI, or serve
# frontend/index.html separately for the custom interface.
# The same image can be pushed to Google Cloud Run or Agent Engine.
# ------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so Docker caches this layer between builds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent team, its MCP server, the API server, and the web UI.
COPY agents/ agents/
COPY mcp_server/ mcp_server/
COPY frontend/ frontend/
COPY server_main.py .

ENV GOOGLE_GENAI_USE_VERTEXAI=FALSE
ENV HOST=0.0.0.0
EXPOSE 8000

CMD ["python", "server_main.py"]
