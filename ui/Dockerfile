FROM python:3.12-slim
WORKDIR /ui
RUN pip install --no-cache-dir streamlit==1.40.* httpx==0.27.*
COPY ui/app.py .
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
