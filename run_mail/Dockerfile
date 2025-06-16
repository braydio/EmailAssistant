FROM python:3.11-slim
RUN pip install python-dotenv openai
COPY email_processor.py /app/
WORKDIR /app
CMD ["bash","-lc","python email_processor.py"]
