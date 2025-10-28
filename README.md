# Cirdan

## Copy to Import/Remote Directory for Data Across Network

Copy directories to a fixed destination and build md5 hashes. Some criterias are checked while selecting the source directory.

The GUI is close to a well known copy tool so the old dogs don´t need to learn new tricks.

RoboCopy is used so this is for Windows.

There is a check for updates on startup. The tool `download_app.py` / `download_app` is used to download new version and replace the outdated.

The application can be also be run on PowerShel/CMD. Try

`cirdan.exe -h`

to learn usage.

JSON files are used to store configuration (not touched by application):

- `config.json`: admin given parameters as domain, paths etc.
- `gui.json`: basic parameters for the GUI
- `labels.json`: text shown in the GUI

By default user settings are stored in `%AppData%\Local\Cirdan\settings.json`.

Nuitka is needed to bild Windows executables. The Batch-Script `make-dist-bat` can be used. Check if paths need to be adapted.

Still testing. The author is not responsible for any malfunction and/or lost data.

MIT License



