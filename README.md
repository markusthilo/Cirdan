# Cirdan
## Copy to Import/Remote Directory Across Network
<img alt="screenshot Cirdan GUI" src="screenshot.png" />

Copy source directories into a configured import directory and record an MD5 for every copied file. While a source is selected, Cirdan can check a whitelist, a blacklist, and the path length. After a successful copy it can drop a trigger file and a metadata file so a later process knows the upload is ready.

The GUI stays close to a familiar copy tool. The same job can be started from the command line. Windows and Linux are supported. The copy itself is done by the bundled `copymd5` binary (`copymd5.exe` on Windows, `copymd5` on Linux), which must sit next to the application.

## Requirements
Python 3.14 or newer.

`PyInstaller` is required only when you build the Windows executables:

```
python -m pip install pyinstaller
```

On an offline machine, download the wheels elsewhere and install them from that directory:

```
python -m pip download pyinstaller
python -m pip install --no-index --find-links .\ pyinstaller
```

## Installation
Clone the repository:

```
git clone https://codeberg.org/markusthilo/Cirdan.git
```

Build the Windows executables from the Cirdan directory. This writes `cirdan.exe`, `installer-win.exe`, and `version.txt`:

```
cd Cirdan
python make_cirdan.py
```

Install from the directory named by `update_path` in `config.json`. One optional argument is the install directory. If it is omitted, the installer asks.

Windows (default `C:/Programm Files/Cirdan`):

```
python installer-win.py
python installer-win.py "C:/Program Files/Cirdan"
```

The Windows installer mirrors with `robocopy /mir`. Names that start with a dot (`.git`, `.gitignore`, …) and `__pycache__` are left out. If `Cirdan.lnk` is missing, or if it does not point at `cirdan.exe` in this install directory, the installer asks whether to create the desktop shortcut. Enter accepts Yes.

Linux (default `/opt/Cirdan`):

```
python installer-lin.py
python installer-lin.py /opt/Cirdan
```

The Linux installer copies with `rsync -a` and the same exclusions. It uses `sudo` only when the destination directory is not writable by the current user. A menu entry at `/usr/share/applications/cirdan.desktop` is offered only when that install used `sudo`. Enter accepts Yes.

On Windows, a running `cirdan.exe` compares `version.txt` in `update_path` with its own version. When a newer build is available and `installer-win.exe` is next to that `version.txt`, the GUI can start the installer. The install path must not be a UNC path.

## Configuration
`config.json` in the application directory is the admin configuration. `-c` / `--config` selects another file. Labels come from the JSON file named by `labels_path`. English and German packs are `labels_en.json` and `labels_de.json`.

Paths are chosen by operating system. A value that starts with `$HOME/` is under the user home directory. A value that starts with `$APP/` is under the application directory. Other values are used as given.

`destinations` lists the import directories shown in the GUI. Only a directory that exists and can be listed is offered. Each entry has:

- `path`: the name of a path from the `paths` section, such as `import1_path`
- `todo`: the name of a set in the `todo` section, such as `selection` or `static`

A todo entry describes what is written into the uploaded directory:

- `trigger_name`: file written when the task is applied. Its content is the hostname and username as JSON.
- `meta_name`: metadata filename. `strftime` codes are expanded, so `%y%m%d_%H%M%S_metadata.txt` becomes a timestamped name.
- `meta_content`: text of that file. `%p` is replaced by a JSON list of `{pattern, matches}` counts from `count_paths`.
- `delete_name`: file removed before the new trigger is written.
- `do_something`: `false` marks the “do nothing” task. That task is also what the ↔ checkbox in the GUI selects.

`halted_name` is the trigger file of a held upload. “Trigger further processing” lists subdirectories of the selected destination that contain this file and whose stored username is the current user.

`count_paths` is a list of regular expressions. Matches are counted while the source is scanned, and again when further processing is triggered for a directory that uses `%p`.

`tsv_name` is the MD5 table written next to the copied files. `strftime` codes are expanded.

