from google.appengine.ext import db
from google.appengine.ext.db import Key

from model import CrashReport
from search_model import Search
from simhash import sim_hash


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
    def update_report_state(cls, fingerprint, new_state):
        # state can be one of 'unresolved'|'pending'|'submitted'|'resolved'
        return CrashReports.update_crash_report(fingerprint, {
           'state': new_state
        })

    @classmethod
    def update_report_issue(cls, fingerprint, issue):
        return CrashReports.update_crash_report(fingerprint, {
            'issue': issue
        })

    @classmethod
    def update_crash_report(cls, fingerprint, delta_state):
        name = CrashReport.key_name(fingerprint)
        to_update = list()
        q = CrashReport.all()
        q.filter('name = ', name)
        for crash_report in q.run():
            # update state
            # only allow * mutable * properties of crash reports to be updated

            # having to manually update properties on the entity this was, as expando entities
            # do not have a way to update an entity via a property name :(
            if 'labels' in delta_state:
                crash_report.labels = delta_state.get('labels')
            if 'date_time' in delta_state:
                crash_report.date_time = delta_state.get('date_time')
            if 'count' in delta_state:
                crash_report.count = delta_state.get('count')
            if 'issue' in delta_state:
                crash_report.issue = delta_state.get('issue')
            if 'state' in delta_state:
                crash_report.state = delta_state.get('state')

            to_update.append(crash_report)

        # update datastore and search indexes
        db.put(to_update)
        Search.add_crash_reports(to_update)
        # clear memcache
        CrashReport.clear_cache(name)
        # return crash report
        return CrashReport.get_crash(fingerprint)

    @classmethod
    def trending(cls, start=None, limit=20):
        q = CrashReport.all()
        # only search for crashes that are not resolved
        q.filter('state IN ', ['unresolved', 'pending', 'submitted'])

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

        trending = sorted(trending, key=lambda report: report['count'], reverse=True)
        return {
            'trending': trending,
            'has_more': has_more
        }
