from pywps import Process
# from pywps import LiteralInput
from pywps import ComplexInput, LiteralInput, ComplexOutput
from pywps import Format, FORMATS
from pywps.app.Common import Metadata

from flyingpigeon.log import init_process_logger
from flyingpigeon.utils import rename_complexinputs
from flyingpigeon import eodata
from flyingpigeon.config import cache_path

from datetime import datetime as dt
from datetime import timedelta, time
from tempfile import mkstemp
import zipfile


from os.path import exists, join
from os import makedirs

from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt

import logging
LOGGER = logging.getLogger("PYWPS")


class EO_COP_indicesProcess(Process):
    def __init__(self):
        inputs = [
            LiteralInput("indices", "Earth Observation Product Indice",
                         abstract="Choose an indice based on Earth Observation Data",
                         default='NDVI',
                         data_type='string',
                         min_occurs=1,
                         max_occurs=1,
                         allowed_values=['NDVI','BAI']
                         ),

            LiteralInput('BBox', 'Bounding Box',
                         data_type='string',
                         abstract="Enter a bbox: min_lon, max_lon, min_lat, max_lat."
                                  " min_lon=Western longitude,"
                                  " max_lon=Eastern longitude,"
                                  " min_lat=Southern or northern latitude,"
                                  " max_lat=Northern or southern latitude."
                                  " For example: -80,50,20,70",
                         min_occurs=1,
                         max_occurs=1,
                         default='14,15,8,9',
                         ),

            LiteralInput('start', 'Start Date',
                         data_type='date',
                         abstract='First day of the period to be searched for EO data.'
                                  '(if not set, 30 days befor end of period will be selected',
                         default=(dt.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                         min_occurs=0,
                         max_occurs=1,
                         ),

            LiteralInput('end', 'End Date',
                         data_type='date',
                         abstract='Last day of the period to be searched for EO data.'
                                  '(if not set, current day is set.)',
                         default=dt.now().strftime('%Y-%m-%d'),
                         min_occurs=0,
                         max_occurs=1,
                         ),

            LiteralInput('cloud_cover', 'Cloud Cover',
                         data_type='integer',
                         abstract='Max tollerated percentage of cloud cover',
                         default="30",
                         allowed_values=[0, 10, 20, 30, 40, 50, 60, 70, 80, 100]
                         ),

            LiteralInput('username', 'User Name',
                         data_type='string',
                         abstract='Authentification user name for the COPERNICUS Sci-hub ',
                         # default='2013-12-31',
                         min_occurs=1,
                         max_occurs=1,
                         ),

            LiteralInput('password', 'Password',
                         data_type='string',
                         abstract='Authentification password for the COPERNICUS Sci-hub ',
                         min_occurs=1,
                         max_occurs=1,
                         ),
        ]

        outputs = [
            # ComplexOutput("output_txt", "Files search result",
            #               abstract="Files found according to the search querry",
            #               supported_formats=[Format('text/plain')],
            #               as_reference=True,
            #               ),

            ComplexOutput("output_plot", "NDVI example file",
                          abstract="Plots in RGB colors",
                          supported_formats=[Format('image/png')],
                          as_reference=True,
                          ),

            ComplexOutput("output_archive", "Tar archive",
                          abstract="Tar archive of the iamge files",
                          supported_formats=[Format("application/x-tar")],
                          as_reference=True,
                          ),

            ComplexOutput("output_log", "Logging information",
                          abstract="Collected logs during process run.",
                          supported_formats=[Format("text/plain")],
                          as_reference=True,
                          )
        ]

        super(EO_COP_indicesProcess, self).__init__(
            self._handler,
            identifier="EO_COPERNICUS_indices",
            title="EO indices",
            version="0.1",
            abstract="Derivateing indices like NDVI based on",
            metadata=[
                Metadata('Documentation', 'http://flyingpigeon.readthedocs.io/en/latest/'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True,
        )

    def _handler(self, request, response):
        response.update_status("start fetching resource", 10)

        init_process_logger('log.txt')
        response.outputs['output_log'].file = 'log.txt'

        # products = [inpt.data for inpt in request.inputs['indices']]

        indice = request.inputs['indices'][0].data

        bbox = []  # order xmin ymin xmax ymax
        bboxStr = request.inputs['BBox'][0].data
        bboxStr = bboxStr.split(',')
        bbox.append(float(bboxStr[0]))
        bbox.append(float(bboxStr[2]))
        bbox.append(float(bboxStr[1]))
        bbox.append(float(bboxStr[3]))

        if 'end' in request.inputs:
            end = request.inputs['end'][0].data
            end = dt.combine(end, time(23, 59, 59))
        else:
            end = dt.now()

        if 'start' in request.inputs:
            start = request.inputs['start'][0].data
            start = dt.combine(start, time(0, 0, 0))
        else:
            start = end - timedelta(days=30)

        if (start > end):
            start = dt.now() - timedelta(days=30)
            end = dt.now()
            LOGGER.exception("periode end befor periode start, period is set to the last 30 days from now")

        username = request.inputs['username'][0].data
        password = request.inputs['password'][0].data
        cloud_cover = request.inputs['cloud_cover'][0].data

        api = SentinelAPI(username, password)

        geom = {
          "type": "Polygon",
          "coordinates": [[[ bbox[0], bbox[1]],
                           [ bbox[2], bbox[1]],
                           [ bbox[2], bbox[3]],
                           [ bbox[0], bbox[3]],
                           [ bbox[0], bbox[1]]]]}

        footprint = geojson_to_wkt(geom)

        response.update_status("start searching tiles acording query", 15)

        products = api.query(footprint,
                             date=(start, end),
                             platformname='Sentinel-2',
                             cloudcoverpercentage=(0, cloud_cover),
                             # producttype='SLC',
                             # orbitdirection='ASCENDING',
                             )

        LOGGER.debug('%s products found' % len(products.keys()))
        DIR_cache = cache_path()
        DIR_EO = join(DIR_cache, 'scihub.copernicus')
        if not exists(DIR_EO):
            makedirs(DIR_EO)

        # api.download_all(products)
        # try:
            # with open(filepathes, 'w') as fp:
            #     fp.write('############################################\n')
            #     fp.write('###     Following files are fetched      ###\n')
            #     fp.write('############################################\n')
            #     fp.write('\n')

        resources = []

        for key in products.keys():
            try:
                filename = products[key]['filename']
                # form = products[key]['format']
                ID = str(products[key]['identifier'])
                file_zip = join(DIR_EO, '%s.zip' % (ID))
                DIR_tile =join(DIR_EO, '%s' % (filename))
                response.update_status("fetch file %s" % ID , 20)
                LOGGER.debug('path: %s' % DIR_tile)
                if exists(file_zip):
                    LOGGER.debug('file %s.zip already fetched' % ID)
                else:
                    try:
                        api.download(key, directory_path=DIR_EO)
                        response.update_status("***%s sucessfully fetched" % ID, 20)
                        LOGGER.debug('Tile %s fetched' % ID)
                        LOGGER.debug('Files %s fetched ' % ID)
                    except:
                        LOGGER.exception('failed to extract file %s' % filename)
                if exists(DIR_tile):
                     LOGGER.debug('file %s already unzipped' % filename)
                else:
                    try:
                        # zipfile = join(DIR_EO, '%szip' % (filename)).strip(form)
                        zip_ref = zipfile.ZipFile(file_zip, 'r')
                        zip_ref.extractall(DIR_EO)
                        zip_ref.close()
                        LOGGER.debug('Tile %s unzipped' % ID)
                    except:
                        LOGGER.exception('failed to extract %s ' % file_zip)
                resources.append(DIR_tile)
            except:
                LOGGER.exception('failed to fetch %s' % key)

        size = float(products[key]['size'].split(' ')[0])
        producttype = products[key]['producttype']
        beginposition = str(products[key]['beginposition'])

        imgs = []
        tiles = []
        for resource in resources:
            try:
                response.update_status("Calculating %s indices " % ( indice ), 40)
                if indice == 'NDVI':
                    LOGGER.debug('Calculate NDVI for %s', resource )
                    tile = eodata.get_ndvi(resource)
                    LOGGER.debug('resources BAI calculated')
                if indice == 'BAI':
                    LOGGER.debug('Calculate BAI for %s', resource )
                    tile = eodata.get_bai(resource)
                    LOGGER.debug('resources BAI calculated')
                tiles.append(tile)
            except:
                LOGGER.exception('failed to calculate indice for %s ' % resource)

        for tile in tiles:
            try:
                LOGGER.debug("Plot tile %s" % tile)
                img = eodata.plot_band(tile, file_extension='PNG', colorscheem=indice)
                imgs.append(img)
            except:
                LOGGER.exception("Failed de plot tile %s " % tile)

        from flyingpigeon.utils import archive
        tarf = archive(imgs)

        response.outputs['output_archive'].file = tarf

        i = next((i for i, x in enumerate(imgs) if x), None)
        if i is None:
            i = "dummy.png"
        response.outputs['output_plot'].file = imgs[i]

        # from flyingpigeon import visualisation as vs
        #
        # images = vs.concat_images(imgs, orientation='v')

        response.update_status("done", 100)
        return response
