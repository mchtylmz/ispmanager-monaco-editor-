#!/bin/sh
exec /usr/bin/env -i \
  "AUTH_USER=${AUTH_USER-}" "AUTH_LEVEL=${AUTH_LEVEL-}" \
  "PARAM_lang=${PARAM_lang-}" "PARAM_func=${PARAM_func-}" "PARAM_sok=${PARAM_sok-}" \
  "PARAM_theme=${PARAM_theme-}" "PARAM_font_size=${PARAM_font_size-}" \
  "PARAM_fullscreen=${PARAM_fullscreen-}" "PARAM_wrap=${PARAM_wrap-}" "PARAM_minimap=${PARAM_minimap-}" "PARAM_height=${PARAM_height-}" \
  "PARAM_site_notice_style=${PARAM_site_notice_style-}" "PARAM_site_notice_text=${PARAM_site_notice_text-}" \
  /usr/bin/python3 -I -B /usr/local/mgr5/addon/ismonaco_site_notice_0_3_0.py
