# Copyright (C) 2017-2024 Arne Bachmann. All rights reserved


def help_output() -> None:
  print(r"""rsyncr  (C) Arne Bachmann 2017-2024
    This rsync wrapper simplifies backing up the current directory tree.

    Syntax:  rsyncr <target-path> [options]

    <target-path>  - either a local folder /path or Drive:\path  or a remote path [rsync://][user@]host:/path
        Drive:     - use that drive's current folder (Windows only)
        Drive:\~   - use same path on that target drive

    Copy mode options (default: update):
      --add                -a  Immediately copy only additional files (otherwise add + update modified)
      --sync               -s  Remove files in target that were removed in source, also empty folders
      --del                -d  Only remove files, do not add nor update
      --simulate           -n  Don't actually sync, stop after simulation
      --estimate               Estimate copy speed
      --file <file path>       Transfer a single local file instead of synchronizing a folder
      --user <user name>   -u  Manual remote user name specification, unless using user@host notation
      --skip-move              Do not compute potential moves

    Interactive options:
      --ask                -i  In case of dangerous operation, ask user interactively
      --force-dir          -f  Sync even if target folder name differs
      --force              -y  Sync even if deletions or moved files have been detected
      --force-copy             Force writing over existing files

    Generic options:
      --flat       -1  Don't recurse into sub folders, only operate on current folder
      --checksum   -C  Full file comparison using checksums
      --compress   -c  Compress data during transport, handle many files better
      --verbose    -v  Show more output
      --help       -h  Show this information

    Special options:
      --benchmark       re-run the benchmark on distance measures, e.g., after installing a new library
      --with-checksums  corrupDetect compatibility: if set, .corrupdetect files are *not* ignored
    """)
  import sys; sys.exit(0)
