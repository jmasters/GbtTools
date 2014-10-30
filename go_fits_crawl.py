#!/usr/bin/env python

import os
import fnmatch
import pyfits
import sqlite3

conn = sqlite3.connect('gbt-metadata-archive.db')
c = conn.cursor()

GOFITS_KEYS = {'INSTRUME':'text','GBTMCVER':'text','SIMULATE':'text','DATE-OBS':'text','TIMESYS':'text','OBJECT':'text','PROJID':'text','OBSID':'text','SCAN':'integer','OBSERVER':'text','PROCNAME':'text','PROCTYPE':'text','OBSTYPE':'text','SWSTATE':'text','SWTCHSIG':'text','COORDSYS':'text','RADESYS':'text','EQUINOX':'text','RA':'real','DEC':'real'}

tablecols = ','.join(['`'+d+'` '+ GOFITS_KEYS[d] for d in sorted(GOFITS_KEYS)])
print "create table gbt(" + tablecols + ")"
c.execute("create table gbt(" + tablecols + ")")

def locate(pattern, root=os.curdir):
    for path, dirs, files in os.walk(os.path.abspath(root)):
        if path.endswith('/GO') and not path.endswith('.bad/GO'):
            for filename in fnmatch.filter(files, pattern):
                yield os.path.join(path, filename)
 
def main():
    for i, file in enumerate(locate("*.fits", "/home/archive/science-data/tape-0001")):

        # if file is empty, continue
        if os.stat(file).st_size==0:
            continue

        item = []
        fd = pyfits.open(file,memmap=1,mode='readonly')
        for headerkey in (sorted(GOFITS_KEYS)):
            try:
                value = fd[0].header[headerkey]
                item.append(value)

            except (KeyError):
                item.append(None)
            except (IndexError):
                print i,file

        insertcmd = 'insert into gbt values ('+('?,'*len(GOFITS_KEYS))[:-1]+')'
        c.execute(insertcmd, item)
        fd.close()

    conn.commit()
    c.close()

    return    

if __name__ == "__main__":
    main()
