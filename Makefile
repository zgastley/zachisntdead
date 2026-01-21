PY=python3

.PHONY: all build md site

all: build

md:
	$(PY) build_markdown.py

build:
	$(PY) build.py

site: md build
