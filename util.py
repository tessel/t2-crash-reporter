from model import CrashReport
from simhash import sim_hash


class CrashReportException(Exception):
    """
    Defines the exception type
    """


class CrashReports(object):
    """
    Encapsulates all the logic for creating/ querying crash reports.
    """
    @classmethod
    def add_crash_report(cls, report):
        fingerprint = sim_hash(report)
        crash_report = CrashReport.add_or_remove(fingerprint, report)
        return crash_report
