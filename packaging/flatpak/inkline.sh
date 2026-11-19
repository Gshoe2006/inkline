#!/bin/sh
# Inkline's launcher inside the Flatpak: the app lives in /app/lib/inkline.
exec python3 /app/lib/inkline/inkline.py "$@"
