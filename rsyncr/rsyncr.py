# (C) 2017-2022 Arne Bachmann. All rights reserved
# TODO add encoding header

# TODO moved contains deleted - but uncertain?
# TODO rsync wrapper script that supports humans in detecting dangerous changes to a folder structure synchronization.
# The script highlights the main changes and detects potential unwanted file deletions, while hinting to moved files that might correspond to a folder rename or move.

# TODO tests failing
# TODO copying .git folders (or any dot-folders?) changes the owner and access rights! This leads to problems on consecutive syncs

from __future__ import annotations
import time; time_start:float = time.time()
import collections, functools, os, subprocess, sys, textwrap
assert sys.version_info >= (3, 7)  # version 3.6 ensures maximum roundtrip chances, but is end of live already
from typing import cast, Any, Callable, Dict, Iterable, List, NamedTuple, Optional, Set, Tuple
from typing_extensions import Final
from .distance import cygwinify, distance
from .help import help


# Parse program options
add      = '--add'        in sys.argv or '-a' in sys.argv
sync     = '--sync'       in sys.argv or '-s' in sys.argv
delete   = '--del'        in sys.argv or '-d' in sys.argv
simulate = '--simulate'   in sys.argv or '-n' in sys.argv
force    = '--force'      in sys.argv or '-y' in sys.argv
ask      = '--ask'        in sys.argv or '-i' in sys.argv
flat     = '--flat'       in sys.argv or '-1' in sys.argv
compress = '--compress'   in sys.argv or '-c' in sys.argv
verbose  = '--verbose'    in sys.argv or '-v' in sys.argv
checksum = '--checksum'   in sys.argv or '-C' in sys.argv
backup   = '--backup'     in sys.argv
override = '--force-copy' in sys.argv
estimate = '--estimate'   in sys.argv
usage    = len(sys.argv) < 2 or '--help' in sys.argv or '-' in sys.argv or '-?' in sys.argv or '/?' in sys.argv
force_foldername = '--force-foldername' in sys.argv or '-f' in sys.argv
cwdParent = file = rsyncPath = source = target = ""
protocol = 0; rversion = (0, 0)
if usage: help()


# Settings
MAX_MOVE_DIRS:int = 2  # don't display more than this number of potential directory moves
MAX_EDIT_DISTANCE = 5  # insertions/deletions/replacements (and also moves for damerau-levenshtein)
MEBI:int          = 1024 << 10
QUOTE:str = '"' if sys.platform == "win32" else ""
FEXCLUDE:List[str] = ['*~~'] + ([".corruptdetect"] if '--with-checksums' not in sys.argv else [])  # ~~to avoid further copying of previous backups
DEXCLUDE:List[str] = ['.redundir', '.imagesubsort_cache', '.imagesubsort_trash', '$RECYCLE.BIN', 'System Volume Information', 'Recovery', 'catalog Previews.lrdata']

# Rsync output classification
State: Final[Dict[str,str]]  = {".": "unchanged", ">": "store", "c": "changed", "<": "restored", "*": "message"}  # rsync output marker detection
Entry: Final[Dict[str,str]]  = {"f": "file", "d": "dir", "u": "unknown"}
Change:Final[Dict[str,bool]] = {".": False, "+": True, "s": True, "t": True}  # size/time have [.+st] in their position
FileState:NamedTuple = collections.namedtuple("FileState", ["state", "type", "change", "path", "newdir", "base"])  # 9 characters and one space before relative path


# Utility functions TODO benchmark this
def xany(pred:Callable[[Any], bool], lizt:Iterable[Any]) -> bool: return functools.reduce(lambda a, b: a or  pred(b), lizt if hasattr(lizt, '__iter__') else list(lizt), False)
def xall(pred:Callable[[Any], bool], lizt:Iterable[Any]) -> bool: return functools.reduce(lambda a, b: a and pred(b), lizt if hasattr(lizt, '__iter__') else list(lizt), True)


