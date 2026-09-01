# Cirdan
## Copy to Import/Remote Directory Across Network
<img alt="screenshot Cirdan GUI" src="screenshot.png" />

Copy directories to a fixed destination and build md5 hashes. Some criteria are checked while selecting the source directory.

The GUI is close to a well known copy tool so the old dogs don´t need to learn new tricks.

RoboCopy is used so this is for Windows.
## Requirements
Python 3.13 works fine. Newer versions should be no problem.

In addition to the standard libraries `PyInstaller` is required in case you want to build executables:

```
python -m pip install pyinstaller
```
In case your machine is offline, download the libraries on an online system:

```
python -m pip download pyinstaller
```
Transport the .whl files to the offline machine and execute:
```
python -m pip install --no-index --find-links .\ pyinstaller
```
## Installation
You might use git:
```
git clone https://codeberg.org/markusthilo/Cirdan.git
```
If you want to generate executables to copy and run the tool in an environment without Python, change into the Cirdan directory and use the make script:
```
cd Cirdan
python make.py
```
To copy the Cirdan directory it is possible to use the downloader script that is primarily intended to update an installed version:
```
python downloader.py .\ destination-dir\
```
or
```
downloader.exe .\ destination-dir\
```
if you have built executables.
## Configuration
The configuration files are in JSON file format:
- `config.json`: admin given parameters as domain, paths etc.
- `gui.json`: basic parameters for the GUI
By default there are language packs for English (`labels_en.json`) and German (`labels_de.json`).
### Example `config.json`
```
{
    "labels_path": "$APP/labels_de.json",
    "local_path": "$HOME/AppData/Local/Cirdan/",
    "target_path": "//192.168.128.150/UrkSp/Import/",
    "log_path": "//192.168.128.150/UrkSp/Import/_logs/",
    "update_path": "//192.168.128.150/UrkSp/Import/_dist/Cirdan/",
    "domain": "polizei.berlin.de",
    "destinations": {
        "Importverzeichnis LKA 711": {"sub_path": "LKA 711", "triggers": "static"},
        "Importverzeichnis LKA 712": {"sub_path": "LKA 712", "triggers": "static"},
        "Importverzeichnis LKA 713": {"sub_path": "LKA 713", "triggers": "static"},
        "Importverzeichnis LKA 714": {"sub_path": "LKA 714", "triggers": "selection"},
        "Importverzeichnis LKA 724": {"sub_path": "LKA 724", "triggers": "static"},
        "Importverzeichnis Dir 1 IuK": {"sub_path": "Dir 1", "triggers": "static"},
        "Importverzeichnis Dir 2 IuK": {"sub_path": "Dir 2", "triggers": "static"},
        "Importverzeichnis Dir 3 IuK": {"sub_path": "Dir 3", "triggers": "static"},
        "Importverzeichnis Dir 4 IuK": {"sub_path": "Dir 4", "triggers": "static"},
        "Importverzeichnis Dir 5 IuK": {"sub_path": "Dir 5", "triggers": "static"},
        "Importverzeichnis LKA 1 IuK": {"sub_path": "LKA 1", "triggers": "static"},
        "Importverzeichnis LKA 2 IuK": {"sub_path": "LKA 2", "triggers": "static"},
        "Importverzeichnis LKA 3 IuK": {"sub_path": "LKA 3", "triggers": "static"},
        "Importverzeichnis LKA 4 IuK": {"sub_path": "LKA 4", "triggers": "static"},
        "Importverzeichnis LKA 5 IuK": {"sub_path": "LKA 5", "triggers": "static"},
        "Importverzeichnis LKA 6 IuK": {"sub_path": "LKA 6", "triggers": "static"},
        "Importverzeichnis LKA 62 OT 3 IuK": {"sub_path": "LKA 62 OT 3", "triggers": "static"},
        "Importverzeichnis LKA 645 IuK": {"sub_path": "LKA 645", "triggers": "static"},
        "Importverzeichnis LKA 8 IuK": {"sub_path": "LKA 8", "triggers": "static"},
        "Importverzeichnis LKA KoSt ST 2": {"sub_path": "LKA KoSt ST 2", "triggers": "static"},
        "Testverzeichnis markus.thilo": {"sub_path": "Transfer_THI", "triggers": "selection"}
    },
	"app_name": "Cirdan",
    "triggers": {
        "static": ["AW für Ermittler"],
        "selection": [
            "AW für Ermittler",
            "BU für Dir 1 IuK",
            "BU für Dir 2 IuK",
            "BU für Dir 3 IuK",
            "BU für Dir 4 IuK",
            "BU für Dir 5 IuK",
            "BU für LKA 814"
        ]
    },
    "settings_name": "settings.json",
    "log_name": "log.txt",
    "lastlog_name": "lastlog.txt",
    "crashlog_name": "crashlog.txt",
    "tsv_name": "md5.txt",
    "trigger_name": "fertig.txt",
    "qualicheck_name": "qualicheck.txt",
    "source_whitelist": [
        "^[0-9]{6}-([0-9]{4}|[0-9]{6})-(([iZ0-9][0-9]{5})|(StA[0-9]{3}))/(EAV|MSD)[0-9]{2}[A-Z]{3}[0-9A-Z]{4}.*"
    ],
    "max_path_length": 230,
	"max_hash_size": 1073741824,
    "source_blacklist": [
        "^[^/]+/(?!((EAV|MSD)[0-9]{2}[A-Z]{3}[0-9A-Z]{4})|(.*\\.(txt|pdf)$))",
        ".*/Help/HTML5/.*",
        ".*/Help/LicenseUpgrade/.*"
    ],
    "destination_blacklist": [
        "^[^/]*/fertig.txt",
        "^[^/]*/fehler.txt",
        "^[^/]*/start.txt",
        "^[^/]*/zu_loeschen.txt"
    ],
	"mail": {
        "smtp_host": "smtpt.msd.polizei.berlin.de",
        "smtp_port": 25,
        "smtp_timeout": 30,
        "From": "MSD-Netz-Support <MSD-Netz-Support@polizei.berlin.de>",
        "Reply-To": "MSD-Netz-Support@polizei.berlin.de",
        "Default-Subject": "Cirdan: Import wurde durchgeführt",
        "body": "Hallo Nutzer,\n\ndies ist eine vom Upload-Tool Cirdan automatisch generierte Benachrichtigung.\n\nDer Upload wurde durchgeführt.\n\nVerzeichnis: %\nGesamtgröße: %\nAnzahl der Dateien: %\nDavon nicht kopiert: %\nDavon fehlerhaft: %\n\nBeste Grüße\n\nMSD-Netz-Support-Team\n"
    }
}

```
## Usage
- Launch the GUI:
```
python cirdan.py
```
- Launch with a preselected directory:
```
python cirdan.py -g directory-to-upload\
```
- Learn command line usage:
```
python cirdan.py -h
```
Having executables, double clicking `cirdan.exe` should work.
## Legal Notice
### License
MIT License

Copyright (c) 2025 Markus Thilo

https://opensource.org/license/MIT

### Disclaimer
This is not a commercial product with an army of developers and a department for quality control behind it. The author is not responsible for any malfunction and/or lost data. Use the software at your own risk.
