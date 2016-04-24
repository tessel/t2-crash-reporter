import StringIO
import csv

import webapp2
from webapp2 import uri_for

from common import common_request
from model import CrashReport, Link
from util import CrashReports


class RequestHandlerUtils(object):
    @classmethod
    def add_brand(cls, handler):
        brand = Link('Tessel Error Reporter', uri_for('home'))
        handler.add_parameter('brand', brand)

    @classmethod
    def add_nav_links(cls, handler):
        nav_links = list()
        nav_links.append(Link('Who we are', 'https://tessel.io/'))
        nav_links.append(Link('About', 'https://tessel.io/about'))
        handler.add_parameter('nav_links', nav_links)


class RootHandler(webapp2.RequestHandler):
    @common_request
    def get(self):
        self.add_parameter('title', 'Tessel Error Reporter')
        self.add_breadcrumb('Tessel Error Reporter', uri_for('home'))
        RequestHandlerUtils.add_brand(self)
        RequestHandlerUtils.add_nav_links(self)
        directory_links = list()
        directory_links.append(Link('Trending Crashes', uri_for('trending_crashes')))
        directory_links.append(Link('Submit Crash', uri_for('submit_crash')))
        directory_links.append(Link('View Crash', uri_for('view_crash')))
        directory_links.append(Link('Update Crash Report', uri_for('update_crash_state')))
        self.add_parameter('directory_links', directory_links)
        self.render('index.html')


class SubmitCrashHandler(webapp2.RequestHandler):
    def common(self, handler):
        handler.add_parameter('title', 'Submit Crash Report')
        handler.add_breadcrumb('Home', uri_for('home'))
        handler.add_breadcrumb('Submit Crash', uri_for('submit_crash'))
        RequestHandlerUtils.add_brand(handler)
        RequestHandlerUtils.add_nav_links(handler)

    @common_request
    def get(self):
        self.request_handler.common(self)
        self.render('submit-crash.html')

    @classmethod
    def csv_to_list(cls, input_as_csv):
        if not input_as_csv:
            return None
        else:
            input_as_io = StringIO.StringIO(input_as_csv)
            reader = csv.reader(input_as_io, delimiter=',')
            tokens = list()
            for token in reader:
                tokens.extend(token)
            return tokens

    @common_request
    def post(self):
        self.request_handler.common(self)
        if self.empty_query_string('crash', 'labels'):
            self.request_handler.redirect(uri_for('submit_crash'))
        else:
            crash = self.get_parameter('crash')
            labels = SubmitCrashHandler.csv_to_list(self.get_parameter('labels'))
            # strip spaces around the crash report
            crash_report = CrashReports.add_crash_report(crash.strip(), labels)
            message = 'Added Crash Report with fingerprint, count) => (%s, %s)' % \
                      (crash_report.fingerprint, CrashReport.get_count(crash_report.name))
            self.add_message(message)
            self.add_to_json('crash_report', CrashReport.to_json(crash_report))
            self.render('submit-crash.html')


class ViewCrashHandler(webapp2.RequestHandler):
    def common(self, handler):
        handler.add_parameter('title', 'Show Crash')
        handler.add_breadcrumb('Home', uri_for('home'))
        handler.add_breadcrumb('View Crash', uri_for('view_crash'))
        RequestHandlerUtils.add_brand(handler)
        RequestHandlerUtils.add_nav_links(handler)

    @common_request
    def get(self):
        self.request_handler.common(self)
        if not self.empty_query_string('fingerprint'):
            fingerprint = self.get_parameter('fingerprint')
            crash_report = CrashReport.get_crash(fingerprint)
            if crash_report:
                crash_report_item = CrashReport.to_json(crash_report)
                self.add_parameter('crash_report', crash_report_item)
                self.add_to_json('crash_report', crash_report_item)
        self.render('show-crash.html')


class UpdateCrashStateHandler(webapp2.RequestHandler):
    def common(self, handler):
        handler.add_parameter('title', 'Update Crash State')
        handler.add_breadcrumb('Home', uri_for('home'))
        handler.add_breadcrumb('Update Crash State', uri_for('update_crash_state'))
        RequestHandlerUtils.add_brand(handler)
        RequestHandlerUtils.add_nav_links(handler)

    @common_request
    def get(self):
        self.request_handler.common(self)
        self.render('update-crash-state.html')

    @common_request
    def post(self):
        self.request_handler.common(self)
        if not self.empty_query_string('fingerprint', 'state'):
            fingerprint = self.get_parameter('fingerprint')
            state = self.get_parameter('state', default_value='unresolved',
                                       valid_iter=['unresolved', 'pending', 'submitted', 'resolved'])
            crash_report = CrashReports.update_report_state(fingerprint, state)
            if crash_report:
                crash_report_item = CrashReport.to_json(crash_report)
                self.add_parameter('crash_report', crash_report_item)
                self.add_to_json('crash_report', crash_report_item)
        self.render('update-crash-state.html')


class TrendingCrashesHandler(webapp2.RequestHandler):
    def common(self, handler):
        handler.add_parameter('title', 'Show Crash')
        handler.add_breadcrumb('Home', uri_for('home'))
        handler.add_breadcrumb('Trending Crashes', uri_for('trending_crashes'))
        RequestHandlerUtils.add_brand(handler)
        RequestHandlerUtils.add_nav_links(handler)

    @common_request
    def get(self):
        self.request_handler.common(self)
        start = self.get_parameter('start')
        trending_result = CrashReports.trending(start=start)
        self.add_parameter('trending', trending_result.get('trending', list()))
        self.add_parameter('has_more', trending_result.get('has_more', False))
        self.add_to_json('trending', trending_result)
        self.render('trending.html')


application = webapp2.WSGIApplication(
    [
        webapp2.Route('/', handler='main.RootHandler', name='home'),
        webapp2.Route('/crashes/state/update', handler='main.UpdateCrashStateHandler', name='update_crash_state'),
        webapp2.Route('/crashes/submit', handler='main.SubmitCrashHandler', name='submit_crash'),
        webapp2.Route('/crashes', handler='main.ViewCrashHandler', name='view_crash'),
        webapp2.Route('/trending', handler='main.TrendingCrashesHandler', name='trending_crashes'),
        webapp2.Route('/admin/crashes/upgrade',
                      handler='update_schema.UpdateSchemaHandler', name='update_crash_reports'),
    ]
    , debug=True
)
