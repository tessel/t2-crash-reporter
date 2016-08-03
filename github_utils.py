import json
from github import Github

TOKEN_KEY = 'github_token'
OWNER = 'tessel'
REPO = 't2-cli'


class GithubClient(object):
    """
    A set of github utilities.
    """
    def __init__(self):
        with open('client_secrets.json', 'r') as contents:
            secrets = json.loads(contents.read())
            github_token = secrets.get(TOKEN_KEY)
            self.github_token = Github(login_or_token=github_token)

    """
    Submits a GitHub issue for a given fingerprint.
    """
    def submit_issue(self, fingerprint):
        pass