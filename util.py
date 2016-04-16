from model import CrashReport
from simhash import sim_hash
from search_model import Search

from google.appengine.ext.db import Key


def crash_uri(fingerprint):
    return '/crashes?fingerprint=%s' % fingerprint


def snippetize(trace, snippet_length=3):
    if not trace:
        return None
    else:
        lines = trace.splitlines(True)
        content = [line for line in lines if len(line.strip()) > 0][:snippet_length]
        return '%s...' % ''.join(content)


class CrashReportException(Exception):
    """
    Defines the exception type
    """


class CrashReports(object):
    """
    Encapsulates all the logic for creating/ querying crash reports.
    """
    @classmethod
    def add_crash_report(cls, report, labels=None):
        fingerprint = sim_hash(report)
        crash_report = CrashReport.add_or_remove(fingerprint, report, labels=labels)
        # add crash report to index
        Search.add_to_index(crash_report)
        return crash_report

    @classmethod
    def trending(cls, start=None, limit=20):
        q = CrashReport.all()
        if start:
            q.filter('__key__ >', Key(start))
        q.order('__key__')
        q.order('name')
        q.order('-count')

        uniques = set()
        trending = list()
        has_more = False
        for crash_report in q.run():
            if len(uniques) > limit:
                has_more = True
                break
            else:
                if crash_report.name not in uniques:
                    uniques.add(crash_report.name)
                    crash_report = CrashReport.get_crash(crash_report.fingerprint)
                    trending.append(CrashReport.to_json(crash_report))
        return {
            'trending': trending,
            'has_more': has_more
        }
