import sys
import os
from main import application

INTERP = os.path.expanduser("/var/www/u0688176/data/flaskenv/bin/python")
if sys.executable != INTERP:
   os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())
