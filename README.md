# SlowCopy

Copy directories to a fixed destination and build md5 hashes. Some criterias are checked while selecting the source directory. Some subdirectories with to many files will be zipped.

The GUI is close to a well known copy tool so the old dogs don´t need to learn new tricks.

RoboCopy is used so this is for Windows.

There is a check for updates on startup.

The tool can be also be run on PowerShel/CMD. Try

`slowcopy-v*.exe -h`

to learn usage.

JSON files are used to store configuration (not touched by application) and user settings that ere rewritten every run:

- `config.json`: admin given parameters as domain, paths etc.
- `gui.json`: basic parameters for the GUI
- `labels.json`: text shown in the GUI
- `settings.json`: parameters (e.g. user name) that are set by the GUI or CMD arguments

Nuitka is needed to bild Windows executable. The make-script can be used.

Still testing. The author is not responsible for any malfunction and/or lost data.

MIT License
