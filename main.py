import webapp2
from webapp2 import uri_for

from common import common_request
from model import CrashReport, Link
from util import CrashReports


class RootHandler(webapp2.RequestHandler):
    @common_request
    def get(self):
        self.add_parameter('title', 'T2 Crash Detector')
        self.add_breadcrumb('Home', uri_for('home'))
        brand = Link('T2 Crash Detector', uri_for('home'))
        nav_links = list()
        nav_links.append(Link('About', '#'))
        nav_links.append(Link('Contact', '#'))
        self.add_parameter('brand', brand)
        self.add_parameter('nav_links', nav_links)
        directory_links = list()
        directory_links.append(Link('Submit Crash', uri_for('submit_crash')))
        directory_links.append(Link('View Crash', uri_for('view_crash')))
        self.add_parameter('directory_links', directory_links)
        self.render('index.html')


class SubmitCrashHandler(webapp2.RequestHandler):
    def common(self, request):
        request.add_parameter('title', 'Submit Crash Report')
        request.add_breadcrumb('Home', uri_for('home'))
        request.add_breadcrumb('Submit Crash', uri_for('submit_crash'))
        brand = Link('T2 Crash Detector', uri_for('home'))
        nav_links = list()
        nav_links.append(Link('About', '#'))
        nav_links.append(Link('Contact', '#'))
        request.add_parameter('brand', brand)
        request.add_parameter('nav_links', nav_links)

    @common_request
    def get(self):
        self.request_handler.common(self)
        self.render('submit-crash.html')

    @common_request
    def post(self):
        self.request_handler.common(self)
        if self.empty_query_string('crash'):
            self.request_handler.redirect(uri_for('submit_crash'))
        else:
            crash = self.get_parameter('crash')
            # strip spaces around the crash report
            crash_report = CrashReports.add_crash_report(crash.strip())
            message = 'Added Crash Report with fingerprint, count) => (%s, %s)' % \
                      (crash_report.fingerprint, CrashReport.get_count(crash_report.name))
            self.add_message(message)
            self.add_to_json('crash_report', CrashReport.to_json(crash_report))
            self.render('submit-crash.html')


class ViewCrashHandler(webapp2.RequestHandler):
    def common(self, request):
        request.add_parameter('title', 'Show Crash')
        request.add_breadcrumb('Home', uri_for('home'))
        request.add_breadcrumb('View Crash', uri_for('view_crash'))
        brand = Link('T2 Crash Detector', uri_for('home'))
        nav_links = list()
        nav_links.append(Link('About', '#'))
        nav_links.append(Link('Contact', '#'))
        request.add_parameter('brand', brand)
        request.add_parameter('nav_links', nav_links)

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


application = webapp2.WSGIApplication(
    [
        webapp2.Route('/', handler='main.RootHandler', name='home'),
        webapp2.Route('/crashes/submit', handler='main.SubmitCrashHandler', name='submit_crash'),
        webapp2.Route('/crashes', handler='main.ViewCrashHandler', name='view_crash'),
    ]
    , debug=True
)
