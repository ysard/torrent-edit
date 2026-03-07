#!/usr/bin/env python3
# A tool to edit BitTorrent metadata (private flag and trackers) of torrent files.
# Copyright (C) 2026  Ysard
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# Standard imports
from typing import Union
from pathlib import Path
import hashlib
import shutil
import argparse
import logging
import itertools as it

# Custom imports
from bcoding import bdecode, bencode


LOGGER = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Minimal logger configuration"""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def open_torrent(filepath: str) -> dict:
    """Load and deserialize a .torrent file

    :param filepath: Path to the torrent file.
    :return: The deserialized torrent metadata structure.
    """
    with open(filepath, "rb") as file:
        torrent_file = bdecode(file)

    raw_info_hash = bencode(torrent_file["info"])
    info_hash = hashlib.sha1(raw_info_hash).hexdigest()

    LOGGER.info("Process %s (hash: %s)", Path(filepath).name, info_hash)

    return torrent_file


def edit_torrent(
    torrent_file: dict,
    private: Union[bool, None] = False,
    new_trackers: Union[tuple, list] = (),
    old_trackers: Union[tuple, list, None] = (),
    replace: bool = False,
) -> Union[dict, None]:
    """Modify the privacy flag and tracker list of a torrent

    .. raises:: ValueError
        If the resulting torrent would contain no trackers.

    :param torrent_file: A deserialized torrent structure.
    :key private: Whether to set the torrent as private.
        Private torrents disable DHT, PEX and LSD in most BitTorrent clients.
        (default: False)
    :key new_trackers: List of new trackers to add or replace in the torrent metadata.
        (see :meth:`replace` keyword).
        If only new_trackers is passed, the trackers are added to the existing ones,
        except if replace keyword is True. In this case all the existing trackers
        will be replaced.
    :key old_trackers: List of old trackers to remove from the torrent metadata.
        If no tracker is found, the torrent will NOT be processed at all.
        This option takes precedence over :meth:`private`.
    :key replace: If True, the existing tracker list is replaced entirely with
        :meth:`new_trackers`.
    :return: The modified deserialized torrent metadata structure.
        Return None if the torrent is not modified.
    """
    torrent_list = (
        torrent_file["announce-list"]
        if "announce-list" in torrent_file
        else [torrent_file["announce"]]
    )
    LOGGER.debug("Existing trackers: %s", ", ".join(torrent_list))

    if old_trackers and not set(torrent_list) & set(old_trackers):
        LOGGER.debug("Trackers don't match: do not process this torrent!")
        return

    if private is not None:
        LOGGER.debug("Toggle private attribute: %s", private)
        torrent_file["info"]["private"] = int(private)

    if all(param is None for param in (new_trackers, old_trackers)):
        # Nothing to do about trackers
        return torrent_file

    # Set operation shenanigans
    if new_trackers:
        if not replace:
            # NOTE: can duplicate items, but keep the order
            torrent_list += new_trackers
        else:
            torrent_list = new_trackers

    if old_trackers:
        torrent_list = list(set(torrent_list) - set(old_trackers))

    if not torrent_list:
        raise ValueError("Tracker list would become empty.")

    torrent_file["announce"] = torrent_list[0]

    if len(torrent_list) > 1:
        torrent_file["announce-list"] = torrent_list
    elif "announce-list" in torrent_file:
        del torrent_file["announce-list"]

    LOGGER.debug("Updated trackers: %s", ", ".join(torrent_list))

    return torrent_file


def write_torrent(filepath: str, torrent_file: Union[dict, None]) -> None:
    """Write a modified torrent file to disk

    The original file is backed up before writing.

    :param filepath: Path to the torrent file.
    :param torrent_file: The modified deserialized torrent metadata structure,
        or None if the torrent should not be modified.
    """
    if not torrent_file:
        return

    data = bencode(torrent_file)

    # Make a backup
    shutil.copy2(filepath, str(filepath) + ".bak")

    with open(filepath, "wb") as file:
        file.write(data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Edit BitTorrent metadata (private flag and trackers)."
    )

    parser.add_argument(
        "torrents",
        help="Path to the .torrent file(s)",
        nargs="*",
    )

    privacy_group = parser.add_mutually_exclusive_group()
    privacy_group.add_argument(
        "--public",
        help="Remove the private flag",
        action="store_true",
    )
    privacy_group.add_argument(
        "--private",
        help="Set the torrent as private (disable DHT/PEX)",
        action="store_true",
    )

    parser.add_argument(
        "--add",
        nargs="+",
        metavar="URL",
        help="Add all trackers with the provided list",
    )

    parser.add_argument(
        "--remove",
        nargs="+",
        metavar="URL",
        help="Remove all trackers with the provided list. "
            "If no tracker is found, the file will be skipped, even if private is set.",
    )

    parser.add_argument(
        "--replace",
        nargs="+",
        metavar="URL",
        help="Replace all trackers with the provided list",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (debug logging)",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.verbose)

    new_trackers = args.add
    old_trackers = args.remove
    replace = args.replace is not None
    if args.private:
        private = True
    elif args.public:
        private = False
    else:
        # Do not touch this setting
        private = None

    if replace:
        # Validate new trackers with replace
        new_trackers = args.replace

    # Handle jokers & multiple files
    filepaths = it.chain(
        *(
            filepath.parent.glob(filepath.name)
            for filepath in map(Path, args.torrents)
        )
    )
    for filepath in filepaths:
        write_torrent(
            filepath,
            edit_torrent(
                open_torrent(filepath),
                private=private,
                new_trackers=new_trackers,
                old_trackers=old_trackers,
                replace=replace,
            ),
        )


if __name__ == "__main__":
    main()
