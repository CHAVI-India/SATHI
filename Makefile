# Translation management
# Usage: make messages LANG=bn

LANG ?= bn

# Only scan chaviprom, promapp,  patientapp, providerapp, and templates directories
IGNORE_DIRS = --ignore="docs/*" \
              --ignore="venv/*" \
              --ignore="node_modules/*" \
              --ignore="static/*" \
              --ignore="staticfiles/*" \
              --ignore="media/*" \
              --ignore="item_media/*" \
              --ignore="logs/*" \
              --ignore=".git/*" \
              --ignore=".github/*"

messages:
	cd /mnt/share/chavi-prom && django-admin makemessages -l $(LANG) $(IGNORE_DIRS)

compilemessages:
	cd /mnt/share/chavi-prom && django-admin compilemessages -l $(LANG)

.PHONY: messages compilemessages