def parseLine(line:str) -> FileState:
  ''' Parse one rsync item.

  Must be called from the checkout folder.
  >>> print(parseLine("cd+++++++++ 05 - Bulgarien/07"))
  FileState(state='changed', type='dir', change=False, path='/rsyncr/05 - Bulgarien/07', newdir=True, base='07')
  >>> print(parseLine("*deleting   05 - Bulgarien/IMG_0648.JPG"))
  FileState(state='deleted', type='unknown', change=True, path='/rsyncr/05 - Bulgarien/IMG_0648.JPG', newdir=False, base='IMG_0648.JPG')
  >>> print(parseLine(">f+++++++++ 05 - Bulgarien/07/IMG_0682.JPG"))
  FileState(state='store', type='file', change=False, path='/rsyncr/05 - Bulgarien/07/IMG_0682.JPG', newdir=False, base='IMG_0682.JPG')
  '''
  atts:str  = line.split(" ")[0]  # until space between itemization info and path
  path:str  = line[line.index(" ") + 1:].lstrip(" ")
  state:str = cast(str, State.get(atts[0]))  # *deleting
  if state != "message":
    entry:str = Entry.get(atts[1], ""); assert entry  # f:file, d:dir
    change:bool = xany(lambda _: _ in "cstpoguax", atts[2:])  # check attributes for any change
  else:
    entry = Entry["u"]  # unknown type
    change = True
  path = cygwinify(os.path.abspath(path))
  newdir:bool = atts[:2] == "cd" and xall(lambda _: _ == "+", atts[2:])
  if state == "message" and atts[1:] == "deleting": state = "deleted"
  try: assert path.startswith(cwdParent + "/") or path == cwdParent
  except: raise Exception(f"Wrong path prefix: {path} vs {cwdParent}")
  path = path[len(cwdParent):]
  return FileState(state, entry, change, path, newdir, os.path.basename(path))


def estimateDuration() -> str:
  return f'{QUOTE}{rsyncPath}{QUOTE}' + \
     " -n --stats {rec}{addmode} '{source}' '{target}'".format(
      rec="-r " if not flat and not file else "",
      addmode="--ignore-existing " if add else ("-I " if override else "-u "),  # -I ignore-times (size only)
      source=source,
      target=target
    )


def constructCommand(simulate:bool) -> str:  # TODO -m prune empty dir chains from file list
  return f'{QUOTE}{rsyncPath}{QUOTE}' + \
       " {sim}{rec}{addmode}{delmode}{comp}{part}{bacmode}{units}{check} -i -t --no-i-r {exclude} '{source}' '{target}'".format(  # -t keep times, -i itemize
      sim="-n " if simulate else ("--info=progress2 -h " if protocol >= 31 or rversion >= (3, 1) else ""),
      rec="-r " if not flat and not file else "",  # TODO allow flat with --delete
      addmode="--ignore-existing " if add else ("--existing " if delete else ("-I " if override else "-u ")),  # --ignore-existing only copy additional files (vs. --existing: don't add new files) -u only copy if younger -I ignore times
      delmode="--delete-after --prune-empty-dirs --delete-excluded " if sync or delete else "",
      comp="-S -z --compress-level=6 " if compress else "",
      part="-P " if file else "",  # -P = --partial --progress
      bacmode=("-b --suffix='~~' " if backup else ""),
      units=("" if simulate else "-hh --stats "),  # using SI-units
      check="-c" if checksum else "",
      exclude=" ".join(f"--exclude='{fe}' --filter='P {fe}' "   for fe in FEXCLUDE) +
              " ".join(f"--exclude='{de}/' --filter='P {de}/' " for de in DEXCLUDE),  # P = exclude from deletion, meaning not copied, but also not removed it exists only in target.
      source=source,
      target=target
    )


