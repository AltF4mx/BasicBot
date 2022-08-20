FROM python:3.10.6-slim

WORKDIR $HOME/containers/TGModerBot

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "-m", "app"]