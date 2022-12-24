import time, requests, argparse
from datetime import datetime, timedelta
from logging import debug, info, warning as warn, basicConfig, INFO, DEBUG

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webdriver import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.expected_conditions import (
    element_to_be_clickable as clickable,
    presence_of_element_located as present,
    url_to_be as url_is,
    text_to_be_present_in_element_attribute as text_in_attr
)

from rich.logging import RichHandler
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn, TimeElapsedColumn

from config import DEFAULT_HOURS_TO_CLOCK, USERNAME, PASSWORD, CHROMEDRIVER_PATH, FAIL_PING_URL, LOGIN_URL

progress_columns = [SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(bar_width=None), TimeElapsedColumn()]

def ping(text="", data=None, url=FAIL_PING_URL):
    try:
        requests.get(url, timeout=10, data=data)
        debug(f"{text} ping success")
    except requests.RequestException as e:
        warn(f"{text} ping failed: %s" % e)

class OneUSGAutoClock:
    wait_time_dict = {'long': 60.0, 'medium': 30.0, 'short': 15.0, 'tiny': 5.0}
    duo_timeout = 120.0

    def __init__(self, hours_to_clock: float = DEFAULT_HOURS_TO_CLOCK, only_out: bool = False):

        self.hours_to_clock = float(hours_to_clock)
        self.mins_to_clock = self.hours_to_clock * 60.0
        self.seconds_to_clock = self.mins_to_clock * 60.0

        self.only_out = bool(only_out)

        self.login_url = LOGIN_URL

        self.start_dt = datetime.now()
        self.end_dt = self.start_dt + timedelta(hours=self.hours_to_clock)

    @property
    def browser(self):
        if not hasattr(self, "_browser"):
            debug("Initializing browser")
            options = Options()
            options.add_argument("--headless")
            webdriver.chrome.service.DEFAULT_EXECUTABLE_PATH = CHROMEDRIVER_PATH
            self._browser = webdriver.Chrome(options=options)
            # TODO: switch to webdriver.Remote so we can catch KeyboardInterrupt without closing the browser
            # see https://github.com/SeleniumHQ/selenium/issues/10444
            self.logged_in = False
            debug("Browser initialized")
        else:
            debug("Using existing browser")

        return self._browser

    def WDWait(self, by=None, label=None,
               method=None, keys=None, timeout='medium',
               until=clickable, until_not=False, until_args=None):
        """
        Wrapper for WebDriverWait.until() with some convenience features.

        Parameters
        ----------
          * `by` : str
            `By.ID`, `By.XPATH`, etc.
          * `label` : str
            label of the element to find
          * `method` : str
            method to call on the element, must be one of ("click", "send_keys", None)
          * `keys` : str
            keys to send to the element, if method is "send_keys"
          * `timeout` : str or float
            WebDriverWait timeout (seconds). If a string, must be a key in self.wait_time_dict
          * `until` : callable
            expected condition to wait for, e.g. `clickable`, `present` (default `clickable`)
          * `until_not` : bool
            if True, use `WebDriverWait.until_not` instead of `WebDriverWait.until` (default False)
          * `until_args` : list
            arguments to pass to `WebDriverWait.until` (default `until_args=[(by, label)]`)
        """

        if isinstance(timeout, str):
            debug(f"setting timeout {timeout} to {self.wait_time_dict[timeout]}")
            timeout = self.wait_time_dict[timeout]

        waiter = WebDriverWait(self.browser, timeout)

        if until_args is None:
            debug(f"setting until_args to [(by, label)]")
            until_args = [(by, label)]
        else:
            debug(f"using passed until_args {until_args}")

        if not until_not:
            debug(f"waiting until {until.__name__}")
            element: WebElement = waiter.until(until(*until_args))
        else:
            debug(f"waiting until not {until.__name__}")
            element: WebElement = waiter.until_not(until(*until_args))

        if method == "click":
            debug(f"clicking {label}")
            element.click()
        elif method == "send_keys":
            debug(f"sending keys {keys if (keys != PASSWORD) else ('*'*len(keys))} to {label}")
            element.send_keys(keys)
        elif method is None:
            debug(f"returning element {label} without calling method")
        else:
            raise NotImplementedError(f"method {method} not implemented in WDWait")

        return element

    def login(self):
        # go to login page
        self.browser.get(self.login_url)

        # click gt logo
        self.WDWait(By.XPATH, "//*[@id='https_idp_gatech_edu_idp_shibboleth']/div/div/a/img", method="click")

        # type username
        self.WDWait(By.NAME, "username", method="send_keys", keys=USERNAME)

        # type password
        self.WDWait(By.NAME, "password", method="send_keys", keys=PASSWORD)

        # click submit
        self.WDWait(By.NAME, "submitbutton", method="click")

        # wait for duo auth to appear
        self.WDWait(By.ID, "auth-view-wrapper", until=present)

        # progress bar while we wait
        with Progress(*progress_columns, expand=True, transient=True) as progress:
            progress.add_task(f"Waiting for Duo Auth", total=None)

            try:
                # wait for duo auth to disappear
                self.WDWait(By.ID, "auth-view-wrapper", until_not=True, until=present, timeout=self.duo_timeout)
            except TimeoutException as e:
                ping(f"No Duo Auth after waiting for {self.duo_timeout} seconds.", data=f"NO DUO AUTH ({self.duo_timeout}s)")
                self.browser.quit()
                raise TimeoutException(f"No Duo Auth after waiting for {self.duo_timeout} seconds.") from e

            # trust this browser (dont-trust-browser-button for not trusting)
            self.WDWait(By.ID, "trust-browser-button", method="click")

            # wait for redirect to login page
            self.WDWait(until=url_is, until_args=[self.login_url])

            # refresh since on first redirect the page is blank
            self.browser.refresh()

        info("Authenticated")
        self.logged_in = True

    def go_to_clock_page(self):
        if self.logged_in and self.browser.current_url != self.login_url:
            debug("Already logged in, but not on clock page. Going to clock page.")
            self.browser.get(self.login_url)
        elif not self.logged_in:
            debug("Logging in.")
            self.login()
        else:
            debug("Already logged in and on clock page.")

    def clock_in(self):
        # go to login page if not already there
        self.go_to_clock_page()

        # click the menu button
        self.WDWait(By.ID, "TL_RPTD_SFF_WK_GROUPBOX$PIMG", method="send_keys", keys=Keys.RETURN)

        # click the "in" button
        self.WDWait(By.ID, "TL_RPTD_SFF_WK_TL_ACT_PUNCH1", method="send_keys", keys=Keys.RETURN)

        try:
            # handle double-clock popup (TODO: may not be needed)
            self.WDWait(By.ID, "#ICOK", method="send_keys", keys=Keys.RETURN)
            self.WDWait(By.ID, "PT_WORK_PT_BUTTON_BACK", method="send_keys", keys=Keys.RETURN)
            warn("Double-clock prevented.")
        except (NoSuchElementException, TimeoutException):
            pass

        # wait for status to be "In"
        self.WDWait(until=text_in_attr, until_args=[(By.ID, "TL_WEB_CLOCK_WK_DESCR50_1"), "innerHTML", "In"])

        # make note of clock-in time
        self.clock_in_time = time.time()
        self.clock_in_dt = datetime.now()

    def idle(self):
        # until the clockout time, refresh every 15 mins
        min_counter, elapsed_time = 0.0, 0.0
        with Progress(*progress_columns, expand=True, transient=True) as progress:
            tid = progress.add_task(f"Clocking", total=self.seconds_to_clock)

            while elapsed_time < self.seconds_to_clock:
                elapsed_time = time.time() - self.clock_in_time
                progress.update(tid, completed=elapsed_time)

                time.sleep(0.6)
                min_counter += 0.01
                if min_counter % 15 == 0:
                    self.browser.refresh()
                    debug(f"{elapsed_time / 3600:.3f}hrs / {min_counter}mins")
                    try:
                        # if the timeout popup appears, dismiss it
                        self.WDWait(By.ID, "BOR_INSTALL_VW$0_row_0", method="send_keys", keys=Keys.RETURN, timeout="tiny")
                        warn("Timeout Prevented")
                    except (NoSuchElementException, TimeoutException):
                        pass

    def clock_out(self):
        self.go_to_clock_page()

        # click the menu button
        self.WDWait(By.ID, "TL_RPTD_SFF_WK_GROUPBOX$PIMG", method="send_keys", keys=Keys.RETURN)

        # click the "out" button
        self.WDWait(By.ID, "TL_RPTD_SFF_WK_TL_ACT_PUNCH3", method="send_keys", keys=Keys.RETURN)

        # verify status is "Out"
        self.WDWait(until=text_in_attr, until_args=[(By.ID, "TL_WEB_CLOCK_WK_DESCR50_1"), "innerHTML", "Out"])

        # make note of clock-out time
        self.clock_out_time = time.time()
        self.clock_out_dt = datetime.now()
        self.clocked_time = self.clock_out_time - self.clock_in_time

    def run(self):
        if not self.only_out:
            info(f"Clocking {self.hours_to_clock}hrs / {self.hours_to_clock*60:.0f}mins (clock in at {self.start_dt}, out at {self.end_dt})")

        self.login()
        debug("Logged in")

        try:
            if not self.only_out:
                self.clock_in()
                info(f"Clocked in at {self.clock_in_dt}")

                self.idle()
                debug("Idle complete")
            else:
                warn("Only clocking out")
                self.clock_in_time = time.time()
        except KeyboardInterrupt:
            # NOTE: this does not work since SIGINT kills the browser too (https://github.com/SeleniumHQ/selenium/issues/10444)
            warn(f"Keyboard interrupt detected, clocking out")
        finally:
            self.clock_out()
            info(f"Clocked out at {self.clock_out_dt}")
            self.browser.quit()

        if self.clocked_time:
            info(f"Clocked {self.clocked_time / 3600:.3f}hrs / {self.clocked_time / 60:.0f}mins, {'more' if self.clocked_time > self.seconds_to_clock else 'less'} than requested ({self.hours_to_clock}hrs) by {abs((self.seconds_to_clock - self.clocked_time) / 60):.1f}mins.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="oneusg.py", description="Automated clock in/out for OneUSG hourly employees.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("hours", nargs="?", help="hours to clock", type=float, default=DEFAULT_HOURS_TO_CLOCK)
    parser.add_argument("--debug", action="store_true", help="set log level to debug")
    parser.add_argument("--only-out", action="store_true", help="clock out only")
    args = parser.parse_args()

    basicConfig(
        level=DEBUG if args.debug else INFO,
        format="%(message)s", datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, enable_link_path=False)],
    )

    try:
        OneUSGAutoClock(args.hours, only_out=args.only_out).run()
    except Exception as e:
        ping(f"Uncaught Exception at {datetime.now()}", data=str(e))
        raise e
