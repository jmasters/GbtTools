#/usr/bin/env python
import sys
import matplotlib
matplotlib.use('TkAgg') # will this cause problems with the wx panels used in turtle?
from matplotlib import pyplot
from kapteyn import maputils
from kapteyn import celestial
from kapteyn import positions
from kapteyn.mplutil import VariableColormap, TimeCallback
import numpy
from matplotlib import mlab
import subprocess
import shlex
from datetime import datetime
import re

DEBUG = False
#DEBUG = True

class Sim:
    """General class for simulation points"""
    def __init__(self):
        pass
    
    def startSim(self):
        pass
    
    def hasNextPoint(self):
        pass
    
    def getNextPoint(self):
        pass
    
    def endSim(self):
        pass

class SimSim(Sim):
    """Class to simulate the simulator output for testing"""
    def __init__(self, filename):
        # file should be tab-delimited: ra dec offset
        # for example,
        #06:40:19.14	10:14:31.46	None
        #06:41:05.10	10:15:00.14	Galactic + (-00:03:00.00, -00:03:00.00) cosv
        self.filename = filename
        self.file = None
        self.line = None
        
    def startSim(self):
        """Start the simulation"""
        self.file = open(self.filename, "r")
        
    def hasNextPoint(self):
        """Check if file has more points"""
        return self.line != ''
        
    def getNextPoint(self):
        """Get next point from file"""
        self.line = self.file.readline()
        if self.line != '':
            ra, dec, offset = self.line.split("\t")
            offset = offset[:-1] # remove newline
            # offset could be done differently (look at __repr__) but this works
            return (ra, dec, offset)
        return (None, None, None)
    
    def endSim(self):
        """End simulation"""
        self.file.close()

class SimPts(Sim):
    """Class to hold actual simulator points"""
    def __init__(self, pts):
        self.pts = pts
        self.curpt = 0
    
    def hasNextPt(self):
        return self.curpt < len(self.pts)
    
    def getNextPt(self):
        rp = self.pts[self.curpt]
        self.curpt += 1
        return rp

