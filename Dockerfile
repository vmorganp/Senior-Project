from ubuntu

# make sure apt doesn't try to ask us stupid questions
ENV DEBIAN_FRONTEND=noninteractive

# apt install all the stuff we need
RUN apt-get update && apt-get install -y \
    wget \
    zip \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# copy all of our files into home (realistically TODO this should be paired down a bit)
COPY ./* /home/

# install our python requir.ements
RUN pip3 install -r /home/requirements.txt
WORKDIR /home