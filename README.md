[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ysard/torrent-edit)](https://github.com/ysard/torrent-edit/releases/latest/)
[![version on pypi](https://img.shields.io/pypi/v/torrent-edit.svg)](https://pypi.python.org/pypi/torrent-edit)
[![python versions on pypi](https://img.shields.io/pypi/pyversions/torrent-edit)](https://pypi.python.org/pypi/torrent-edit)
[![license](https://img.shields.io/pypi/l/torrent-edit.svg)](https://github.com/ysard/torrent-edit/blob/main/LICENSE)

A small command-line tool to modify BitTorrent `.torrent` files.

This tool is designed to perform simple metadata edits without recreating the torrent.
It supports Transmission & qBittorrent resume files.

---

## TL;DR: Migration from yggtorrent

Example for qBittorrent + Windows (adapt paths for Transmission or GNU/Linux, see further):

```bash
$ torrent-edit %LOCALAPPDATA%/qBittorrent/BT_backup/*.torrent \
    --remove http://connect.maxp2p.org:8080/<your_announce>/announce \
    --replace \
    https://tracker1/announce \
    https://tracker2/announce \
    --resume_path %LOCALAPPDATA%/qBittorrent/BT_backup/
```

`--remove` allows to filter the torrents, keeping only the ones that match the old tracker.
You can add it back to the list using `--replace` or `--add`.
The `--resume_path` option updates the `.fastresume` or `.resume` files
(these are the files that keep the list of trackers up to date or just statistics and download paths,
in qBittorrent or Transmission respectively).


## Features

- Toggle torrent **private/public** flag
- Add new trackers
- Remove existing trackers
- Replace the entire tracker list
- Automatic `.bak` backup before writing
- Synchronize `.resume` & `.fastresume` files for torrents already loaded in a client

## Installation

### From pypi

```bash
pip install torrent-edit
```

### From source

```bash
git clone https://github.com/yourname/torrent-edit.git
cd torrent-edit
pip install .
```

Editable install (recommended for development)
```bash
pip install -e .
```

## Usage

```
usage: torrent-edit [-h] [--public | --private] [--add URL [URL ...]] [--remove URL [URL ...]] [--replace URL [URL ...]] [-v] torrent

Edit BitTorrent metadata (private flag and trackers).

positional arguments:
  torrent               Path to the .torrent file(s)

options:
  -h, --help            show this help message and exit
  --public              Remove the private flag
  --private             Set the torrent as private (disable DHT/PEX)
  --inplace             Modify the torrent inplace even if the hash has changed instead of recreating it
                        (if the privacy flag has been toggled)(not recommended)
  --resume_path [RESUME_PATH]
                        Directory of the .resume or .fastresume file(s). Used for qBittorrent and Transmission.
  --add URL [URL ...]   Add all trackers with the provided list
  --remove URL [URL ...]
                        Remove all trackers with the provided list.
                        If no tracker is found, the file will be skipped, even if private is set.
  --replace URL [URL ...]
                        Replace all trackers with the provided list
  -v, --verbose         Enable verbose output (debug logging)
```

## Examples

You can specify multiple files:
```bash
$ torrent-edit *.torrent [...]
```

- Make a torrent private / public

```bash
$ torrent-edit "Mr.and.Mr.Macron's.holidays.financed.by.your.taxes.mkv.torrent" --private
```

This sets the private flag in the torrent metadata.
Most BitTorrent clients will disable DHT, PEX, and LSD when the torrent is private.

```bash
$ torrent-edit movie.torrent --public
```

Removes the private flag.

> ⚠️ **Notice:**
> By doing this, you are changing the torrent's hash. The file will therefore be different
> for the network, and your old peers will no longer be able to find you.
> However, you may have two torrents pointing to the same file, and the hash obtained is
> exactly the same as the hash that would have been obtained if the torrent had been
> generated from the start with this option.

> ⚠️ **Notice:**
> When doing this, you may need to update the path to the file in your application.
> This is because the torrent client treats it as a new pending download.
> To AVOID this, use the `--resume_path` parameter that points to the `.resume` or `.fastresume`
> files of Transmission or qBittorrent. The updates will be made automatically and visible
> once the client is restarted.

Use the `--inplace` parameter to force editing the torrent file in place (even if the hash is modified).
This can be useful if you are working with torrents that not already loaded in a BitTorrent client.

- Add a tracker

```bash
$ torrent-edit movie.torrent \
    --add https://tracker/announce
```

You can specify multiple trackers:

```bash
$ torrent-edit movie.torrent \
    --add \
    https://tracker1/announce \
    https://tracker2/announce
```

- Remove a tracker

```bash
$ torrent-edit movie.torrent \
    --remove http://oldtracker/announce
```

- Replace all trackers

```bash
$ torrent-edit movie.torrent \
    --replace \
    https://tracker1/announce \
    https://tracker2/announce
```

This removes all existing trackers and replaces them with the provided ones.

## How to use in real life (GNU/Linux)

- Stop the BitTorrent service or application (Transmission, qBittorrent, etc.)

- Find the directory with the torrents used by your application, and go into it.

    - For Transmission server: `/var/lib/transmission-daemon/info/torrents/` (torrents), `/var/lib/transmission-daemon/info/resume/` (resume files)
    - For Transmission client: `~/.config/transmission/torrents/` (torrents), `~/.config/transmission/resume/` (resume files)

    - For qBittorrent (Linux): `~/.local/share/qBittorrent/BT_backup/` (torrent & fastresume files)
    - For qBittorrent (Windows): `%LOCALAPPDATA%/qBittorrent/BT_backup` (torrent & fastresume files)

- Execute the script with your own arguments.

- If you are using a simple client, just restart it, it's done.

- If you are using Transmission server, you *may* have to restart the service and
reload the torrents with the remote administration tool.

```bash
sudo find . -iname "*.torrent" -exec transmission-remote 127.0.0.1:9091 -n transmission_login:transmission_pass -a {} \;
```

Done!

## Alternative

The tool `transmission-edit` allows you to update the tracker list, but will NOT
allow you to toggle the private flag.

Example:
    
```bash
cd /var/lib/transmission-daemon/info/torrents
sudo transmission-edit -r "old_url" "new_url" *.torrent
```

## Contributions

This project is open for any contribution! Any bug report can be posted by
opening an [issue](https://github.com/ysard/torrent-edit/issues).

## License

torrent-edit is released under the GNU General Public License v3 (GPLv3+).
