# Copyright (C) 2017-2023 Arne Bachmann. All rights reserved
# HINT: there is the difflib.get_close_matches() function in the stdlib

import contextlib, itertools, logging, pathlib, sys, time
from appdirs import AppDirs  # for persistence of benchmark result
from beartype.typing import cast, Dict, Generator, Iterator, List, Protocol, Set

if '--test' in sys.argv: logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format="%(message)s")
_log = logging.getLogger(); debug, info, warn, error = _log.debug, _log.info, _log.warning, _log.error


config_dir:str = AppDirs("rsyncr", "AB").user_config_dir


class DistanceMeasure(Protocol):
  # returns a positive, non-normalized number used for ordering (might correspond with MAX_EDIT_DISTANCE)
  __name__: str
  def __call__(_, a:str, b:str) -> int|float: ...


FUNCS:Set[DistanceMeasure] = set()


# Conditional function definition for cygwin under Windows
if sys.platform == 'win32':  # this assumes that rsync for windows is built using cygwin internals
  def cygwinify(path:str) -> str:
    r''' Convert file path to cygwin path.

    >>> cygwinify(r"C:\hello\world.txt")
    '/cygdrive/c/hello/world.txt'
    >>> cygwinify(r"X::::\\hello///world.txt")
    '/cygdrive/x/hello/world.txt'
    '''
    p:str = path.replace("\\", "/")
    while "//" in p: p = p.replace("//", "/")
    while "::" in p: p = p.replace("::", ":")
    if ":" in p:  # cannot use os.path.splitdrive on linux/cygwin
      x:List[str] = p.split(":")
      p = "/cygdrive/" + x[0].lower() + x[1]
    return p[:-1] if p[-1] == "/" else p
else:
  def cygwinify(path:str) -> str: return path.rstrip('/')


def run_tests(func:DistanceMeasure) -> float:
  ''' Measure speed of the distance function. '''
  debug(f"Benchmark {func.__name__}")
  start:float = time.time()
  for i in range(1):  # HINT range can be increased to adapt test speed
    for a, b, c, d in itertools.product(range(ord('A'), ord('E') + 1), range(ord('A'), ord('E') + 1), range(ord('A'), ord('D') + 1), range(ord('A'), ord('D') + 1)):
      for e, f, g, h in itertools.product(range(ord('A'), ord('E') + 1), range(ord('A'), ord('E') + 1), range(ord('A'), ord('D') + 1), range(ord('A'), ord('D') + 1)):
        x:str = chr(a) + chr(b) + chr(c) + chr(d)
        y:str = chr(e) + chr(f) + chr(g) + chr(h)
        func(x, y)
  return time.time() - start


def benchmark(funcs:Set[DistanceMeasure]) -> DistanceMeasure:
  ''' Automatic determination of fastest distance measure. '''
  results:Dict[DistanceMeasure,float] = {func: run_tests(func) for func in funcs}
  return min([(duration, func) for func, duration in results.items()])[1]


def probe(name) -> Generator[str|None,DistanceMeasure,None]:
  ''' Check if the distance measure 'name' is available. '''
  debug(f"Probe {name}")
  func:DistanceMeasure = yield name
  func.__name__ = name
  FUNCS.add(func)
  debug(f"Loaded {name}")
  yield None


@contextlib.contextmanager
def probe_library(name:str) -> Iterator[Generator[str|None,DistanceMeasure,None]]:
  try:
    it = iter(probe(name))
    for step in it:  # yield None
      if step: yield it  # ignore yield None
  except (ImportError, AssertionError) as e: warn(e)


_distance:DistanceMeasure
# https://github.com/seatgeek/fuzzywuzzy (+ https://github.com/ztane/python-Levenshtein/) TODO avoid this try chain if --no-move
with probe_library("fuzzywuzzy") as libs:
  from fuzzywuzzy import fuzz as _fuzz  # type: ignore
  _distance = lambda a, b: (100 - _fuzz.ratio(a, b)) / 20  # noqa: E731  # similarity score 0..100
  assert _distance("abc", "abe") == 1.65  # type: ignore  # error: <nothing> not callable  [misc]
  assert _distance("abc", "cbe") == 3.35  # type: ignore
  libs.send(_distance)

# with contextlib.suppress(ImportError, AssertionError):
#   from textdistance import DamerauLevenshtein  # type: ignore
#   def _distance(a, b) -> float: return DamerauLevenshtein.normalized_distance(a, b)  # type: ignore  # h = hamming, l = levenshtein, dl = damerau-levenshtein
#   from textdistance import distance as _distance  # type: ignore  # https://github.com/orsinium/textdistance, now for Python 2 as well
#   def _distance(a, b) -> float: return _distance('l', a, b)  # type: ignore  # h = hamming, l = levenshtein, dl = damerau-levenshtein
#   assert _distance("abc", "cbe") == 2  # until bug has been fixed
#   debug("Using textdistance library")

# https://pypi.python.org/pypi/StringDist/1.0.9
with probe_library("StringDist") as libs:
  from stringdist import levenshtein as _distance0  # type: ignore
  assert _distance0("abc", "cbe") == 2
  libs.send(_distance0)

# https://github.com/dhgutteridge/brew-distance  slow implementation
with probe_library("brew_distance") as libs:
  from brew_distance import distance as _distance01  # type: ignore
  _distance = lambda a, b: _distance01(a, b)[0]  # type: ignore  # noqa: E731  # [1] contains operations
  assert _distance("abc", "cbe") == 2  # type: ignore  # until bug has been fixed
  libs.send(_distance)

# https://github.com/belambert/edit-distance  slow implementation
with probe_library("edit_distance") as libs:
  from edit_distance import SequenceMatcher as _distance1  # type: ignore
  _distance = lambda a, b: _distance1(a, b).distance()  # noqa: E731
  assert _distance("abc", "cbe") == 2  # type: ignore
  libs.send(_distance)

# https://github.com/asottile/editdistance-s
with probe_library("editdistance_s") as libs:
  from editdistance_s import distance as _distance2  # type: ignore
  assert _distance2("abc", "cbe") == 2
  libs.send(_distance2)

# https://pypi.python.org/pypi/editdistance/0.2
with probe_library("editdistance") as libs:
  from editdistance import eval as _distance3  # type: ignore
  assert _distance3("abc", "cbe") == 2
  libs.send(lambda a, b: _distance3(a, b))


best_measures:str = ''
with contextlib.suppress(Exception):
  best_measures = (pathlib.Path(config_dir) / '.rsyncr.cfg').read_text() if '--benchmark' not in sys.argv else ''

if FUNCS:
  distance:DistanceMeasure = benchmark(FUNCS) if not best_measures else [func for func in FUNCS if func.__name__ == best_measures][0]
  info(f"Use {distance.__name__} library")
  del FUNCS
  if not best_measures:
    with contextlib.suppress(Exception): import os; os.makedirs(config_dir, exist_ok=True); (pathlib.Path(config_dir) / '.rsyncr.cfg').write_text(distance.__name__)
else:
  # simple distance measure fallback
  distance = cast(DistanceMeasure, lambda a, b: 0. if a == b else 1.)
  assert distance("abc", "cbe") == 1
  distance.__name__ = "simple comparison"
  warn("Fall back to simple comparison")
