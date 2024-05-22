#!/bin/bash

# This script is used to transform default translation files folders (translationfiles/<lang>/*.(po|mo))
# to the locale folder (locale/<lang>/LC_MESSAGES/*.(po|mo))

cd ..

# Remove the locale/* if it exists to cleanup the old translations
if [ -d "locale" ]; then
  rm -rf locale/*
fi

# Create the locale folder if it doesn't exist
if [ ! -d "locale" ]; then
  mkdir locale
fi

# Loop through the translation folders and copy the files to the locale folder
# Skip the templates folder

for lang in translationfiles/*; do
  if [ -d "$lang" ]; then
	lang=$(basename $lang)
	if [ "$lang" != "templates" ]; then
	  if [ ! -d "locale/$lang/LC_MESSAGES" ]; then
		mkdir -p locale/$lang/LC_MESSAGES
	  fi
	  # Echo the language being copied
	  echo "Copying $lang locale"
	  cp translationfiles/$lang/*.po locale/$lang/LC_MESSAGES/
	  cp translationfiles/$lang/*.mo locale/$lang/LC_MESSAGES/
	fi
  fi
done
