.PHONY: help
help:  ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: docker-build
docker-build:  ## install required packages
	docker build -t webcrawler .

.PHONY: requirements
requirements:  ## install required packages
	pip install -r requirements.txt
	pip install -e ./

.PHONY: tests
tests:  ## run tests
	pip install pytest
	pytest ./tests
