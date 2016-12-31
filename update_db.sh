#!/bin/bash

python2 ${OPENSHIFT_REPO_DIR}battledecks.py 2>&1 | tee /tmp/update_db.log

cat /tmp/update_db.log | mail -r "Battle decks <no-reply@rhcloud.com>" -s "Battle decks update" "gui-gui@netcourrier.com"

echo "*** Sending mail summary ***"

