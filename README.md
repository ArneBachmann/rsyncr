# rsyncr #

![GPLv3 logo](http://www.gnu.org/graphics/gplv3-127x51.png)

Awesome useful `rsync` convenience wrapper for Python 2.
Does the heavy lifting of finding potential problems, plus detects potential moves.

We recommend using `PyPy`, which appears to operate order(s) of magnitude faster during the (inefficient) file tree computations.

## Installation ##

```sh
pip install rsyncr
```

## Usage ##

```text
rsyncr <target-path> [options]
```

with options:

```text
Copy mode options (default: update):
  --add               -a  Copy only additional files (otherwise updating only younger files)
  --sync              -s  Remove files in target if removed in source, including empty folders
  --simulate          -n  Don't actually sync, stop after simulation
  --force-foldername  -f  Sync even if target folder name differs
  --force             -y  Sync even if deletions or moved files have been detected
  --ask               -i  In case of dangerous operation, ask user interactively

Generic options:
  --flat              -1  Don't recurse into sub folders, only copy current folder
  --compress          -c  Compress data during transport, handle many files better
  --verbose           -v  Show more output
  --help              -h  Show this information
```


## rsync details
rsync status output explanation:
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

### rsync options
 https://linux.die.net/man/1/rsync
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
