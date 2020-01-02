ARCH ?= amd64
OS ?= $(shell uname -s | tr '[:upper:]' '[:lower:'])
CURL ?= curl --fail -sSL
XARGS ?= xargs -I {}

BIN_DIR ?= ${HOME}/bin
PATH := $(BIN_DIR):$(PATH)

FIND_EXCLUDES ?= -not \( -name .terraform -prune \)

VERSION ?= $$(grep -E '^current_version' .bumpversion.cfg | sed 's/^.*= //')

MAKEFLAGS += --no-print-directory
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.SUFFIXES:

.PHONY: %/lint %/format %/install

GITHUB_ACCESS_TOKEN ?= 4224d33b8569bec8473980bb1bdb982639426a92
# Macro to return the download url for a github release
# For latest release, use version=latest
# To pin a release, use version=tags/<tag>
# $(call parse_github_download_url,owner,repo,version,asset select query)
parse_github_download_url = $(CURL) https://api.github.com/repos/$(1)/$(2)/releases/$(3)?access_token=$(GITHUB_ACCESS_TOKEN) | jq --raw-output  '.assets[] | select($(4)) | .browser_download_url'

# Macro to download a github binary release
# $(call download_github_release,file,owner,repo,version,asset select query)
download_github_release = $(CURL) -o $(1) $(shell $(call parse_github_download_url,$(2),$(3),$(4),$(5)))

guard/env/%:
	@ _="$(or $($*),$(error Make/environment variable '$*' not present))"

guard/program/%:
	@ which $* > /dev/null || $(MAKE) $*/install

$(BIN_DIR):
	@ echo "[make]: Creating directory '$@'..."
	mkdir -p $@

install/gh-release/%: guard/env/FILENAME guard/env/OWNER guard/env/REPO guard/env/VERSION guard/env/QUERY
install/gh-release/%:
	@ echo "[$@]: Installing $*..."
	$(call download_github_release,$(FILENAME),$(OWNER),$(REPO),$(VERSION),$(QUERY))
	chmod +x $(FILENAME)
	$* --version
	@ echo "[$@]: Completed successfully!"

eclint/lint: | guard/program/eclint
	@ echo "[$@]: Linting all files with eclint..."
	eclint check
	@ echo "[$@]: All files PASSED lint test!"

python/lint: | guard/program/black
	@ echo "[$@]: Linting Python files..."
	black --check .
	@ echo "[$@]: Python files PASSED lint test!"

python/format: | guard/program/black
	@ echo "[$@]: Formatting Python files..."
	black .
	@ echo "[$@]: Successfully formatted Python files!"
