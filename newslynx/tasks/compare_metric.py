from gevent.pool import Pool 

from newslynx.util import gen_uuid
from newslynx.core import db
from newslynx import settings
from .util import ResultIter


class ContentComparison(object):
    table = "content_metric_summary"
    id_col = "content_item_id"
    metrics_attr = "content_metric_comparisons"

    def __init__(self, org, ids, **kw):
        self.org = org
        if not isinstance(ids, list):
            ids = [ids]
        self.ids = ids
        self.bulk_size = kw.get('bulk_size', 1000)
        self.pool = Pool(kw.get('pool_size', 20))
        self.rm_null = kw.get('rm_null', False)
        self.percentiles = kw.get(
            'percentiles', settings.COMPARISON_PERCENTILES)
        self.metrics = getattr(org, self.metrics_attr)

    @property
    def ids_array(self):
        return "ARRAY[{}]".format(",".join([str(i) for i in self.ids]))

    def select_metric(self, metric):
        return "(metrics ->> '{name}')::text::numeric as metric".format(**metric)

    def null_metric(self, metric):
        return "AND (metrics ->> '{name}')::text::numeric IS NOT NULL".format(**metric)

    def init_query(self, metric):
        select = self.select_metric(metric)
        null_metric = self.null_metric(metric)
        if not self.rm_null:
            null_metric = ""
        return \
            """SELECT {select}
               FROM {table}
               WHERE {id_col} in (select unnest({ids_array}))
               {null_metric}
               """\
            .format(select=select, table=self.table,
                    id_col=self.id_col, ids_array=self.ids_array,
                    null_metric=null_metric)

    def metric_summary_query(self, metric):
        return \
            """ SELECT array_agg(metric) as metric_arr,
                       ROUND(avg(metric), 2) as mean,
                       ROUND(min(metric), 2) as min,
                       ROUND(median(metric), 2) as median,
                       ROUND(max(metric), 2) as max
                       FROM ({}) AS "{}"
            """.format(self.init_query(metric), gen_uuid())

    def select_percentile(self, per):
        per_col = "per_" + str(per).replace('.', '_')
        if per_col.endswith('_0'):
            per_col = per_col[:-2]
        return "percentile(metric_arr, {}) as {}".format(per, per_col)

    @property
    def select_percentiles(self):
        ss = []
        for per in self.percentiles:
            ss.append(self.select_percentile(per))
        return ",\n".join(ss)

    def metric_query(self, metric):
        kw = {
            'name': metric.get('name'),
            'percentiles': self.select_percentiles,
            'summary_query': self.metric_summary_query(metric),
            'alias': gen_uuid()
        }
        return \
            """SELECT '{name}' as metric,
                      mean, median, min, max,
                      {percentiles}
               FROM (\n{summary_query}\n) AS "{alias}"
            """.format(**kw)

    @property
    def queries(self):
        """
        Chunk queries.
        """
        queries = []
        for metric in self.metrics.values():
            queries.append(self.metric_query(metric))
            if len(queries)  % self.bulk_size == 0:
                yield "\nUNION ALL\n".join(queries)
        yield "\nUNION ALL\n".join(queries)

    def _execute_one(self, query):
        """
        Execute the chunked queries stream the results.
        """
        res = db.session.execute(query)
        if res:
            for r in ResultIter(res):
                if r:
                    yield r
    
    def execute(self):
        """
        pooled execution.
        """
        for query in self.queries:
            results = ResultIter(db.session.execute(query))
            for r in results:
                yield r
