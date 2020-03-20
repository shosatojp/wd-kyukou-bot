FROM ubuntu:18.04
RUN apt-get update && apt-get install -y python3.8 pandoc python3-pip git
RUN pip3 install --upgrade pip
RUN pip3 install pymongo bs4 requests pyyaml greenlet
RUN CFLAGS="-I/usr/local/include/python3.6/" UWSGI_PROFILE="asyncio" pip3 install uwsgi

# RUN git clone https://github.com/shosatojp/wd-kyukou-bot.git
# COPY . wd-kyukou-bot
CMD python3 wd-kyukou-bot/run.py