# calculation of number of segetal flora species

from os import environ, mkdir
from os.path import join
import tempfile
# import shutil

from cdo import *
cdo = Cdo()

# birdhouse WPS must be running (make start # in the toplevel of one of the birds)
# export PYTHONPATH=$HOME/birdhouse/flyingpigeon/flyingpigeon/
from flyingpigeon import segetalflora as sg
from flyingpigeon import clipping , timeseries
from flyingpigeon.utils import drs_filename , sort_by_time


from malleefowl import wpslogging as logging
     
climate_type = ['1','2','3','4','5','6','7','all']
culture_type = ['fallow', 'extensiv', 'intensiv', 'all']
HOME = environ['HOME']
nc1  = join(HOME , '.conda/envs/birdhouse/var/cache/pywps/tas_EUR-11_MOHC-HadGEM2-ES_historical_r1i1p1_CLMcom-CCLM4-8-17_v1_sem_200101-200510.nc')
#nc2  = join(HOME , '.conda/envs/birdhouse/var/cache/pywps/tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r1i1p1_CLMcom-CCLM4-8-17_v1_sem_199101-200010.nc')

countries = ['AUT','BEL','BGR','CYP','CZE','DEU','DNK','ESP','EST','FIN','FRA','GBR','GRC','HUN','HRV','IRL','ITA','LVA','LTU','LUX','MLT','NLD','POL','PRT','ROU','SVK','SVN','SWE','NOR','CHE','ISL','MKD','MNE','SRB','MDA','UKR','BIH','ALB','BLR','KOS']

ncs = [nc1]

prefix = drs_filename(nc).strip('.nc')
calc = [{'func':'mean','name':'tas'}]
calc_grouping = ['year']

# create temp dir

dir_tas = (os.path.curdir+'/dir_tas/')
dir_polygons = (os.path.curdir+'/dir_polygons/')
dir_timeseries = (os.path.curdir+'/dir_timeseries/')

mkdir(dir_tas)
mkdir(dir_polygons)
mkdir(dir_timeseries)
ncs_sort = sort_by_time(ncs)
# prepare input files, Europe clipping and concatination 
prefix = 'tas_EUR-11_MOHC-HadGEM2-ES_historical_r1i1p1_CLMcom-CCLM4-8-17_v1_sem_'
europe_yearsum = clipping.clip_continent(urls=ncs, calc=calc,calc_grouping= calc_grouping,
                                         prefix=prefix , continent='Europe', dir_output=dir_tas)
fldmean = timeseries.fldmean(europe_yearsum, dir_output = dir_timeseries)

for cult in culture_type: 
  for clim in climate_type:
    eq = sg.get_equation(culture_type= cult , climate_type=clim)
    sf_prefix = prefix.replace('tas_', 'sf_%s_%s_' %(cult, clim))
    output = join(dir_polygons, sf_prefix+'.nc' ) 
    cdo.expr(eq , input=europe_yearsum, output=output)
    fldmean = timeseries.fldmean(output, dir_output = dir_timeseries)
    for country in countries:
      try: 
        EUR_seglo = clipping.clip_counties_EUR(urls=output, prefix= sf_prefix.replace('_EUR', '_%s'% (country)), dir_output = dir_polygons, country=country)
        fldmean = timeseries.fldmean(EUR_seglo, dir_output = dir_timeseries)
      except Exception as e:
        msg = 'ocgis calculations failed '
        #logger.exception(msg)
        #raise CalculationException(msg, e)
        print msg