`source_whitelist` must match the source tree, or the source is rejected. `source_blacklist` and `max_path_length` are checked unless `-n` / `--nocheck` is set. In the GUI a too-long path or a blacklisted path can be ignored for the rest of that check. `destination_blacklist` rejects an existing destination subdirectory that already contains a matching file, such as `ready.txt`.

Mail is sent only when the SMTP server accepts a connection. The address field is the local part; `@domain` is appended. Each `%` in `mail.body` is replaced, in order, with: directory name, size, file count, read errors, write errors, size mismatches.

The last destination, username, mail address, subject, and the send-mail choice are stored in `local_path` / `settings_name`.

`gui` sets padding (`pad_factor`), the window size factors, and the green and red status colours.

### Example `config.json`
```
{
    "paths": {
        "Windows": {
            "labels_path": "$APP/labels_de.json",
            "icon_path": "$APP/icons/cirdan.png",
            "local_path": "$HOME/AppData/Local/Cirdan/",
            "log_path": "P:/Cirdan/test/target/_logs/",
            "update_path": "P:/Cirdan/",
            "import1_path": "P:/Cirdan//test/target/import1/",
            "import2_path": "P:/Cirdan//test/target/import2/",
            "import3_path": "P:/Cirdan//test/target/import3/"
        },
        "Linux": {
            "labels_path": "$APP/labels_de.json",
            "icon_path": "$APP/icons/cirdan.png",
            "local_path": "$HOME/.local/share/Cirdan/",
            "log_path": "$APP/test/target/_logs/",
            "update_path": "$APP/",
            "import1_path": "$APP/test/target/import1/",
            "import2_path": "$APP/test/target/import2/",
            "import3_path": "$APP/test/target/import3/"
        }
    },
    "destinations": {
        "Import 1": {"path": "import1_path", "todo": "selection"},
        "Import 2": {"path": "import2_path", "todo": "static"},
        "Import 3": {"path": "import3_path", "todo": "static"}
    },
    "todo": {
        "static": {
            "Only task": {
                "trigger_name": "ready.txt",
                "meta_name": "%y%m%d_%H%M%S_metadata.txt",
                "meta_content": "{\n    \"task\": 0\n    \"paths_count\": %p\n}",
                "delete_name": "not_ready.txt",
                "do_something": true
            },
            "Do nothing": {
                "trigger_name": "not_ready.txt",
                "meta_name": null,
                "meta_content": null,
                "delete_name": null,
                "do_something": false
            }
        },
        "selection": {
            "Task 1": {
                "trigger_name": "ready.txt",
                "meta_name": "%y%m%d_%H%M%S_metadata.txt",
                "meta_content": "{\n    \"task\": 1,\n    \"paths_count\": %p\n}",
                "delete_name": "not_ready.txt",
                "do_something": true
            },
            "Task 2": {
                "trigger_name": "ready.txt",
                "meta_name": "%y%m%d_%H%M%S_metadata.txt",
                "meta_content": "{\n    \"task\": 2\n}",
                "delete_name": "not_ready.txt",
                "do_something": true
            },
            "Task 3": {
                "trigger_name": "ready.txt",
                "meta_name": "%y%m%d_%H%M%S_metadata.txt",
                "meta_content": "{\n    \"task\": 3\n}",
                "delete_name": "not_ready.txt",
                "do_something": true
            },
            "Do nothing": {
                "trigger_name": "not_ready.txt",
                "meta_name": null,
                "meta_content": null,
                "delete_name": null,
                "do_something": false
            }
        }
    },
    "domain": "example.net",
    "settings_name": "settings.json",
    "halted_name": "not_ready.txt",
    "log_name": "log.txt",
    "lastlog_name": "lastlog.txt",
    "crashlog_name": "crashlog.txt",
    "tsv_name": "%y%m%d_%H%M%S_md5.txt",
    "source_whitelist": [
        "^[0-9]{6}-([0-9]{4}|[0-9]{6})-(([iZ0-9][0-9]{5})|(StA[0-9]{3}))/(EAV|MSD)[0-9]{2}[A-Z]{3}[0-9A-Z]{4}.*"
    ],
    "max_path_length": 230,
    "source_blacklist": [
        "^[^/]+/(?!((EAV|MSD)[0-9]{2}[A-Z]{3}[0-9A-Z]{4})|(.*\\.(txt|pdf)$))",
        ".*/Help/HTML5/.*",
        ".*/Help/LicenseUpgrade/.*"
    ],
    "destination_blacklist": [
        "^[^/]*/ready.txt$",
        "^[^/]*/error.txt$",
        "^[^/]*/start.txt$",
        "^[^/]*/delete.txt$"
    ],
    "count_paths": [
        ".*/aw_iped$",
        ".*\\.[eE]01$",
        ".*/python.*"
    ],
    "mail": {
        "smtp_host": "smtpt.example.net",
        "smtp_port": 25,
        "smtp_timeout": 30,
        "From": "From <from@example.net>",
        "Reply-To": "reply-to@example.net",
        "default-subject": "Cirdan: upload has finished",
        "body": "Dear user,\n\nthis is message generated by Cirdan, the upload tool for geeks.\n\nThe upload is complete.\n\nDirectory: %\nSize: %\nFiles: %\nRead errors: %\nWrite errors: %\nSize mismatches: %\n\nRegards,\n\nSupport-Team\n"
    },
    "gui": {
        "pad_factor": 1,
        "x_factor": 64,
        "y_factor": 48,
        "green_fg": "black",
        "green_bg": "pale green",
        "red_fg": "black",
        "red_bg": "coral"
    }
}
```

