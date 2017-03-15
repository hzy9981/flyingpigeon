from flyingpigeon.indices import indices, indices_description
from flyingpigeon.subset import countries, countries_longname
from flyingpigeon.utils import GROUPING

from flyingpigeon.log import init_process_logger
from flyingpigeon.utils import rename_complexinputs

from pywps import Process
from pywps import LiteralInput
from pywps import ComplexInput, ComplexOutput
from pywps import Format
from pywps.app.Common import Metadata

import logging
LOGGER = LOGGER.getLogger("PYWPS")


class IndicespercentileProcess(Process):
    def __init__(self):
        inputs = [
            ComplexInput('resource', 'Resource',
                         abstract="NetCDF Files or archive (tar/zip) containing netCDF files",
                         min_occurs=1,
                         max_occurs=1000,
                         #  maxmegabites=5000,
                         supported_formats=[
                             Format('application/x-netcdf'),
                             Format('application/x-tar'),
                             Format('application/zip'),
                         ]),

            LiteralInput("indices", "Index",
                         abstract='Select an index',
                         default='TG',
                         data_type='string',
                         min_occurs=1,
                         max_occurs=1,  # len(indices()),
                         allowed_values=['TG', 'TN', 'TX'],  # indices()
                         ),

            LiteralInput("percentile", "Percentile",
                         abstract='Select an percentile',
                         default='90',
                         data_type='integer',
                         min_occurs=1,
                         max_occurs=1,  # len(indices()),
                         allowed_values=range(1, 100),  # indices()
                         ),

            LiteralInput("refperiod", "Reference Period",
                         abstract="Time refperiod to retrieve the percentile level",
                         default="19700101-20101231",
                         data_type='string',
                         min_occurs=0,
                         max_occurs=1,
                         ),

            # self.refperiod = self.addLiteralInput(
            #     identifier="refperiod",
            #     title="Reference refperiod",
            #     abstract="Reference refperiod for climate condition (all = entire timeserie)",
            #     default=None,
            #     type=type(''),
            #     minOccurs=0,
            #     maxOccurs=1,
            #     allowedValues=['all','1951-1980', '1961-1990', '1971-2000','1981-2010']
            #     )

            LiteralInput("groupings", "Grouping",
                         abstract="Select an time grouping (time aggregation)",
                         default='yr',
                         data_type='string',
                         min_occurs=1,
                         max_occurs=len(GROUPING),
                         allowed_values=GROUPING
                         ),

            LiteralInput("polygons", "Country subset",
                         abstract=countries_longname(),
                         default='DEU',
                         data_type='string',
                         min_occurs=0,
                         max_occurs=len(countries()),
                         allowed_values=countries()
                         ),

            LiteralInput("mosaic", "Mosaic",
                         abstract="If Mosaic is checked, selected polygons be clipped as a mosaic for each input file",
                         default='0',
                         data_type='boolean',
                         min_occurs=0,
                         max_occurs=1,
                         ),
        ]

        outputs = [
            ComplexOutput("output", "Index",
                          abstract="Calculated index as NetCDF file",
                          metadata=[],
                          supported_formats=[Format("application/x-tar")],
                          as_reference=True
                          ),

            ComplexOutput('output_log', 'Logging information',
                          abstract="Collected logs during process run.",
                          as_reference=True,
                          supported_formats=[Format("text/plain")])
        ]

        super(IndicespercentileProcess, self).__init__(
            self.__handler,
            identifier="indices_percentile",
            title="Climate indices -- Percentile",
            version="0.10",
            abstract="Climate indices based on one single input variable\
             and the percentile of a reference period.",
            metadata=[
                {'title': 'Doc',
                 'href': 'http://flyingpigeon.readthedocs.io/en/latest/descriptions/\
                 index.html#climate-indices'},
                {"title": "ICCLIM",
                 "href": "http://icclim.readthedocs.io/en/latest/"},
                {"title": "Percentile-based indices", "href": "http://flyingpigeon.readthedocs.io/en/\
                latest/descriptions/indices.html#percentile-based-indices"},
                ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True
            )

    def _handler(self, request, response):
        from flyingpigeon.indices import calc_indice_percentile
        from flyingpigeon.utils import archive, archiveextract

        init_process_logger('log.txt')
        response.outputs['output_log'].file = 'log.txt'

        ncs == archiveextract(
            resource=rename_complexinputs(request.inputs['resource']))
        indices = request.inputs['indices']
        polygons = request.inputs['polygons']
        percentile = request.inputs['percentile']
        groupings = request.inputs['groupings']
        mosaic = request.inputs['mosaic']
        refperiod = request.inputs['refperiod']

        response.update_status('starting: indices=%s, refperiod=%s, groupings=%s, num_files=%s'
                               % (indices, refperiod, groupings, len(ncs)), 2)

        results = calc_indice_percentile(
            resources=ncs,
            indices=indices,
            percentile=percentile,
            mosaic=mosaic,
            polygons=polygons,
            refperiod=refperiod,
            groupings=groupings,
            dir_output=path.curdir,
            )

        if not results:
            raise Exception("failed to produce results")
        response.update_status('num results %s' % len(results), 90)

        try:
            tarf = archive(results)
        except:
            msg = "Tar file preparation failed."
            LOGGER.exception(msg)

        response.outputs['output'].file = tarf
        response.update_status('done: indice=%s, num_files=%s' % (indices, len(ncs)), 100)
