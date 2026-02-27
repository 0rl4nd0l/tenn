FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir git+https://github.com/harshkedia177/axon.git@f9c2f52b55a4ea478783eb83ec4d0663546bd2e1

WORKDIR /workspace
ENTRYPOINT ["axon"]
