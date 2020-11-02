# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import absolute_import
from builtins import str
from builtins import range
from builtins import object
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from .pages.login import LoginPage
from .utils import backend_retry
import pytest
import requests
import time
import traceback
import logging
import os
import re
# requests.urllib3.disable_warnings()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
PNG_PATH = "assets"

class SeleniumHelper(object):
    """
    The helper class provides the Remote Browser
    """
    sauce_username=None
    sauce_access_key=None
    sauce_tunnel_id=None
    sauce_tunnel_parent=None
    jenkins_build=None

    def __init__(self, browser, browser_version, splunk_web_url, splunk_mgmt_url, debug=False, cred=("admin", "Chang3d!"), headless=False, test_case=None):
        self.splunk_web_url = splunk_web_url
        self.splunk_mgmt_url = splunk_mgmt_url
        self.cred = cred
        self.test_case = test_case
        if not debug:
            # Using Saucelabs
            self.init_sauce_env_variables()

        try:
            if browser == "firefox":
                if debug:
                    self.browser = webdriver.Firefox(firefox_options=self.get_local_firefox_opts(headless), log_path="selenium.log")
                else:
                    self.browser = webdriver.Remote(
                    command_executor='https://ondemand.saucelabs.com:443/wd/hub',
                    desired_capabilities=self.get_sauce_firefox_opts(browser_version)) 

            elif browser == "chrome":
                if debug:
                    self.browser = webdriver.Chrome(
                        chrome_options=self.get_local_chrome_opts(headless), 
                        service_args=["--verbose", "--log-path=selenium.log"]
                    )
                else:
                    self.browser = webdriver.Remote(
                    command_executor = 'https://ondemand.saucelabs.com:443/wd/hub',
                    desired_capabilities = self.get_sauce_chrome_opts(browser_version))

            elif browser == "IE":
                if debug:
                    self.browser = webdriver.Ie(capabilities=self.get_local_ie_opts())
                else:
                    self.browser = webdriver.Remote(
                    command_executor = 'https://ondemand.saucelabs.com:443/wd/hub',
                    desired_capabilities = self.get_sauce_ie_opts(browser_version))
            elif browser == "safari":
                if debug:
                    self.browser = webdriver.Safari()
                else:
                    self.browser = webdriver.Remote(
                    command_executor = 'https://ondemand.saucelabs.com:443/wd/hub',
                    desired_capabilities = self.get_sauce_safari_opts(browser_version))
            else:
                raise Exception("No valid browser found.! expected=[firefox, chrome, safari], got={}".format(browser))
        except Exception as e:
            raise e

        try:
            self.browser_session = self.browser.session_id
            self.login_to_splunk(*self.cred)
        except:
            self.browser.quit()
            if not debug:
                self.update_saucelab_job(False)
            raise

    @classmethod
    def init_sauce_env_variables(cls):
        # Read Environment variables to fetch saucelab credentials
        if cls.sauce_username and cls.sauce_access_key:
            return
        cls.sauce_username = os.environ.get('SAUCE_USERNAME')
        cls.sauce_access_key = os.environ.get('SAUCE_PASSWORD')
        cls.sauce_tunnel_id = os.environ.get('SAUCE_TUNNEL_ID') or 'sauce-ha-tunnel'
        cls.sauce_tunnel_parent = os.environ.get('SAUCE_TUNNEL_PARENT') or 'qtidev'
        if cls.sauce_tunnel_parent in ["null", "none"]:
            cls.sauce_tunnel_parent = None

        cls.jenkins_build = os.environ.get('JOB_NAME') or os.environ.get('JENKINS_JOB_ID') or "Local Run"
        print("\nUsing Saucelabs tunnel: {}".format(cls.sauce_tunnel_id))
        if not cls.sauce_username or not cls.sauce_access_key: 
            raise Exception(
                    "SauceLabs Credentials not found in the environment."
                    " Please make sure SAUCE_USERNAME and SAUCE_PASSWORD is set."
                )

    def get_sauce_opts(self):
        # Get saucelab default options
        sauce_options = {
            'screenResolution': '1280x768',
            'seleniumVersion': '3.141.0',
            # best practices involve setting a build number for version control
            'build': self.jenkins_build,
            'name': self.test_case,
            'username': self.sauce_username,
            'accessKey': self.sauce_access_key,
            # setting sauce-runner specific parameters such as timeouts helps
            # manage test execution speed.
            'maxDuration': 1800,
            'commandTimeout': 300,
            'idleTimeout': 1000,
            'tunnelIdentifier': self.sauce_tunnel_id,
        }
        if self.sauce_tunnel_parent:
            sauce_options["parenttunnel"] = self.sauce_tunnel_parent

        return sauce_options

    def get_sauce_ie_opts(self, browser_version):
        sauce_options = {
            'build': self.jenkins_build,
            'name': self.test_case,
            'username': self.sauce_username,
            'accessKey': self.sauce_access_key,
            'tunnelIdentifier': 'sauce-ha-tunnel',
            'parenttunnel':'qtidev',
            'platformName': 'Windows 10',
            'browserName': 'internet explorer',
            'seleniumVersion': '3.141.0',
            'iedriverVersion': '3.141.0',
            'maxDuration': 1800,
            'commandTimeout': 300,
            'idleTimeout': 1000
        }
        ie_opts = {
            'platformName': 'Windows 10',
            'browserName': 'internet explorer',
            'browserversion': browser_version,
            'iedriverVersion': "3.141.0",
            'sauce:options': sauce_options 
        }
        return ie_opts

    def get_local_ie_opts(self):
        capabilities = DesiredCapabilities.INTERNETEXPLORER
        capabilities['se:ieOptions'] = {}
        capabilities['ignoreZoomSetting'] = True
        capabilities['se:ieOptions']['ie.ensureCleanSession'] = True
        capabilities['requireWindowFocus'] = True
        capabilities['nativeEvent'] = False
        return capabilities
        
    def get_local_chrome_opts(self, headless_run):
        chrome_opts = webdriver.ChromeOptions()
        chrome_opts.add_argument('--ignore-ssl-errors=yes')
        chrome_opts.add_argument('--ignore-certificate-errors')
        if headless_run:
            chrome_opts.add_argument('--headless')
            chrome_opts.add_argument("--window-size=1280,768")
        return chrome_opts

    def get_local_firefox_opts(self, headless_run):
        firefox_opts = webdriver.FirefoxOptions()
        firefox_opts.log.level = "trace"
        if headless_run:
            firefox_opts.add_argument('--headless')
            firefox_opts.add_argument("--window-size=1280,768")
        return firefox_opts

    def get_sauce_firefox_opts(self, browser_version):
        firefox_opts = {
            'platformName': 'Windows 10',
            'browserName': 'firefox',
            'browserVersion': browser_version,
            'sauce:options': self.get_sauce_opts(),
            'acceptInsecureCerts': True,
            'acceptSslCerts': True
        }
        return firefox_opts

    def get_sauce_chrome_opts(self, browser_version):
        chrome_opts = {
            'platformName': 'Windows 10',
            'browserName': 'chrome',
            'browserVersion': browser_version,
            'goog:chromeOptions': {'w3c': True,'args':['ignore-certificate-errors','ignore-ssl-errors=yes']},
            'sauce:options': self.get_sauce_opts()
        }
        return chrome_opts

    def get_sauce_safari_opts(self, browser_version):
        sauce_opts = self.get_sauce_opts()
        sauce_opts["screenResolution"] = "1024x768"
        safari_opts = {
            'platformName': 'macOS 10.14',
            'browserName': 'safari',
            'browserVersion': browser_version,
            'sauce:options': sauce_opts
        }
        return safari_opts

    def login_to_splunk(self, *cred):
        try:
            login_page = LoginPage(self)
            login_page.login.login(*cred)
        except:
            self.browser.save_screenshot(os.path.join(PNG_PATH, "login_error.png"))
            raise

    def update_saucelab_job(self, status):
        data = '{"passed": false}' if status else '{"passed": true}'
        response = requests.put('https://saucelabs.com/rest/v1/{}/jobs/{}'.format(
                        self.sauce_username, self.browser_session), 
                        data=data, 
                        auth=(self.sauce_username, self.sauce_access_key))
        response = response.json()
        print("\nSauceLabs job_id={}".format(response.get("id")))
        print("SauceLabs Video_url={}".format(response.get("video_url")))

