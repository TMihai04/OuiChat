# Attachment constants

from pathlib import Path

# TODO: When creating installer for the backend, use systemd to run the backend as service. Uncomment these then and add an env var
# ATTACHMENTS_DIR = Path("/var/lib/ouichat/attachments")
# ICONS_DIR = Path("/var/lib/ouichat/icons")

# As absolute paths
ATTACHMENTS_DIR = Path("./ignore/attachments").resolve()
ICONS_DIR = Path("./ignore/icons").resolve()