## Usage
Launch the GUI. With no source directory this is the default:

```
python cirdan.py
```

Open the GUI with one directory already selected:

```
python cirdan.py -g directory-to-upload
```

Copy one directory from the console. `-d` names a destination from `config.json`. `-t` names a task from that destination’s todo set. `-p` replaces the configured directory for that destination and requires `-d`.

```
python cirdan.py -d "Import 1" -t "Task 1" directory-to-upload
```

Send a status mail and skip the source checks:

```
python cirdan.py -d "Import 1" -t "Task 1" -m john.doe -n directory-to-upload
```

`-m` is the mailbox name without the domain (`john.doe` becomes `john.doe@example.net` when `domain` is `example.net`).

Show every option, or print the version:

```
python cirdan.py -h
python cirdan.py -v
```

| Option | Meaning |
| --- | --- |
| `-c`, `--config FILE` | Configuration file instead of `config.json` |
| `-d`, `--destination STRING` | Destination name from `config.json` |
| `-g`, `--gui` | Force the GUI |
| `-l`, `--log FILE` | Also write this log file |
| `-m`, `--mail STRING` | Mail the local part of this address when the copy finishes |
| `-n`, `--nocheck` | Skip blacklist and path-length checks |
| `-p`, `--path DIRECTORY` | Destination directory, overriding the configured path (needs `-d`) |
| `-s`, `--subject STRING` | Subject of the status mail |
| `-t`, `--todo STRING` | Task to apply after the copy (needs `-d`) |
| `-u`, `--username STRING` | Username written into the trigger file |
| `-v`, `--version` | Print the version and exit |
| `DIRECTORY` | Source directory. Without it, the GUI opens |

In the GUI, add one or more source directories. Each source is copied to `<destination>/<source name>/`. A successful copy writes the MD5 table, removes `delete_name` when the selected task has one, then writes the metadata file and the trigger file. Read errors, write errors, and size mismatches are reported and suppress the trigger.

“Trigger further processing” does the same write step for a directory that was uploaded earlier and is still held by `halted_name`.

With the Windows executables, double-click `cirdan.exe`.

## Legal Notice
### License
MIT License

Copyright (c) 2026 Markus Thilo

https://opensource.org/license/MIT

### Disclaimer
This is not a commercial product with an army of developers and a department for quality control behind it. The author is not responsible for any malfunction and/or lost data. Use the software at your own risk.
