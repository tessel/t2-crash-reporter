import logging

from google.appengine.api import search

from model import CrashReport, to_milliseconds

__INDEX__ = 'CrashReportsIndex'


class Search(object):
    @classmethod
    def delete_all_in_index(cls):
        index = search.Index(name=__INDEX__)
        while True:
            document_ids = [document.doc_id
                            for document in index.get_range(ids_only=True)]
            if not document_ids:
                break
            index.delete(document_ids)

    @classmethod
    def crash_report_to_document(cls, crash_report):
        if not crash_report:
            return None

        fields = [
            search.AtomField(name='key', value=unicode(crash_report.key())),
            search.AtomField(name='fingerprint', value=crash_report.fingerprint),
            search.TextField(name='crash', value=crash_report.crash),
            search.DateField(name='time', value=crash_report.date_time),
            search.NumberField(name='count', value=CrashReport.get_count(crash_report.name)),
            search.AtomField(name='state', value=crash_report.state),
            search.AtomField(name='issue', value=crash_report.issue),
        ]
        labels = [search.TextField(name='labels', value=label)
                  for label in crash_report.labels]
        fields.extend(labels)
        document = search.Document(doc_id=unicode(crash_report.key()), fields=fields)
        return document

    @classmethod
    def add_to_index(cls, crash_report):
        if crash_report:
            document = Search.crash_report_to_document(crash_report)
            try:
                index = search.Index(name=__INDEX__)
                index.put(document)
            except search.Error, e:
                logging.exception('Unable to add document to index', e)

    @classmethod
    def add_crash_reports(cls, crash_reports):
        if crash_reports:
            documents = [Search.crash_report_to_document(crash_report) for crash_report in crash_reports]
            try:
                index = search.Index(name=__INDEX__)
                index.put(documents)
            except search.Error, e:
                logging.exception('Unable to add documents to index', e)

    @classmethod
    def search(cls, query, cursor=None, limit=25):
        # documentation for the query string format is at
        # https://cloud.google.com/appengine/docs/python/search/query_strings

        if not cursor:
            cursor = search.Cursor()
        else:
            cursor = search.Cursor(web_safe_string=cursor)

        if query:
            index = search.Index(name=__INDEX__)

            # default sort options
            sort_time = search.SortExpression(
                expression='time',
                direction=search.SortExpression.DESCENDING,
                default_value=0)
            sort_options = search.SortOptions(expressions=[sort_time])

            # query options
            query_options = search.QueryOptions(
                cursor=cursor,
                limit=limit,
                sort_options=sort_options)
            query = search.Query(query_string=query, options=query_options)
            # search
            results = index.search(query)
            fingerprints = set()
            models = list()
            for document in results:
                fingerprint = Search._find_first(document, 'fingerprint')
                model = {
                    'key': Search._find_first(document, 'key'),
                    'crash': Search._find_first(document, 'crash'),
                    'labels': Search._find_fields(document, 'labels'),
                    'fingerprint': fingerprint,
                    'time': to_milliseconds(Search._find_first(document, 'time')),  # in millis
                    'count': CrashReport.get_count(CrashReport.key_name(Search._find_first(document, 'fingerprint'))),
                    'issue': Search._find_first(document, 'issue')
                }
                # de-dupe fingerprints
                if fingerprint not in fingerprints:
                    fingerprints.add(fingerprint)
                    models.append(model)

            cursor = None
            if results.cursor:
                cursor = results.cursor.web_safe_string

            return {
                'cursor': cursor,
                'results': models
            }
        else:
            return None

    @classmethod
    def _find_fields(cls, document, field_name):
        fields = document.fields
        return [f.value for f in fields if f.name == field_name]

    @classmethod
    def _find_first(cls, document, field_name):
        results = Search._find_fields(document, field_name)
        if results and len(results) > 0:
            return results[0]
        else:
            return None
