#!/bin/bash
source /home/apps/headas-linux/lhea-init.sh
for d in `find /home/archive/science-data/tape-0001/ -wholename '*/GO/*.fits'`
do
    for key in PROJID OBSERVER OBJECT OBSTYPE RADESYS RA DEC SKYFREQ
    do
        fkeypar ${d}[0] ${key}
        echo -n `pget fkeypar value`, >> archive.csv
    done
    echo >> archive.csv
done
