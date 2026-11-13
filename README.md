# ISPmanager Monaco Editor

A Monaco-based editor for ISPmanager 6, with a shared note you can show when creating or editing a site. It works inside File Manager and uses the panel’s existing save actions and file permissions.

This is an independent plugin, not an official ISPmanager product.

## Features

- Syntax highlighting, language selection, search, and matching tags and brackets.
- Light/dark themes, font size, word wrap, minimap, and fullscreen mode.
- Save with Ctrl/Cmd+S; fullscreen also includes **Save** and **Save and close**.
- Switch between Monaco and the panel’s text editor.
- Server-wide editor defaults and an optional blue info or yellow warning note on site forms.

Project-wide PHP/Laravel autocomplete is not included yet.

## Compatibility

Tested by the user on **ISPmanager Lite 6.155.0 / Phoenix, Rocky Linux 8.10 x86_64**. Installation and update scenarios were also tested locally with Python 3.6.

Requires Linux, root access, `/usr/bin/python3` (3.6+), and the standard `/usr/local/mgr5` layout. Other ISPmanager 6 versions and editions still need testing; support for later major versions is not confirmed. The installer checks files and runtime requirements, not UI compatibility.

## Install or update

Download the `.pyz` installer and `.sha256` file from [v0.3.1 release](https://github.com/mchtylmz/ispmanager-monaco-editor-/releases/tag/v0.3.1), upload both to `/root`, and save any open edits. Then run on the server:

```sh
cd /root
sha256sum -c ismonaco-setup-0.3.1.sha256 && /usr/bin/python3 -I -B /root/ismonaco-setup-0.3.1.pyz
```

The same command handles a fresh install, updates a verified editor 0.2.5 installation while keeping its settings, or checks an already-current installation. Unknown or modified installations are rejected. New installs and updates ask for a panel restart; refresh the panel afterward.

Installer **0.3.1** bundles plugin **0.3.0** and editor **0.2.5**. No Node.js or internet connection is needed on the server. See the [installation guide](docs/TEK_DOSYA_KURULUM.md) for checks and recovery options.

## Settings

Open **Monaco settings** as root to set editor defaults and the site note’s text and style. The note appears on the site form’s main settings tab; leave it blank to hide it. These settings apply across the server.

## Security and data

File access and saving stay with ISPmanager’s existing form and permissions. The plugin adds no separate site-file API and does not change site files, databases, or panel core files during installation.

Only root can change global settings. Site notes are plain text and visible to users who open the form, so keep credentials out of them. File contents and session details are not placed in frame URLs. Real two-account isolation testing is still pending.

## Development

`frontend/` contains the editor UI, `integration/` the panel handlers and installer, and `tools/` and `tests/` the local development utilities.

```sh
npm ci
npm run build
npm run test:editor
```

Packaging and archive-based tests also need the original release ZIPs in `dist/`: plugin 0.3.0 for the standalone installer, and editor 0.2.5 for the plugin package. These are not included in the source checkout or the v0.3.1 release assets. Editing the frontend alone does not update the bundled installer.

More details: [architecture](docs/MIMARI.md) · [plugin scope](docs/PLUGIN_0_3_0.md).
