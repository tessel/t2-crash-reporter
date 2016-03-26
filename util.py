from model import CrashReport
from simhash import sim_hash

from google.appengine.ext.db import Key


def crash_uri(fingerprint):
    return '/crashes?fingerprint=%s' % fingerprint


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
