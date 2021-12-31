import sys

verbose = '--verbose' in sys.argv or '-v' in sys.argv


# Conditional function definition for cygwin under Windows
if sys.platform == 'win32':  # this assumes that the rsync for windows build is using cygwin internals
  def cygwinify(path:str) -> str:
    p = path.replace("\\", "/")
    while "//" in p: p = p.replace("//", "/")
    while "::" in p: p = p.replace("::", ":")
    if ":" in p:  # cannot use os.path.splitdrive on linux/cygwin
      x = p.split(":")
      p = "/cygdrive/" + x[0].lower() + x[1]
    return p[:-1] if p[-1] == "/" else p
else:
  def cygwinify(path:str) -> str: return path[:-1] if path[-1] == "/" else path


try:  # https://github.com/seatgeek/fuzzywuzzy (+ https://github.com/ztane/python-Levenshtein/) TODO avoid this try chain if --no-move
  from fuzzywuzzy import fuzz  # type: ignore
  def distance(a, b): return (100 - fuzz.ratio(a, b)) / 20  # similarity score 0..100
  assert distance("abc", "abe") == 1.65; assert distance("abc", "cbe") == 3.35
  if verbose: print("Using fuzzywuzzy library")
except:
  try:
    from textdistance import distance as _distance  # type: ignore  # https://github.com/orsinium/textdistance, now for Python 2 as well
    def distance(a, b): return _distance('l', a, b)  # type: ignore  # h = hamming, l = levenshtein, dl = damerau-levenshtein
    assert distance("abc", "cbe") == 2  # until bug has been fixed
    if verbose: print("Using textdistance library")
  except:
    try:
      from stringdist import levenshtein as distance  # type: ignore  # https://pypi.python.org/pypi/StringDist/1.0.9
      assert distance("abc", "cbe") == 2
      if verbose: print("Using StringDist library")
    except:
      try:
        from brew_distance import distance as _distance  # type: ignore  # https://github.com/dhgutteridge/brew-distance  slow implementation
        def distance(a, b): return _distance(a, b)[0]  # [1] contains operations  # type: ignore
        assert distance("abc", "cbe") == 2  # until bug has been fixed
        if verbose: print("Using brew_distance library")
      except:
        try:
          from edit_distance import SequenceMatcher as _distance  # type: ignore  # https://github.com/belambert/edit-distance  slow implementation
          def distance(a, b): return _distance(a, b).distance()
          assert distance("abc", "cbe") == 2
          if verbose: print("Using edit_distance library")
        except:
          try:
            from editdistance_s import distance  # type: ignore  # https://github.com/asottile/editdistance-s
            assert distance("abc", "cbe") == 2
            if verbose: print("Using editdistance_s library")
          except:
            try:  # https://github.com/asottile/editdistance-s
              from editdistance import eval as distance  # type: ignore  # https://pypi.python.org/pypi/editdistance/0.2
              assert distance("abc", "cbe") == 2
              if verbose: print("Using editdistance library")
            except:
              def distance(a, b): return 0 if a == b else 1  # simple distance measure fallback
              assert distance("abc", "cbe") == 1
              if verbose: print("Using simple comparison")
