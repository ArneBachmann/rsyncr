# coding=utf-8

# TODO add automatic benchmark via timeit for all available libraries and store fastest one

import logging, sys
from typing import List

_log = logging.getLogger(); debug, info, warn, error = _log.debug, _log.info, _log.warning, _log.error


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


# distance() returns a positive, non-normalized integer used for ordering - but corresponds with MAX_EDIT_DISTANCE
try:  # https://github.com/seatgeek/fuzzywuzzy (+ https://github.com/ztane/python-Levenshtein/) TODO avoid this try chain if --no-move
  from fuzzywuzzy import fuzz  # type: ignore
  def distance(a, b) -> float: return (100 - fuzz.ratio(a, b)) / 20  # similarity score 0..100
  assert distance("abc", "abe") == 1.65; assert distance("abc", "cbe") == 3.35
  debug("Using fuzzywuzzy library")
except:
#  try:
#    from textdistance import DamerauLevenshtein  # type: ignore
#    def distance(a, b) -> float: return DamerauLevenshtein.normalized_distance(a, b)  # type: ignore  # h = hamming, l = levenshtein, dl = damerau-levenshtein
#    from textdistance import distance as _distance  # type: ignore  # https://github.com/orsinium/textdistance, now for Python 2 as well
#    def distance(a, b) -> float: return _distance('l', a, b)  # type: ignore  # h = hamming, l = levenshtein, dl = damerau-levenshtein
#    assert distance("abc", "cbe") == 2  # until bug has been fixed
#    debug("Using textdistance library")
#  except:
    try:
      from stringdist import levenshtein as distance  # type: ignore  # https://pypi.python.org/pypi/StringDist/1.0.9
      assert distance("abc", "cbe") == 2
      debug("Using StringDist library")
    except:
      try:
        from brew_distance import distance as _distance  # type: ignore  # https://github.com/dhgutteridge/brew-distance  slow implementation
        def distance(a, b) -> float: return _distance(a, b)[0]  # [1] contains operations  # type: ignore
        assert distance("abc", "cbe") == 2  # until bug has been fixed
        debug("Using brew_distance library")
      except:
        try:
          from edit_distance import SequenceMatcher as _distance  # type: ignore  # https://github.com/belambert/edit-distance  slow implementation
          def distance(a, b) -> float: return _distance(a, b).distance()
          assert distance("abc", "cbe") == 2
          debug("Using edit_distance library")
        except:
          try:
            from editdistance_s import distance  # type: ignore  # https://github.com/asottile/editdistance-s
            assert distance("abc", "cbe") == 2
            debug("Using editdistance_s library")
          except:
            try:  # https://github.com/asottile/editdistance-s
              from editdistance import eval as distance  # type: ignore  # https://pypi.python.org/pypi/editdistance/0.2
              assert distance("abc", "cbe") == 2
              debug("Using editdistance library")
            except:
              def distance(a, b) -> float: return 0. if a == b else 1.  # simple distance measure fallback
              assert distance("abc", "cbe") == 1
              debug("Using simple comparison")
