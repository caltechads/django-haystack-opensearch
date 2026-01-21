VERSION = 1.0.0

PACKAGE = django-haystack-opensearch

#======================================================================


clean:
	rm -rf *.tar.gz dist *.egg-info
	find . -name "*.pyc" -exec rm '{}' ';'
	find . -name "*.pyo" -exec rm '{}' ';'
	find . -name "*.pyd" -exec rm '{}' ';'
	find . -name "__pycache__" -exec rm -rf '{}' ';'
	rm -rf .pytest_cache
	rm -rf build
	rm -rf dist

compile: uv.lock
	@uv pip compile --group=docs --group=demo pyproject.toml -o requirements.txt

release:
	@uv build --sdist --wheel
	@twine upload dist/*
	git push origin master

docs:
	@echo "Generating docs..."
	@cd doc && rm -rf build && make html
	@open doc/build/html/index.html

.PHONY: docs release compile dist clean list
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | xargs