def main():
  # Source handling
  global add, sync, delete, cwdParent, file, rsyncPath, source, target, protocol, version
  file = sys.argv[sys.argv.index('--file') + 1] if '--file' in sys.argv else None
  if file:
    del sys.argv[sys.argv.index('--file'):sys.argv.index('--file') + 2]
    if not os.path.exists(file): raise Exception(f"File not found '{file}'")
    file = file.replace("\\", "/")
    print(f"Running in single file transfer mode for '{file}'")
    while len(file) > 0 and file[0] == '/': file = file[1:]
    while len(file) > 0 and file[-1] == '/': file = file[:-1]

  # Target handling. Accepted target paths: D: (cwd on D:), or /local_path, or D:\local_path, or rsync://path, or rsync://user@path, arnee@rsync.hidrive.strato.com:/users/arnee/path/
  user:Optional[str] = sys.argv[sys.argv.index('--user') + 1] if '--user' in sys.argv else None
  if user: del sys.argv[sys.argv.index('--user'):sys.argv.index('--user') + 2]
  remote:Optional[str|bool] = None
  if sys.argv[1].startswith('rsync://'): sys.argv[1] = sys.argv[1].replace('rsync://', ''); remote = True
  if '@' in sys.argv[1]:  # must be a remote URL with user name specified
    user = sys.argv[1].split("@")[0]
    sys.argv[1] = sys.argv[1].split("@")[1]
    remote = True
  if user: print(f"Using remote account '{user}' for login")
  remote = remote or ':' in sys.argv[1][2:]  # ignore potential drive letter separator (in local Windows paths)
  if remote:  # TODO use getpass library
    if not user: raise Exception("User name required for remote file upload")
    if ':' not in sys.argv[1]: raise Exception("Expecting server:path rsync path")
    host = sys.argv[1].split(':')[0]  # host name
    path = sys.argv[1].split(':')[1]  # remote target path
    remote = cast(str, user) + "@" + host
    target = remote + ":" + path  # TODO this simply reconstructs what ws deconstructed above, right?
  else:  # local mode
    if sys.argv[1].strip().endswith(":"):  # just a drive letter - means current folder on that drive
      olddrive = os.path.abspath(os.getcwd())
      os.chdir(sys.argv[1])    # change drive
      drivepath = os.getcwd()  # get current folder on that drive
      os.chdir(olddrive)       # change back
    else: drivepath = sys.argv[1]
    if drivepath.rstrip("/\\").endswith(f"{os.sep}~") and sys.platform == "win32":
      drivepath = drivepath[0] + os.getcwd()[1:]  # common = os.path.commonpath(("A%s" % os.getcwd()[1:], "A%s" % drivepath[1:]))
    if drivepath != '--test' and not os.path.exists(drivepath): raise Exception(f"Target folder '{drivepath}' doesn't exist. Create it manually to sync. This avoids bad surprises!")
    target = cygwinify(os.path.abspath(drivepath))

  # Preprocess source and target folders
  rsyncPath = os.getenv("RSYNC", "rsync")  # allows definition of custom executable
  cwdParent = cygwinify(os.path.dirname(os.getcwd()))  # because current directory's name may not exist in target, we need to track its contents as its own folder
  if '--test' in sys.argv: import doctest; doctest.testmod(); sys.exit(0)
  if target[-1] != "/": target += "/"
  source = cygwinify(os.getcwd()); source += "/"
  if not remote:
    diff = os.path.relpath(target, source)
    if diff != "" and not diff.startswith(".."):
      raise Exception(f"Cannot copy to parent folder of source! Relative path: .{os.sep}{diff}")
  if not force_foldername and os.path.basename(source[:-1]).lower() != os.path.basename(target[:-1]).lower():
    raise Exception(f"Are you sure you want to synchronize from '{source}' to '{target}' using different folder names? Use --force-foldername or -f if yes")  # TODO E: to F: shows also warning
  if file: source += file  # combine source folder (with trailing slash) with file name
  if verbose:
    print(f"Operation: {'SIMULATE ' if simulate else ''}" + ("ADD" if add else ("UPDATE" if not sync else ("SYNC" if not override else "COPY"))))
    print(f"Source: {source}")
    print(f"Target: {target}")


  # Determine total file size
  output:str = subprocess.Popen(f"{QUOTE}{rsyncPath}{QUOTE} --version", shell=True, stdout=subprocess.PIPE, stderr=sys.stderr).communicate()[0].decode(sys.stdout.encoding).replace("\r\n", "\n").split("\n")[0]
  protocol = int(output.split("protocol version ")[1])
  assert output.startswith("rsync"), f"Cannot determine rsync version: {output}"  # e.g. rsync  version 3.0.4  protocol version 30)
  rversion = cast(Tuple[int,int], tuple([int(_) for _ in output.split("version ")[1].split(" ")[0].split(".")[:2]]))
  print(f"Detected rsync version {rversion[0]}.{rversion[1]}.x  protocol {protocol}")

  if estimate:
    command:str = estimateDuration()
    if verbose: print(f"\nAnalyzing: {command}")
    lines:List[str] = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=sys.stderr).communicate()[0].decode(sys.stdout.encoding).replace("\r\n", "\n").split("\n")
    line:str = [l for l in lines if l.startswith("Number of files:")][0]
    totalfiles:int = int(line.split("Number of files: ")[1].split(" (")[0].replace(",", ""))
    line = [l for l in lines if l.startswith("Total file size:")][0]
    totalbytes:int = int(line.split("Total file size: ")[1].split(" bytes")[0].replace(",", ""))
    print(f"\nEstimated run time for {totalfiles} entries: %.1f (SSD) %.1f (HDD) %.1f (Ethernet) %.1f (USB 3.0)" % (
      totalbytes / (60 *  130 * MEBI),   # SSD
      totalbytes / (60 *   60 * MEBI),   # HDD
      totalbytes / (60 * 12.5 * MEBI),   # 100 Mbit/s
      totalbytes / (60 *  0.4 * MEBI)))  # USB 3.0 TODO really?
    if not ask: input("Hit Enter to continue.")

  # Simulation rsync run
  if not file and (simulate or not add):  # only simulate in multi-file mode. in add-only mode we need not check for conflicts
    command = constructCommand(simulate=True)
    if verbose: print(f"\nSimulating: {command}")
    lines = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=sys.stderr).communicate()[0].decode(sys.stdout.encoding).replace("\r\n", "\n").split("\n")  # TODO allow different encodings per line? code was removed
    entries:List[FileState] = [parseLine(line) for line in lines if line != ""]  # parse itemized information
    entries[:] = [entry for entry in entries if entry.path != ""]  # throw out all parent folders (TODO might require makedirs())

    # Detect files belonging to newly create directories - can be ignored regarding removal or moving
    newdirs:Dict[str,List[str]] = {entry.path: [e.path for e in entries if e.path.startswith(entry.path) and e.type == "file"] for entry in entries if entry.newdir}  # associate dirs with contained files
    entries[:] = [entry for entry in entries if entry.path not in newdirs and not xany(lambda files: entry.path in files, newdirs.values())]
    # TODO why exclude files in newdirs from being recognized as moved? must be complementary to the movedirs logic

    # Main logic: Detect files and relationships
    #@functools.lru_cache(maxsize=99999)
    def new(entry:FileState) -> List[str]: return [e.path for e in addNames if e is not entry and entry.base == e.base]  # all entries not being the first one (which they shouldn't be anyway)
    addNames:List[FileState] = [f for f in entries if f.state == "store"]
    potentialMoves:Dict[str,List[str]] = {old.path: new(old) for old in entries if old.type == "unknown" and old.state == "deleted"}  # what about modified?
    removes:Set[str] = {rem for rem, froms in potentialMoves.items() if not froms}  # exclude entries that have no origin
    potentialMoves = {k: v for k, v in potentialMoves.items() if k not in removes}
    modified:List[str] = [entry.path for entry in entries if entry.type == "file" and entry.change and entry.path not in removes and entry.path not in potentialMoves]
    added:Set[str] = {entry.path for entry in entries if entry.type == "file" and entry.state in ("store", "changed") and entry.path and not xany(lambda a: entry.path in a, potentialMoves.values())}  # latter is a weak check
    modified[:] = [name for name in modified if name not in added]
    potentialMoveDirs:Dict[str,str] = {}
    if not add and '--skip-move' not in sys.argv and '--skip-moves' not in sys.argv:
      if verbose: print("Computing potential directory moves")  # HINT: a check if all removed files can be found in a new directory cannot be done, as we only that that a directory has been deleted, but nothing about its files
      potentialMoveDirs = {delname: ", ".join([f"{_[1]}:{_[0]}" for _ in sorted([(distance(os.path.basename(addname), os.path.basename(delname)), addname) for addname in newdirs.keys()]) if _[0] < MAX_EDIT_DISTANCE][:MAX_MOVE_DIRS]) for delname in potentialMoves.keys() | removes}
      potentialMoveDirs = {k: v for k, v in potentialMoveDirs.items() if v != ""}

    # User interaction
    if len(added)             > 0: print("%-5s added files"   % len(added))
    if len(modified)          > 0: print("%-5s chngd files"   % len(modified))
    if len(removes)           > 0: print("%-5s remvd entries" % len(removes))
    if len(potentialMoves)    > 0: print("%-5s moved files (maybe)" % len(potentialMoves))
    if len(newdirs)           > 0: print("%-5s Added dirs (including %d files)" % (len(newdirs), sum([len(files) for files in newdirs.values()])))
    if len(potentialMoveDirs) > 0: print("%-5s Moved dirs (maybe) " % len(potentialMoveDirs))
    if not (added or newdirs or modified or removes):
      print("Nothing to do.")
      if verbose: print("Finished after %.1f minutes." % ((time.time() - time_start) / 60.))
      if not simulate and ask: input("Hit Enter to exit.")
      sys.exit(0)
    while ask:
      selection = input(textwrap.dedent(f"""Options:
        show (a)dded ({len(added)}), (c)hanged ({len(modified)}), (r)emoved ({len(removes)}), (m)oved files ({len(potentialMoves)})
        show (A)dded ({len(newdirs)}:{sum(len(_) for _ in newdirs.values())}), (M)oved ({len(potentialMoveDirs)}) folders:files
        only (add), (sync), (update), (delete)
        or continue to {'sync' if sync else ('add' if add else 'update')} via (y)
        exit via <Enter> or (x)\n  => """))
      if   selection == "a": print("\n".join("  "   + add for add in added))
      elif selection == "t": print("\n".join("  "   + add for add in sorted(added, key = lambda a: (a[a.rindex("."):] if "." in a else a) + a)))  # by file type
      elif selection == "c": print("\n".join("  > " + mod for mod in sorted(modified)))
      elif selection == "r": print("\n".join("  "   + rem for rem in sorted(removes)))
      elif selection == "m": print("\n".join(f"  {_from} -> {_tos}" for _from, _tos in sorted(potentialMoves.items())))
      elif selection == "M": print("\n".join(f"  {_from} -> {_tos}" for _from, _tos in sorted(potentialMoveDirs.items())))
      elif selection == "A": print("\n".join(f"DIR {folder} ({len(files)} files)" + ("\n    " + "\n    ".join(files) if len(files) > 0 else "") for folder, files in sorted(newdirs.items())))
      elif selection == "y": force = True; break
      elif selection[:3] == "add":  add = True;  sync = False; delete = False; force = True; break  # TODO run simulation/estimation again before exectution
      elif selection[:4] == "sync": add = False; sync = True;  delete = False; force = True; break
      elif selection[:2] == "up":   add = False; sync = False; delete = False; force = True; break
      elif selection[:3] in ("del", "rem"):
                                    add = False; sync = False; delete = True;  force = True; break
      else: sys.exit(1)

    if len(removes) + len(potentialMoves) + len(potentialMoveDirs) > 0 and not force:
      print("\nPotentially harmful changes detected. Use --force or -y to run rsync anyway.")
      sys.exit(1)

  if not simulate:  # quit without execution
    command = constructCommand(simulate=False)
    if verbose: print(f"\nExecuting: {command}")
    subprocess.Popen(command, shell=True, stdout=sys.stdout, stderr=sys.stderr).wait()

  if verbose: print("Finished after %.1f minutes." % ((time.time() - time_start) / 60.))


if __name__ == '__main__': main()
