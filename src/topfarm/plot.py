# TOPFARM - A Multi-fidelity Wind Farm Layout Optimization Tool
# Copyright (C) 2015  DTU Wind Energy, the TOPFARM development Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = 'Pierre-Elouan Rethore'
__email__ = "pire@dtu.dk"
__version__ = '0.1.0'
__copyright__ = "Copyright 2015, DTU Wind Energy, TOPFARM Development Team"
__license__ = "AGPL v3"
__status__ = "Alpha"

from openmdao.lib.datatypes.api import VarTree, Float, Slot, Array, List, Int, Str, Dict, Enum
from openmdao.main.api import Component
import seaborn as sns
import numpy as np
from path import path as pa
from tlib import *
import matplotlib as plt

from IPython.display import display, clear_output

class OffshorePlot(Component):
    wt_positions = Array([], unit='m', iotype='in', desc='Array of wind turbines attached to particular positions')
    baseline = Array([], unit='m', iotype='in', desc='Array of wind turbines attached to particular positions')
    borders = Array(iotype='in', desc='The polygon defining the borders ndarray([n_bor,2])', unit='m')
    depth = Array(iotype='in', desc='An array of depth ndarray([n_d, 2])', unit='m')
    foundation_length = Float(iotype='in', desc='The total foundation length of the wind farm')
    foundations = Array(iotype='in', desc='The foundation length ofeach wind turbine')
    wt_dist = Array(iotype='in', desc="""The distance between each turbines ndarray([n_wt, n_wt]).""", unit='m')
    spiral_param = Float(5.0, iotype='in', desc='spiral parameter')
    png_name = Str('wind_farm', iotype='in', desc='The base of the png name used to save the fig')
    result_file = Str('wind_farm', iotype='in', desc='The base result name used to save the fig')
    net_aep = Float(iotype='in', desc='')
    distribution = Str('spiral', iotype='in', desc='The type of distribution to plot')
    elnet_layout = Dict(iotype='in')
    elnet_length = Float(iotype='in')
    inc = 0
    fs = 15 #Font size
    
    def __init__(self):
        super(OffshorePlot, self).__init__()
        self.fig = plt.figure(num=None, figsize=(7, 4), dpi=200, facecolor='w', edgecolor='k')
        self.shape_plot = self.fig.add_subplot(121)
        self.objf_plot = self.fig.add_subplot(122)


        #sns.set(style="darkgrid")
        #self.pal = sns.dark_palette("skyblue", as_cmap=True)
        plt.rc('lines', linewidth=1)        
        plt.ion()
        self.force_execute = True 
        if not pa('fig').exists():
            pa('fig').mkdir()

    def execute(self):
        plt.ion()     
        dist_min = np.array([self.wt_dist[i] for i in range(self.wt_dist.shape[0]) ]).min()
        dist_mean = np.array([self.wt_dist[i] for i in range(self.wt_dist.shape[0]) ]).mean()
        if self.inc==0:
            try:
                pa(self.result_file+'.results').remove()
            except:
                pass
            self.iterations = [self.inc]
            self.targvalue = [[self.foundation_length, self.elnet_length, dist_mean, dist_min, self.net_aep]]
            self.pre_plot()
        else:
            self.iterations.append(self.inc)
            self.targvalue.append([self.foundation_length, self.elnet_length, dist_mean, dist_min, self.net_aep])
            #print self.iterations,self.targvalue
        #if self.inc % (2*self.wt_positions.shape[0]) == 0:
        #self.refresh()
        #plt.show()
        self.save_plot('fig/'+self.png_name+'layout%d.png'%(self.inc))
        self.inc += 1

    def pre_plot(self):
        
        plt.ion()
        #plt.show()
        ### Plot the water depth
        N = 100
        self.X, self.Y = plt.meshgrid(plt.linspace(self.depth[:,0].min(), self.depth[:,0].max(), N), 
                                  plt.linspace(self.depth[:,1].min(), self.depth[:,1].max(), N))
        self.Z = plt.griddata(self.depth[:,0],self.depth[:,1],self.depth[:,2],self.X,self.Y, interp='linear')

        Zin = points_in_poly(self.X,self.Y, self.borders)
        self.Z.mask = Zin.__neg__()
        self.targname = ['Foundation length', 'El net length', 'Mean WT Dist', 'Min WT Dist', 'AEP']
        #Z.mask = False
        #Z.data[Zin.__neg__()] = -20.0

        display(plt.gcf())
   
    # def refresh(self):
        self.shape_plot.clear()
        self.shape_plot.contourf(self.X, self.Y, self.Z, 10, vmax=self.depth[:,2].max())       #, cmap=self.pal
        self.shape_plot.set_aspect('equal')
        self.shape_plot.autoscale(tight=True)

        Plot = lambda b, *args, **kwargs: self.shape_plot.plot(b[:,0], b[:,1],*args, **kwargs)
        if self.distribution == 'spiral':
            spiral = lambda t_, a_, x_: [a_*t_**(1./x_) * np.cos(t_), a_*t_**(1./x_) * np.sin(t_)]
            spirals = lambda ts_, a_, x_: np.array([spiral(t_, a_, x_) for t_ in ts_])
            for P in self.baseline:
                Plot(P + spirals(plt.linspace(0.,10*np.pi,1000), self.spiral_param, 1.), 'w-', linewidth=0.1)


        self.shape_plot.plot(self.borders[:,0], self.borders[:,1],'k-')
        self.posi = self.shape_plot.plot(self.wt_positions[:,0], self.wt_positions[:,1],'ro')
        self.plotel = self.shape_plot.plot(np.array([self.baseline[[i,j],0] for i, j in self.elnet_layout.keys()]).T, 
                                           np.array([self.baseline[[i,j],1]  for i, j in self.elnet_layout.keys()]).T, 'y--', linewidth=1)
        #print self.plotel

        self.objf_plot.clear()
        targarr = np.array(self.targvalue)
        self.posb = []
        for i in range(targarr.shape[1]):
            self.posb.append(self.objf_plot.plot(self.iterations, self.targvalue[0][i],'.', label=self.targname[i]))
        print 'posb', self.posb
        self.objf_plot.legend(loc=3)

        plt.title('Foundation = %8.2f'%(self.foundation_length))
        plt.draw()

    def save_plot(self, filename):
        plt.ion()
        targarr = np.array(self.targvalue)
        self.posi[0].set_xdata(self.wt_positions[:,0])
        self.posi[0].set_ydata(self.wt_positions[:,1])
        while len(self.plotel)>0:
            self.plotel.pop(0).remove()
        self.plotel = self.shape_plot.plot(np.array([self.wt_positions[[i,j],0] for i, j in self.elnet_layout.keys()]).T, 
                                   np.array([self.wt_positions[[i,j],1]  for i, j in self.elnet_layout.keys()]).T, 'y-', linewidth=1)
        for i in range(len(self.posb)):
            self.posb[i][0].set_xdata(self.iterations)
            self.posb[i][0].set_ydata(targarr[:,i])
        self.objf_plot.set_xlim([0, self.iterations[-1]])
        self.objf_plot.set_ylim([0.5, 1.2])
        plt.title('Foundation = %8.2f'%(self.foundation_length))
        plt.draw()
        #print self.iterations[-1] , ': ' + ', '.join(['%s=%6.2f'%(self.targname[i], targarr[-1,i]) for i in range(len(self.targname))])
        with open(self.result_file+'.results','a') as f:
            f.write( '%d:'%(self.inc) + ', '.join(['%s=%6.2f'%(self.targname[i], targarr[-1,i]) for i in range(len(self.targname))]) + 
                str(self.wt_positions) + '\n'
                )
        #plt.show()
        plt.savefig(filename)
        display(plt.gcf())
        #plt.show()
        clear_output(wait=True)
        