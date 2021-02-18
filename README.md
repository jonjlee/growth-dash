# Growth Dashboard

# Prepare a Data File

Source data files are expected to be encrypted. A file can be encrypted by using the growth-dash script:

  poetry run growth-dash -e data.txt

The generates `data.txt.enc` which should be made available at a public URL for growth-dash to fetch on startup.
  
The growth-dash script is in src/growth_dash/console.py and configured as a binary in the tool.poetry.scripts section of pyproject.toml.

