
A small command-line tool to modify BitTorrent `.torrent` files.

This tool is designed to perform simple metadata edits without recreating the torrent.

---

## Features

- Toggle torrent **private/public** flag
- Add new trackers
- Remove existing trackers
- Replace the entire tracker list
- Automatic `.bak` backup before writing

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
  --add URL [URL ...]   Add all trackers with the provided list
  --remove URL [URL ...]
                        Remove all trackers with the provided list
  --replace URL [URL ...]
                        Replace all trackers with the provided list
  -v, --verbose         Enable verbose output (debug logging)
```

## Examples

You can specify multiple files:
```bash
$ torrent-edit *.torrent [...]
```

- Make a torrent private

```bash
$ torrent-edit "Mr.and.Mr.Macron's.holidays.financed.by.your.taxes.mkv.torrent" --private
```

This sets the private flag in the torrent metadata.
Most BitTorrent clients will disable DHT, PEX, and LSD when the torrent is private.

- Make a torrent public

```bash
$ torrent-edit movie.torrent --public
```

Removes the private flag.

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

- Stop the client service (Transmission, qBittorrent, etc.)

- Find the directory of the torrents used by the client, and go into it.

For Transmission: `/var/lib/transmission-daemon/info/torrents`

- Execute the script with your own arguments.

- Restart the service

- Reload the torrents with the remote administration tool.

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