class BeamMap:
    def __init__(self, pts=None, file="turtleall.txt"):
        """Initialize mapper.  If no points given, reads from file instead."""
        # Points to use in simulation
        if pts is None:
            self.sim = SimSim(file)
        else:
            self.sim = SimPts(pts)
        
        self.imagename = "__example1.fits"
        
        rbounds, dbounds = self.findBounds()
        self.size = [rbounds[1]-rbounds[0], dbounds[1]-dbounds[0]]
        
        # format center pos: HH MM SS
        center = [celestial.lon2hms(sum(rbounds)/2.0), celestial.lat2dms(sum(dbounds)/2.0)]
        self.position = [re.sub("[hdms]|\.\w+", " ", c).strip() for c in center]
        
        if DEBUG:
            print 'bounds are',rbounds,'and',dbounds
            print 'which correspond to',[celestial.lon2hms(rb) for rb in rbounds],
            print 'and',[celestial.lat2dms(db) for db in dbounds]
            print 'got size',self.size
            print 'got position',self.position
            print '---------------------------'
    
    def findBounds(self):
        """Find the boundaries of the scan, return in lat/lon
        Does this by running through the simulation
        """
        minra, maxra, mindec, maxdec = [None]*4
        
        self.sim.startSim()
        #sim = SimSim("/users/emcnany/Desktop/turtleall.txt")
        
        ra, dec, offset = self.sim.getNextPoint()
        while self.sim.hasNextPoint():
            if offset == "None":
                offset = ('00:00:00','00:00:00')
            else:
                offset = offset[offset.find("(")+1:offset.find(")")].split(", ")
            offra, offdec = offset
            
            ra = self.getDegFromHMS(ra) + self.getDegFromHMS(offra)
            if ra < minra or minra is None:         minra = ra
            elif ra > maxra or maxra is None:       maxra = ra
            
            dec = self.getDegFromDMS(dec) + self.getDegFromDMS(offdec)
            if dec < mindec or mindec is None:      mindec = dec
            elif dec > maxdec or maxdec is None:    maxdec = dec
            
            ra, dec, offset = self.sim.getNextPoint()
        
        self.sim.endSim()
        return ((minra, maxra), (mindec, maxdec))
    
    def hz2wavelength(self, f):
        """Simple frequency (Hz) to wavelength conversion
        Keywords: f -- input frequency in Hz
        Returns: wavelength in meters
        """
        c = 299792458  # speed of light in m/s
        return (c/f)
    
    def gbtbeamsize(self, hz):
        """Estimate the GBT beam size at a given frequency
        Keywords: hz -- frequency in Hz
        Returns: beam size in arc seconds
        """
        wavelength = self.hz2wavelength(hz)
        diameter = 100 # estimate of telescope diameter in m
        # return diffraction limit in arc seconds
        return ((1.22*wavelength)/diameter)*206265
    
    def get_background_image(self, filename,position,survey,size,pixels,debug=False):
        command = "perl skvbatch_wget" +\
          " file=" + filename + " " +\
          " position=" + position +\
          " Survey=" + survey +\
          " size=" + size +\
          " pixels=" + pixels
    
        if debug:
            print shlex.split(command)
            print command
        p = subprocess.Popen(shlex.split(command))
        p.communicate()
    
    def getDegFromHMS(self, hmsstr):
        """Get the degrees from a HH:MM:SS.ss format string"""
        hmsstr = "%sh%sm%ss"%tuple(hmsstr.split(":"))
        hms = positions.parsehmsdms(hmsstr)[0][0]
        if hmsstr.startswith("-"):
            # check if negative - positions module doesn't take into account
            hms = -1 * hms
        return hms
        
    def getDegFromDMS(self, dmsstr):
        """Get the degrees from a DD:MM:SS.ss format string"""
        dmsstr = "%sd%sm%ss"%tuple(dmsstr.split(":"))
        dms = positions.parsehmsdms(dmsstr)[0][0]
        if dmsstr.startswith("-"):
            # check if negative - positions module doesn't take into account
            dms = -1 * dms
        return dms
    
    def plot_path(self, annim, canvas):
        """Plot line of path between points"""
        #TODO
        pass
    
    def plot_beam(self, cb):
        """Plot current beam point"""
        ra, dec, offset = self.sim.getNextPoint()
        
        if not self.sim.hasNextPoint():
            self.sim.endSim()
            cb.deschedule()
            return
        
        if offset == "None":
            offset = ('00:00:00','00:00:00')
        else:
            offset = offset[offset.find("(")+1:offset.find(")")].split(", ")
        offra, offdec = offset
        
        ra = self.getDegFromHMS(ra) + self.getDegFromHMS(offra)
        dec = self.getDegFromDMS(dec) + self.getDegFromDMS(offdec)
        
        #centerfreq = float(row[29])
        #beamsize = (self.gbtbeamsize(centerfreq)/60/60)
        # not sure how to find this from simulation, hard-coding for now
        beamsize = 0.01
        color = 'r'
        if DEBUG:
            print '---------------------------'
            print 'count',cb.count
            print 'ra,dec',ra,dec,'or',celestial.lon2hms(ra),celestial.lat2dms(dec)
            print 'beamsize', beamsize
            #print 'target ra,dec',celestial.lon2hms(ra_targ),celestial.lat2dms(dec_targ)
        
        #oldra, olddec = cb.lastpt
        #cb.lastpt = (ra, dec)
        beam = cb.annim.Beam(beamsize, beamsize/2, 0, xc=ra, yc=dec, #pos=pos,
                          fc=color, fill=True, alpha=.5)
        
        background = cb.canvas.copy_from_bbox(cb.annim.frame.bbox)
        cb.annim.objlist = [beam]
        cb.canvas.restore_region(background)
        cb.canvas.blit(cb.annim.frame.bbox)
        cb.annim.plot()
    
        for beam in cb.annim.frame.patches:
            cb.annim.frame.draw_artist(beam)
        
        cb.annim.frame.patches = []
        cb.count = cb.count + 1
    
    def main(self):
        ra = self.position[0]
        dec = self.position[1]
        # add a border of 10%
        ra_width = self.size[0] * 1.1
        dec_width = self.size[1] * 1.1
        
        position = "\'"+ra+','+dec+"\'"
        survey = "\'Digitized Sky Survey\'"
        size = "\'"+str(ra_width)+','+str(dec_width)+"\'"
        max_pix = 400
        if (ra_width == dec_width):
            ra_pix = max_pix
            dec_pix = max_pix
        elif ra_width > dec_width:
            ra_pix = max_pix
            dec_pix = int((ra_pix/ra_width) * dec_width)
        else:
            dec_pix = max_pix
            ra_pix = int((dec_pix/dec_width) * ra_width)
        pixels = "\'"+str(ra_pix)+','+str(dec_pix)+"\'"
    
        # retrieve a background image from skyview
        self.get_background_image(self.imagename,position,survey,size,pixels)
    
        fig = pyplot.figure()
        frame = fig.add_axes([0.05, 0.05, 0.85, 0.85])
    
        # try to open it
        try:
            fitsobj = maputils.FITSimage(self.imagename)
            annim = fitsobj.Annotatedimage(frame,cmap='binary')
            image = annim.Image()
            grat = annim.Graticule()
            grat.setp_ticklabel(wcsaxis=1, fmt='HMS')   # Exclude seconds in label
            annim.plot()
            annim.interact_toolbarinfo()
            #annim.interact_imagecolors()
            canvas = annim.frame.figure.canvas
        except(IOError):
            print 'ERROR: could not open fits image'
            sys.exit(8)
    
        # plot the path before plotting the beam
        self.plot_path(annim, canvas)
        self.sim.startSim()
        TimeCallback(self.plot_beam, .1, annim=annim, canvas=canvas, \
                     lastpt=None, count=0) # change every .1 s
        annim.objlist = []

# Command-line usage
if __name__ == "__main__":
    bm = BeamMap()
    bm.main()
    pyplot.show()
