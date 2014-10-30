# Copyright (C) 2004 Associated Universities, Inc. Washington DC, USA.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 675 Mass Ave Cambridge, MA 02139, USA.
#
# Correspondence concerning GBT software should be addressed as follows:
#     GBT Operations
#     National Radio Astronomy Observatory
#     P. O. Box 2
#     Green Bank, WV 24944-0002 USA

# $Id: __init__.py,v 1.16 2007/09/19 13:54:45 mclark Exp $

"""
The turtle.ygor module is the lowest module in the turtle API.  While
it is currently implemented using grail, it is conceivable that all
its functionality could eventually be incorporated (along with grail)
into a more general gbt.ygor module.  (Replacing the current gbt.ygor
module, which has been deprecated.)

Here we define a narrow interface to the live M&C system, so that
higher level modules can provide proxy objects that manage execution
plans.
"""

# Currently, we only export Telescope, as that should be the only
# class needed for what is currently called "observe".  Other classes
# in this module are more directly useful for "config", and one day we
# will dissolve the artificial distinction between the two.  But for
# now, we don't want our objects exposing themselves.
from Telescope     import Telescope
from TSimulator     import TSimulator
from TPlotter       import TPlotter

# Well, OK, that was a little lie.  Offset and Location belong in this
# module as well, and they are good, general purpose utility classes
# that should be exported.
from AntennaPosition  import AntennaPosition
from CIDictionary     import CIDictionary
from Conic            import Conic
from Ephemeris        import Ephemeris
from FocusPosition    import FocusPosition
from ILocation        import ILocation
from Location         import Location
from Loci             import Loci
from NNTLE            import NNTLE
from IOffset          import IOffset
from Offset           import Offset
from Orbit            import Orbit
from RadialVelocity   import RadialVelocity
from SolarSystem      import SolarSystem
from SourceDictionary import SourceDictionary
from PVA              import PVA
from Trajectory       import Trajectory, TrajectorySegment
from SubFocus         import SubFocus
from SubHome          import SubHome
from SubMotion        import SubMotion, SubMotionSegment
from SubNod           import SubNod
from SubNull          import SubNull