class RestHelper(object):

    def __init__(self, splunk_mgmt_url, username ,password):
        self.splunk_mgmt_url = splunk_mgmt_url
        self.username = username
        self.password = password
        self.start_session()

    @backend_retry(3)
    def start_session(self):
        res = requests.post(self.splunk_mgmt_url + '/services/auth/login?output_mode=json',
                            data={'username': self.username, 'password': self.password }, verify=False)

        try:
            res = res.json()
        except:
            raise Exception("Could not parse the content returned from Management Port. Recheck the mgmt url.")
        if (len(res.get("messages", [])) > 0) and (res["messages"][0].get("type") == "WARN"):
            raise Exception("Could not connect to the Splunk instance, verify credentials")

        self.session_key = str(res["sessionKey"])

class UccTester(object):
    """
    The default setup and teardown methods can be added here.
    Use in case if some additional configuration should be added to all the test cases
    """

    def setup_class(self):
        self.wait = WebDriverWait(None, 20)

    def assert_util(self, left, right, operator="==",left_args={}, right_args={}, msg=None):
        args = {'left': left, 'right': right, 'operator':operator, 'left_args': left_args, 'right_args': right_args, 'left_value':None, 'right_value':None}
        operator_map = {
            "==": lambda left,right: left == right,
            "!=": lambda left,right: left != right,
            "<": lambda left,right: left < right,
            "<=": lambda left,right: left <= right,
            ">": lambda left,right: left > right,
            ">=": lambda left,right: left >= right,
            "in": lambda left,right: left in right,
            "not in": lambda left,right: left not in right,
            "is": lambda left,right: left is right,
            "is not": lambda left,right: left is not right,
        }
        def _assert(browser):
            if callable(args['left']):
                args['left_value'] = args['left'](**args['left_args'])
            else:
                args['left_value'] = args['left']
            if callable(args['right']):
                args['right_value'] = args['right'](**args['right_args'])
            else:
                args['right_value'] = args['right']
            return operator_map[args['operator']](args['left_value'], args['right_value'])
        try:
            self.wait.until(_assert)
            condition_failed = False
        except TimeoutException:
            condition_failed = True
        if condition_failed:
            if not msg:
                msg = "Condition Failed. \nLeft-value: {}\nOperator: {}\nRight-value: {}".format(args['left_value'], args["operator"], args['right_value'])
            assert operator_map[args['operator']](args['left_value'], args['right_value']), msg
