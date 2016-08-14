import json
import logging

from google.appengine.ext import deferred

from github import Github
from model import CrashReport
from util import is_appengine_local, crash_uri, CrashReports

# constants
TOKEN_KEY = 'github_token'

DEBUG_OWNER = 'tikurahul'
DEBUG_REPO = 'sandbox'
DEBUG_CRASH_REPORTER_HOST = 'http://localhost:8080'

OWNER = 'tessel'
REPO = 't2-cli'
CRASH_REPORTER_HOST = 'http://crash-reporter.tessel.io'


class GithubOrchestrator(object):
    """
    Orchestrates all communication with GitHub via a task queue.
    """
    __QUEUE__ = 'github-queue'
    __NOTIFY_FREQUENCY__ = 1

    @classmethod
    def manage_github_issue(cls, crash_report):
        """
        Manages the GitHub issue.
        """
        if crash_report is not None:
            count = CrashReport.get_count(crash_report.name)
            if count == 1:
                # new crash
                deferred.defer(
                    GithubOrchestrator.create_issue_job, crash_report.fingerprint, _queue=GithubOrchestrator.__QUEUE__)
                logging.info(
                    'Enqueued job for new issue on GitHub for fingerprint %s' % crash_report.fingerprint)
            elif count > 0 and count % GithubOrchestrator.__NOTIFY_FREQUENCY__ == 0:
                # add comments for an existing crash
                deferred.defer(
                    GithubOrchestrator.add_comment_job, crash_report.fingerprint, _queue=GithubOrchestrator.__QUEUE__)
                logging.info(
                    'Enqueued job for adding comments on GitHub for fingerprint %s' % crash_report.fingerprint)
            else:
                logging.debug('No pending tasks.')

    @classmethod
    def create_issue_job(cls, fingerprint):
        """
        Handles the create issue job.
        """
        try:
            github_client = GithubClient()
            crash_report = CrashReport.get_crash(fingerprint)
            if crash_report is not None:
                # create the github issue
                issue = github_client.create_issue(crash_report)
                logging.info('Created GitHub Issue No(%s) for crash (%s)' % (issue.number, crash_report.fingerprint))
                # update the crash report with the issue id
                updated_report = CrashReports.update_crash_report(crash_report.fingerprint, {
                    # convert to unicode string
                    'issue': str(issue.number)
                })
                logging.info('Updating crash report with fingerprint (%s) complete.' % updated_report.fingerprint)
        except Exception, e:
            logging.error('Error creating issue for fingerprint (%s) [%s]' % (fingerprint, e.message))

    @classmethod
    def add_comment_job(cls, fingerprint):
        try:
            github_client = GithubClient()
            crash_report = CrashReport.get_crash(fingerprint)
            if crash_report is not None:
                github_client.create_comment(crash_report)
        except Exception, e:
            logging.error('Error creating comment for fingerprint (%s) [%s]' % (fingerprint, e.message))


class GithubClient(object):
    """
    A set of github utilities.
    """
    @classmethod
    def issue_title(cls, fingerprint):
        return 'Crash report %s' % fingerprint

    def issue_body(self, fingerprint):
        crash_report_uri = '%s%s' % (self.reporter_host, crash_uri(fingerprint))
        body = 'Full report is at [%s](%s)' % (fingerprint, crash_report_uri)
        return body

    @classmethod
    def issue_comment(cls, count):
        new_comment = 'More crashes incoming. Current crash count is at %s.' % count
        return new_comment

    def __init__(self):
        with open('client_secrets.json', 'r') as contents:
            secrets = json.loads(contents.read())
            github_token = secrets.get(TOKEN_KEY)
            if is_appengine_local():
                self.reporter_host = DEBUG_CRASH_REPORTER_HOST
                self.repo_name = '%s/%s' % (DEBUG_OWNER, DEBUG_REPO)
            else:
                self.reporter_host = CRASH_REPORTER_HOST
                self.repo_name = '%s/%s' % (OWNER, REPO)
            self.github_client = Github(login_or_token=github_token)

    """
    Submits a GitHub issue for a given fingerprint.
    """
    def create_issue(self, crash_report):
        fingerprint = crash_report.fingerprint
        # get repository
        repository = self.github_client.get_repo(self.repo_name)

        # create issue
        issue = repository.create_issue(
            title=GithubClient.issue_title(fingerprint),
            body=self.issue_body(fingerprint),
            labels=[str(fingerprint)])

        return issue

    """
    Updates a crash report with the comment.
    """
    def create_comment(self, crash_report):
        count = CrashReport.get_count(crash_report.name)
        issue_number = int(float(crash_report.issue))
        comment_body = self.issue_comment(count)

        # get repo
        repository = self.github_client.get_repo(self.repo_name)
        issue = repository.get_issue(issue_number)
        # create comment
        comment = issue.create_comment(comment_body)
        return {
            'issue': issue,
            'comment': comment
        }
