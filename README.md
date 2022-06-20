# rsyncr

![GPLv3 logo](http://www.gnu.org/graphics/gplv3-127x51.png)

Awesome useful `rsync` convenience wrapper for Python 3.
Does the heavy lifting of finding potential problems, plus detects potential moves.

We recommend using `PyPy`, which appears to operate order(s) of magnitude faster during the (inefficient) file tree computations.


## Installation

```sh
pip install rsyncr
```

This includes the following dependencies: `typing_extensions`, `textdistance`, but would also make use of `fuzzywuzzy`, `StringDist`, `brew-distance`, `edit-distance`, `editdistance-s` or `editdistance` if installed.


## Usage

`rsyncr` always operates on the *current folder*.
You only specify the target folder (plus options).

```text
rsyncr <target-path> [options]
```

with options:

```text
rsyncr  (C) Arne Bachmann 2017-2022
    This rsync-wrapper simplifies backing up the current directory tree.

    Syntax:  rsyncr <target-path> [options]

    target-path is either a local folder /path or Drive:\path  or a remote path [rsync://][user@]host:/path
      using Drive:    -  use the drive's current folder (Windows only)
      using Drive:\~  -  use full source path on target drive

    Copy mode options (default: update):
      --add                -a  Immediately copy only additional files (otherwise add, and update modified)
      --sync               -s  Remove files in target if removed in source, including empty folders
      --del                -d  Only remove files, do not add nor update
      --simulate           -n  Don't actually sync, stop after simulation
      --estimate               Estimate copy speed
      --file <file path>       Transfer a single local file instead of synchronizing a folder
      --user <user name>   -u  Manual remote user name specification, unless using user@host notation
      --skip-move              Do not compute potential moves

    Interactive options:
      --ask                -i  In case of dangerous operation, ask user interactively
      --force-foldername   -f  Sync even if target folder name differs
      --force              -y  Sync even if deletions or moved files have been detected
      --force-copy             Force writing over existing files

    Generic options:
      --flat       -1  Don't recurse into sub folders, only operate on current folder
      --checksum   -C  Full file comparison using checksums
      --compress   -c  Compress data during transport, handle many files better
      --verbose    -v  Show more output
      --help       -h  Show this information

    Special options:
      --with-checksums  corrupDetect compatibility: if set, .corrupdetect files are not ignored
```


## rsync details
rsync status output explanation:

```
Source: https://stackoverflow.com/questions/4493525/rsync-what-means-the-f-on-rsync-logs
1: > received,  . unchanged or modified (cf. below), c local change, * message, e.g. deleted, h hardlink, * = message following (no path)
2: f file, d directory, L symlink, D device, S special
3: c checksum of orther change
4: s size change
5: t time change
6: p permission
7: o owner
8: g group
9: u future
10: a ACL (not available on all systems)
11: x extended attributes (as above)
```

### rsync options

https://linux.die.net/man/1/rsync
```
-r  --recursive  recursive
-R  --relative   preserves full path
-u  --update     skip files newer in target (to avoid unnecessary write operations)
-i  --itemize-changes  Show results (itemize - necessary to allow parsing)
-t  --times            keep timestamps
-S  --sparse           sparse files handling
-b  --backup           make backups using the "~~" suffix (into folder hierarchy), use --backup-dir and --suffix to modify base backup dir and backup suffix. A second sync will remove backups as well!
-h  --human-readable   ...
-c  --checksum         compute checksum, don't use name, time and size
--stats                show traffic stats
--existing             only update files already there
--ignore-existing      stronger than -u: don't copy existing files, even if older than in source
--prune-empty-dirs     on target, if updating
-z, --compress --compress-level=9
```
