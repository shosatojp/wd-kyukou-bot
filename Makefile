# Web site
ROOTDIR=#/web/public
SOURCEDIR = ./web/public
MDS := $(shell find $(SOURCEDIR) -name '*.md')
HTMLS := $(MDS:%.md=%.html)
CSS = $(ROOTDIR)/templates/pandoc-md2html-template/template-light.css
TEMPLATE= ./web/public/templates/pandoc-md2html-template/template.html
# Server
WSGI_LOG=./log/uwsgi.log
APP_LOG=./log/kyukou.log
RELOAD_TRIGGER=./reload.trigger
SERVER_PORT=5426
MONGOD_PORT=8070
WSGI_FILE=./run_async.py

%.html:%.md FORCE
	pandoc $< --template=$(TEMPLATE) -c $(CSS) --mathjax -o $@ --highlight-style=tango

default: $(HTMLS)

clean:
	rm $(HTMLS)

reload: FORCE
	touch $(RELOAD_TRIGGER)

mongod:
	-kill -9 `lsof -t -i:$(MONGOD_PORT)` 2>/dev/null
	mkdir -p db
	nohup mongod --dbpath `pwd`/db --bind_ip localhost --port $(MONGOD_PORT) >/dev/null &

runasync: reload FORCE
	-kill -9 `lsof -t -i:$(SERVER_PORT)` 2>/dev/null
	nohup uwsgi --asyncio 100 --http-socket localhost:$(SERVER_PORT) --greenlet --processes 1 --threads 1 --logto $(WSGI_LOG) --wsgi-file $(WSGI_FILE) --touch-reload=$(RELOAD_TRIGGER) -L &

run: FORCE
	mkdir -p log
	-kill -9 `lsof -t -i:$(SERVER_PORT)` 2>/dev/null
	nohup python3 run.py &

stop:
	-kill -9 `lsof -t -i:$(SERVER_PORT)` 2>/dev/null
	-kill -9 `lsof -t -i:$(MONGOD_PORT)` 2>/dev/null

ab:
	ab -n $(if ${n},${n},1) $(if ${c},-c ${c}) http://localhost:$(SERVER_PORT)/

log: FORCE
	tail -f $(APP_LOG)

archive: FORCE
	mongodump --archive=archive/kyukou.`date +%Y-%m-%d-%H-%M-%S-%s`.mongo.archive --port $(MONGOD_PORT)

FORCE:;

# find  web/public/ -type d -exec chmod go+x {} \;
