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
from binascii import unhexlify

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


def get_torrent_hash(torrent_file: dict) -> str:
    """Get the unique hash info field of the given torrent

    :param torrent_file: A deserialized torrent structure.
    """
    raw_info_hash = bencode(torrent_file["info"])
    return hashlib.sha1(raw_info_hash).hexdigest()


def open_torrent(filepath: Path) -> tuple[dict, str]:
    """Load and deserialize a .torrent file

    :param filepath: Path to the torrent file.
    :return: The deserialized torrent metadata structure and its hash.
    """
    torrent_file = bdecode(filepath.read_bytes())

    info_hash = get_torrent_hash(torrent_file)
    LOGGER.info("Process %s (hash: %s)", Path(filepath).name, info_hash)

    return torrent_file, info_hash


def edit_torrent(
    torrent_file: dict,
    resume_file: Union[dict, None],
    private: Union[bool, None] = False,
    new_trackers: Union[tuple, list] = (),
    old_trackers: Union[tuple, list, None] = (),
    replace: bool = False,
) -> Union[dict, None]:
    """Modify the privacy flag and tracker list of a torrent

    .. raises:: ValueError
        If the resulting torrent would contain no trackers.

    :param torrent_file: A deserialized torrent structure.
    :param resume_file: The deserialized .resume or .fastresume structure.
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
    try:
        # Flatten the list of lists
        torrent_list = (
            list(it.chain(*torrent_file["announce-list"]))
            if "announce-list" in torrent_file
            else [torrent_file["announce"]]
        )
    except KeyError:
        torrent_list = []
        LOGGER.debug("Announce not found.")

        if not resume_file:
            LOGGER.debug(
                "Announce not found. Are you trying to edit qBittorrent files ? "
                "Please provide the path to the fastresume files with --resume_path."
            )

    if resume_file:
        # Merge torrent_list with trackers in the resume file (qBittorrent)
        # Yeah it's a list of list...
        torrent_list += list(it.chain(*resume_file.get("trackers", [[]])))

    torrent_list = set(torrent_list)
    old_trackers = set(old_trackers) if old_trackers else set()
    new_trackers = set(new_trackers) if new_trackers else set()

    LOGGER.debug("Existing trackers: %s", ", ".join(torrent_list))

    if old_trackers and not torrent_list & old_trackers:
        LOGGER.debug("Trackers don't match: do not process this torrent!")
        return None

    private_flag = torrent_file["info"].get("private", 0)
    hash_modified = False
    if private is not None and private_flag != private:
        # WARNING: Here even we set the private flag to 0 if the torrent is public.
        # The private flag is optional. Its explicit presence, enabled/disabled
        # WILL modify the hash of the torrent.
        LOGGER.debug("Toggle private attribute: %s->%s", private_flag, int(private))
        torrent_file["info"]["private"] = int(private)
        hash_modified = True

    if not new_trackers and not old_trackers:
        # Nothing to do about trackers
        if hash_modified:
            return torrent_file
        return None

    # Set operation shenanigans
    if new_trackers:
        if not replace:
            torrent_list |= new_trackers
        else:
            torrent_list = new_trackers

    torrent_list -= old_trackers

    LOGGER.debug("Updated trackers: %s", ", ".join(torrent_list))

    # Reconstruct the final list of lists
    torrent_list = [[tracker] for tracker in torrent_list]

    if not torrent_list:
        if "announce" in torrent_file:
            del torrent_file["announce"]
        # raise ValueError("Tracker list would become empty.")
    else:
        torrent_file["announce"] = torrent_list[0][0]

    if len(torrent_list) > 1:
        torrent_file["announce-list"] = torrent_list
    elif "announce-list" in torrent_file:
        del torrent_file["announce-list"]

    return torrent_file


def copy_qb_fastresume(
    fastresume_filepath: Path, torrent_file: dict, current_hash: str
):
    """Update hash of qBittorrent's .fastresume file if required, update tracker list

    :param fastresume_filepath: Path of a .fastresume file.
    :param torrent_file: The modified deserialized torrent metadata structure;
    :param current_hash: Hash of the torrent after the modifications.
    """
    resume_file = bdecode(fastresume_filepath.read_bytes())

    # original_hash = hexlify(resume_file["info-hash"]).decode()

    # Inject the new hash (cast to bytes)
    raw_hash = unhexlify(current_hash.encode())
    resume_file["info-hash"] = raw_hash

    # Inject the trackers
    LOGGER.debug("Fastresume old trackers: %s", resume_file["trackers"])

    try:
        pending_trackers = torrent_file.get("announce-list", [[torrent_file["announce"]]])
    except KeyError:
        # No multiple trackers nor announce
        # When the list of list is empty (no trackers) it's a simple empty list (but should work anyway)
        pending_trackers = []

    LOGGER.debug("Fastresume pending trackers: %s", pending_trackers)
    resume_file["trackers"] = pending_trackers

    # Save
    Path(fastresume_filepath.with_stem(current_hash)).write_bytes(bencode(resume_file))


def open_resume_file(
    original_hash: str, resume_path: Union[Path, None]
) -> Union[tuple[None, None], tuple[dict, Path]]:
    """Try to find & open the corresponding .resume or .fastresume file given the torrent's hash

    :param original_hash: Hash of the torrent before any modification.
    :param resume_path: Path for the .resume or .fastresume files (can be None).
    :return: The deserialized .resume or .fastresume structure and its file path.
        Return a `(None, None)` structure if the file was not found.
    """
    if not resume_path:
        return None, None

    resume_filepath = find_resume_file(original_hash, resume_path)
    if not resume_filepath:
        return None, None
    return bdecode(resume_filepath.read_bytes()), resume_filepath


def find_resume_file(original_hash: str, resume_path: Union[Path, None]) -> None:
    """Try to get the corresponding .resume or .fastresume file given the torrent's hash

    :param original_hash: Hash of the torrent before any modification.
    :param resume_path: Path for the .resume or .fastresume files (can be None).
    :return: The file path of the .resume or .fastresume file.
    """
    if not resume_path:
        return None

    files = list(resume_path.glob(original_hash + ".*resume"))
    if not files:
        LOGGER.warning("Resume file not found!")
        return None
    if len(files) > 1:
        LOGGER.error("More than 1 resume file?")
        return None

    return files[0]


def sync_resume_file(
    resume_filepath: Union[Path, None],
    torrent_file: dict,
    original_hash: str,
    current_hash: str,
):
    """Sync torrent stats when the hash has changed or also sync trackers for qBittorrent

    .. note::
        - qBittorrent stores the trackers in use in the .fastresume file.
        - Transmission stores the trackers in use in the .torrent file itself;
        thus it is not handled here. The .resume file is just copied and renamed
        in order to sync stats.

    :param resume_filepath: Path of a .resume or .fastresume file (can be None).
    :param torrent_file: The modified deserialized torrent metadata structure;
    :param original_hash: Hash of the torrent before any modification.
    :param current_hash: Hash of the torrent after the modifications.
    """
    if not resume_filepath:
        LOGGER.warning("Resume file not provided")
        return

    match resume_filepath.suffix:
        case ".resume":
            LOGGER.debug("Sync resume: Transmission format")
            if original_hash != current_hash:
                shutil.copy2(resume_filepath, resume_filepath.with_stem(current_hash))
        case ".fastresume":
            LOGGER.debug("Sync resume: qBittorrent format")
            copy_qb_fastresume(resume_filepath, torrent_file, current_hash)
        case _:
            LOGGER.error("Sync resume: Unknown format (%s)", resume_filepath.suffix)
            return

    LOGGER.debug("Resume file has been synced / renamed (new hash: %s)", current_hash)


def write_torrent(
    filepath: Path,
    resume_filepath: Union[Path, None],
    torrent_file: Union[dict, None],
    original_hash: str,
    inplace: bool = False,
) -> None:
    """Write a modified torrent file to disk

    The original file is backed up before writing.

    :param filepath: Path to the torrent file.
    :param resume_filepath: Path for the .resume or .fastresume files (can be None).
    :param torrent_file: The modified deserialized torrent metadata structure,
        or None if the torrent should not be modified.
    :param original_hash: Hash of the torrent before any modification.
    :key inplace: If True modify the torrent inplace even if the hash has changed
        (privacy flag toggled). Otherwise, a new torrent is created next to the old one,
        as is the .resume or .fastresume file if it is found in :meth:`resume_filepath`.
    """
    if not torrent_file:
        LOGGER.debug("Nothing has changed: do not process this torrent!")
        return

    current_hash = get_torrent_hash(torrent_file)

    if not inplace and current_hash != original_hash:
        filepath = filepath.parent / (current_hash + filepath.suffix)
        LOGGER.debug("Torrent file has been renamed (new hash: %s)", current_hash)
    else:
        # Make a backup
        shutil.copy2(filepath, str(filepath) + ".bak")
        LOGGER.debug("Torrent is modified in place!")

    if not inplace or current_hash == original_hash:
        # Always sync resume for qBittorrent, if inplace is False otherwise.
        sync_resume_file(resume_filepath, torrent_file, original_hash, current_hash)

    filepath.write_bytes(bencode(torrent_file))


def dir_path(path: str) -> Path:
    """Test existence of the given directory"""
    path = Path(path)
    if path.is_dir():
        return path
    raise argparse.ArgumentTypeError(f"{path} is not a valid directory")


def build_parser() -> argparse.ArgumentParser:
    """Command line interface parser"""
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
        "--inplace",
        action="store_true",
        help="Modify the torrent inplace even if the hash has changed "
        "instead of recreating it (if the privacy flag has been toggled)(not recommended)",
    )

    parser.add_argument(
        "--resume_path",
        nargs="?",
        type=dir_path,
        help="Directory of the .resume or .fastresume file(s). "
        "Used for qBittorrent and Transmission.",
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
        *(filepath.parent.glob(filepath.name) for filepath in map(Path, args.torrents))
    )
    for filepath in filepaths:
        torrent_file, original_hash = open_torrent(filepath)
        resume_file, resume_filepath = open_resume_file(original_hash, args.resume_path)

        write_torrent(
            filepath,
            resume_filepath,
            edit_torrent(
                torrent_file,
                resume_file,
                private=private,
                new_trackers=new_trackers,
                old_trackers=old_trackers,
                replace=replace,
            ),
            original_hash,
            inplace=args.inplace,
        )


if __name__ == "__main__":
    main()
