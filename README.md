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

```sh
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
