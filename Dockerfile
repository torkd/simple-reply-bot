FROM python:3.11.4-alpine
WORKDIR /bot
RUN pip install aiogram
COPY bot.py .
CMD ["python", "./bot.py"]