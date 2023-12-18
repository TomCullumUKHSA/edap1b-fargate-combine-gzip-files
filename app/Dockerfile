FROM public.ecr.aws/ubuntu/ubuntu:20.04

WORKDIR /tmp

COPY requirements.txt ./

# install required dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    curl \
    python3-pip \
    unzip && \
    rm -rf /var/lib/apt/lists/*

# install packages needed by python
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

# install local dependencies
RUN for module in modules/*/; do pip install --no-cache-dir "$module"; done

# set AWS default region
ENV AWS_DEFAULT_REGION=eu-west-2

CMD ["python3", "app.py"]
