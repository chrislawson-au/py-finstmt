#!/bin/bash

# Note: Must be run through direnv source

if ! has asdf; then
  echo "asdf not found. Please install asdf first: https://asdf-vm.com/guide/getting-started.html"
  exit 1
fi

# Install asdf plugins
# `asdf plugin list` / `asdf plugin add` work on every asdf version; the
# hyphenated plugin-list/plugin-add forms were removed in asdf 0.16.
if ! asdf plugin list | grep -q "pnpm"; then
  asdf plugin add pnpm https://github.com/jonathanmorley/asdf-pnpm
  echo "Added pnpm asdf plugin"
fi

if ! asdf plugin list | grep -q "pipx"; then
  asdf plugin add pipx https://github.com/amrox/asdf-pyapp
  echo "Added pipx asdf plugin"
fi

# Install necessary versions
asdf install