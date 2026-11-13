#!/bin/sh
exec /usr/bin/env -i \
  "AUTH_USER=${AUTH_USER-}" \
  "AUTH_LEVEL=${AUTH_LEVEL-}" \
  "PARAM_func=${PARAM_func-}" \
  /usr/bin/python3 -I -B /usr/local/mgr5/addon/ismonaco_preview.py
