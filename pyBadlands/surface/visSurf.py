##~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~##
##                                                                                   ##
##  This file forms part of the Badlands surface processes modelling application.    ##
##                                                                                   ##
##  For full license and copyright information, please refer to the LICENSE.md file  ##
##  located at the project root, or contact the authors.                             ##
##                                                                                   ##
##~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~##
"""
This class reads the TIN surface with associated parameters on output 3d surface within IPython notebook.
"""

import os
import time
import h5py
import numpy 
import errno
from scipy.spatial import cKDTree
import xml.etree.ElementTree as ETO

import plotly
from plotly.graph_objs import *
plotly.offline.init_notebook_mode()

class visSurf:
    """
    Class for plotting Badlands surface outputs using plotly.
    """

    def __init__(self, folder=None, ncpus=1, dx=None, timestep=0, crange=None):
        """
        Initialization function which takes the folder path to Badlands outputs
        and the number of CPUs used to run the simulation. It also takes the
        discretization value at which one wants to interpolate the data and the
        time step to load.

        Parameters
        ----------
        variable : folder
            Folder path to Badlands outputs.

        variable: ncpus
            Number of CPUs used to run the simulation.

        variable: dx
            Discretisation value in metres.
            
        variable : timestep
            Time step to load.
            
        variable : crange
            Min/max plotting range for cumulative erosion/deposition [m].

        """

        self.folder = folder
        if not os.path.isdir(folder):
            raise RuntimeError('The given folder cannot be found or the path is incomplete.')

        self.ncpus = ncpus
        self.x = None
        self.y = None
        self.z = None
        self.discharge = None
        self.logdischarge = None
        self.cumchange = None
        self.dx = None
        self.nx = None
        self.ny = None
        self.bbox = None
        self.timestep = timestep
        
        if dx == None:
            raise RuntimeError('Discretization space value is required.')
        self.dx = dx
        self.crange = crange

        self._loadHDF5()
        
        
        return
    
    
    def _loadHDF5(self):
        """
        Read the HDF5 file for a given time step.

        Parameters
        ----------
        variable : timestep
            Time step to load.

        """

        for i in range(0, self.ncpus):
            df = h5py.File('%s/tin.time%s.p%s.hdf5'%(self.folder, self.timestep, i), 'r')
            coords = numpy.array((df['/coords']))
            cumdiff = numpy.array((df['/cumdiff']))
            discharge = numpy.array((df['/discharge']))
            if i == 0:
                x = coords[:,0]
                y = coords[:,1]
                z = coords[:,2]
                c = cumdiff.ravel()
                d = discharge.ravel()
            else:
                c = numpy.append(c, cumdiff)
                d = numpy.append(d, discharge)
                x = numpy.append(x, coords[:,0])
                y = numpy.append(y, coords[:,1])
                z = numpy.append(z, coords[:,2])

        self.nx = int((x.max() - x.min())/self.dx+1)
        self.ny = int((y.max() - y.min())/self.dx+1)
        self.x = numpy.linspace(x.min(), x.max(), self.nx)
        self.y = numpy.linspace(y.min(), y.max(), self.ny)
        self.bbox = numpy.zeros(4,dtype=float)
        self.bbox[0] = x.min()
        self.bbox[1] = y.min()
        self.bbox[2] = x.max()
        self.bbox[3] = y.max()
        
        self.x, self.y = numpy.meshgrid(self.x, self.y)
        xyi = numpy.dstack([self.x.flatten(), self.y.flatten()])[0]
        XY = numpy.column_stack((x,y))
        tree = cKDTree(XY)
        distances, indices = tree.query(xyi, k=3)
        z_vals = z[indices]
        zi = numpy.average(z_vals,weights=(1./distances), axis=1)
        d_vals = d[indices]
        di = numpy.average(d_vals,weights=(1./distances), axis=1)
        c_vals = c[indices]
        ci = numpy.average(c_vals,weights=(1./distances), axis=1)

        onIDs = numpy.where(distances[:,0] == 0)[0]
        if len(onIDs) > 0:
            zi[onIDs] = z[indices[onIDs,0]]
            di[onIDs] = d[indices[onIDs,0]]
            ci[onIDs] = c[indices[onIDs,0]]

        self.z = numpy.reshape(zi,(self.ny,self.nx))
        
        if self.crange != None:
            cclip = numpy.clip(ci, self.crange[0], self.crange[1])
            self.cumchange = numpy.reshape(cclip,(self.ny,self.nx))
        else:
            self.cumchange = numpy.reshape(ci,(self.ny,self.nx))
            
        self.discharge = numpy.reshape(di,(self.ny,self.nx))

        logdis = self.discharge
        IDs = numpy.where(logdis<1.)
        logdis[IDs] = 1.
        self.logdischarge = numpy.log(logdis)
        
        return
    
    def plotSurf(self, width = 800, height = 800,
                 zmin = None, zmax = None, color = None, reverse=False,
                 dataV = 'z', subsample = 1):
        """
        Use Plotly library to visualise a dataset over a surface in 3D.

        Parameters
        ----------

        variable: width
            Figure width.

        variable: height
            Figure height.

        variable: zmin
            Minimal Z-axis value.

        variable: zmax
            Maximal Z-axis value.

        variable: color
            Color scale.

        variable: reverse
            Reverse color scale.

        variable: dataV
            Dataset to plot choices are 'z' for elevation, 'd' for 
            discharge (log-scale) and 'c' for cumulative erosion/
            deposition changes.

        variable: subsample
            Subsampling data everythin nth value.
        """

        if color == None:
            color = 'YIGnBu'

        if zmin == None:
            zmin = vData.min()

        if zmax == None:
            zmax = vData.max()

            
        if dataV == 'z':
            vData = self.z
            title='Model elevation at timestep:%d'%self.timestep
        elif dataV == 'c':
            vData = self.cumchange
            title='Model cumulative elevation change at timestep:%d'%self.timestep
        elif dataV == 'd':
            vData = self.logdischarge
            title='Model discharge (log-scale) at timestep:%d'%self.timestep
        else:
            raise RuntimeError('Requested data to visualise is unknown.')
            
        data = Data([
                Surface(
                    x = self.x[::subsample,::subsample],
                    y = self.y[::subsample,::subsample],
                    z = vData[::subsample,::subsample],
                    colorscale = color,
                    reversescale=reverse
                )
            ])

        dy = self.bbox[3]-self.bbox[1]
        dx = self.bbox[2]-self.bbox[0]
        if dx>=dy:
            dr = 0.5 * (dx-dy)
            rangeX = [self.bbox[0],self.bbox[2]]
            rangeY = [self.bbox[1]-dr,self.bbox[3]+dr]
        else:
            dr = 0.5 * (dy-dx)
            rangeX = [self.bbox[0]-dr,self.bbox[2]+dr]
            rangeY = [self.bbox[1],self.bbox[3]]

        layout = Layout(
            title=title,
            autosize=True,
            width=width,
            height=height,
            scene=Scene(
                zaxis=ZAxis(range=[zmin, zmax], \
                            autorange=False,nticks=10, \
                            gridcolor='rgb(255, 255, 255)', \
                            gridwidth=2,zerolinecolor='rgb(255, 255, 255)', \
                            zerolinewidth=2),

                xaxis=XAxis(autorange=False, range=rangeX, \
                            nticks=10, gridcolor='rgb(255, 255, 255)', \
                            gridwidth=2,zerolinecolor='rgb(255, 255, 255)', \
                            zerolinewidth=2),

                yaxis=YAxis(autorange=False, range=rangeY, nticks=10, \
                            gridcolor='rgb(255, 255, 255)', \
                            gridwidth=2,zerolinecolor='rgb(255, 255, 255)', \
                            zerolinewidth=2),

                bgcolor="rgb(244, 244, 248)"
            )
        )

        fig = Figure(data=data, layout=layout)
        plotly.offline.iplot(fig)

        return