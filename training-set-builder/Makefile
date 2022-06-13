# CONFIG_PATH=./configmaps

default: run

run:
	python -m training_set_builder

# clean:
# 	find . -type f -name '*.pyc' -delete
# 	find . -type d -name '__pycache__' -delete

# configmaps:
# 	@sh -c "./scripts/external-db-config.sh $(CONFIG_PATH)"

# .NOTPARALLEL:

.PHONY: run clean
