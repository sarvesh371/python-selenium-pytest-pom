__author__ = 'sarvesh.singh'

import distro
from selenium import webdriver as seleniumwebdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.action_chains import ActionChains
from appium.webdriver.common.touch_action import TouchAction
from selenium.webdriver.common.by import By
from appium import webdriver
import pathlib
from base.common import (
    run_cmd,
    get_adb_device,
)
from base.logger import Logger
import zipfile
import os
import re
import time
import requests
from pathlib import Path
import base64
import allure


class WebDriver:
    """
    Class to connect any sort of web drivers and common methods of web driver to automate the mobile and web UI
    """

    def __init__(self, browser, remote=None, port='4444'):
        """
        Init Class to initialise Web Driver depending upon browser given
        @sarvesh: Grid is on 192.168.9.111
        param browser: chrome, firefox, android, ios
        :param remote:
        :param port:
        """
        self.browser = str(browser).lower()
        self.osName = distro.name().lower()
        self.logger = Logger(name='DRIVER').get_logger
        download_path = os.getcwd() + '/downloaded_files/'

        if remote is None:
            if self.browser == 'chrome':
                self.logger.debug(f"Local Chrome Driver")
                options = seleniumwebdriver.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--privileged")
                options.add_experimental_option('prefs', {'download.default_directory': download_path})
                self.driver = seleniumwebdriver.Chrome(
                    executable_path=self._get_latest_driver(),
                    desired_capabilities=options.to_capabilities(),
                    chrome_options=options
                )
                self.driver.implicitly_wait(time_to_wait=10)
                self.driver.maximize_window()
            elif self.browser == 'firefox':
                self.logger.debug(f"Local Firefox Driver")
                options = seleniumwebdriver.FirefoxOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--privileged")
                self.driver = seleniumwebdriver.Firefox(
                    executable_path=self._get_latest_driver(),
                    desired_capabilities=options.to_capabilities()
                )
                self.driver.implicitly_wait(time_to_wait=10)
                self.driver.maximize_window()
            elif self.browser == 'android':
                self.logger.debug(f"Local Android Appium Driver")
                os_path = os.environ.get('PATH', None)
                os_path = list(set(os_path.split(":")))
                user = str(run_cmd("whoami").output).strip()
                os_path.append(f"/Users/{user}/Library/Android/sdk/tools")
                os_path.append(f"/Users/{user}/Library/Android/sdk/platform-tools")
                os.environ['PATH'] = ":".join(os_path)
                os.environ['ANDROID_HOME'] = f"/Users/{user}/Library/Android/sdk"
                os.environ['JAVA_HOME'] = str(run_cmd("/usr/libexec/java_home").output).strip()
                apk_path = str(Path(__file__).parent.parent / "resources/com.flipkart.android.apk")
                # device_version = str(run_cmd('adb shell getprop ro.build.version.release').output).strip()
                run_cmd("appium --chromedriver-executable /usr/local/bin/chromedriver", wait=False)
                self.wait_for(10)
                desired_caps = {
                    'platformName': 'Android',
                    'platformVersion': str(run_cmd('adb shell getprop ro.build.version.release').output).strip(),
                    'deviceName': get_adb_device()[0],
                    'appPackage': 'com.flipkart',
                    'appActivity': '.MainActivity',
                    'INSTALL_GRANT_RUNTIME_PERMISSIONS': True,
                    'newCommandTimeout': 300,
                    'app': apk_path
                }
                self.driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
            elif self.browser == 'ios':
                self.logger.debug(f"Local iOS Appium Driver")
            else:
                self.logger.error(f'{self.browser} is a non-supported web-driver !!')
                raise Exception(f'{self.browser} is a non-supported web-driver !!')
        else:
            self.remote_server = f"http://{remote}:{port}/wd/hub"
            if self.browser == 'chrome':
                self.logger.debug(f"Remote Chrome Driver")
                capabilities = {
                    'browserName': 'chrome', 'version': '', 'platform': 'ANY', 'acceptInsecureCerts': True,
                    'timeouts': {'implicit': 60}, 'prefs': {'download.default_directory': download_path},
                    'goog:chromeOptions': {'extensions': [], 'args': ['--no-sandbox', '--privileged']}
                }
                self.driver = seleniumwebdriver.Remote(
                    command_executor=self.remote_server,
                    desired_capabilities=capabilities,
                )
                self.driver.implicitly_wait(time_to_wait=10)
                self.driver.maximize_window()
            elif self.browser == 'firefox':
                self.logger.debug(f"Remote Firefox Driver")
                options = seleniumwebdriver.FirefoxOptions()
                self.driver = seleniumwebdriver.Remote(
                    command_executor=self.remote_server,
                    desired_capabilities=options.to_capabilities(),
                )
                self.driver.implicitly_wait(time_to_wait=60)
                self.driver.maximize_window()
            elif self.browser == 'android':
                self.logger.debug(f"Remote Android Appium Driver")
            elif self.browser == 'ios':
                self.logger.debug(f"Remote iOS Appium Driver")
            else:
                self.logger.error(f'{self.browser} is a non-supported web-driver !!')
                raise Exception(f'{self.browser} is a non-supported web-driver !!')

    def _get_latest_driver(self):
        """
        Get Chrome's latest version from Google's Api
        :return:
        """
        if self.browser == 'chrome':
            if 'darwin' in self.osName:
                driver_location = Path(__file__).parent / f"web_drivers/darwin/chromedriver"
            elif 'linux' in self.osName:
                driver_location = Path(__file__).parent / f"web_drivers/linux/chromedriver"
            else:
                raise Exception(f"{self.osName} is not supported !!")

            down_version = re.search(r'ChromeDriver (.*?) ', run_cmd(f'{str(driver_location)} --version').output,
                                     re.I | re.M).group(1)

            # Get Download Link for Driver
            url = 'https://chromedriver.storage.googleapis.com/LATEST_RELEASE'
            current_version = requests.get(url=url).content.decode()
            if current_version == down_version:
                return str(driver_location)

            if 'darwin' == self.osName:
                url = f"https://chromedriver.storage.googleapis.com/{current_version}/chromedriver_mac64.zip"
            elif 'linux' in self.osName:
                url = f"https://chromedriver.storage.googleapis.com/{current_version}/chromedriver_linux64.zip"
            else:
                raise Exception(f"{self.osName} is not supported !!")

            response = requests.get(url=url, stream=True)
            response.raise_for_status()
            zip_location = Path(__file__).parent / "chromedriver.zip"
            with open(zip_location, 'wb') as handle:
                for block in response.iter_content(1024):
                    handle.write(block)

            with zipfile.ZipFile(zip_location, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(driver_location))
            os.remove(zip_location)
            return str(driver_location)

        elif self.browser == 'firefox':
            if 'darwin' in self.osName:
                driver_location = Path(__file__).parent / f"web_drivers/darwin/geckodriver"
            elif 'linux' in self.osName:
                driver_location = Path(__file__).parent / f"web_drivers/linux/geckodriver"
            else:
                raise Exception(f"{self.osName} is not supported !!")

            down_version = re.search(r'geckodriver (.*?) ', run_cmd(f'{str(driver_location)} --version').output,
                                     re.I | re.M).group(1)

            url = 'https://api.github.com/repos/mozilla/geckodriver/tags'
            response = requests.get(url=url).json()
            if f"v{down_version}" == response[0]['name']:
                return str(driver_location)

            url = response[0]['zipball_url']
            response = requests.get(url=url, stream=True)
            response.raise_for_status()
            zip_location = Path(__file__).parent / "geckodriver.zip"
            with open(zip_location, 'wb') as handle:
                for block in response.iter_content(1024):
                    handle.write(block)

            with zipfile.ZipFile(zip_location, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(driver_location))
            os.remove(zip_location)
            return str(driver_location)

        else:
            # TODO: add support to download FireFox Driver here
            raise Exception(f"self.browser is not supported Yet !!")

    def open_website(self, url):
        """
        This function is used to open the website in browser
        :param url:
        """
        self.driver.get(url)
        self.wait_for(seconds=5)

    def navigate_back(self):
        """
        Navigate back in browser
        """
        self.driver.back()

    def navigate_forward(self):
        """
        Navigate back in browser
        """
        self.driver.forward()

    def page_refresh(self):
        """
        Navigate back in browser
        """
        self.driver.refresh()

    def close_window(self):
        """
        This function is used to close the current active window of browser
        """
        self.driver.close()

    def get_title(self):
        """
        This function is used to get the title of page
        """
        return self.driver.title

    def get_web_element(self, element, locator_type):
        """
        This function is used to return the element
        :param element:
        :param locator_type:
        :return:
        """
        if locator_type == 'id':
            web_element = self.driver.find_element_by_id(element)
        elif locator_type == 'name':
            web_element = self.driver.find_element_by_name(element)
        elif locator_type == 'xpath':
            web_element = self.driver.find_element_by_xpath(element)
        elif locator_type == 'class':
            web_element = self.driver.find_element_by_class_name(element)
        elif locator_type == 'tag':
            web_element = self.driver.find_element_by_tag_name(element)
        elif locator_type == 'css':
            web_element = self.driver.find_element_by_css_selector(element)
        elif locator_type == 'link':
            web_element = self.driver.find_element_by_link_text(element)
        elif locator_type == 'partial_link':
            web_element = self.driver.find_element_by_partial_link_text(element)
        else:
            raise Exception(f'Provided locator type {locator_type} is not supported !!')

        return web_element

    def get_elements(self, element, locator_type):
        """
        This function is used to get the same type of elements in list
        :param element:
        :param locator_type:
        :return:
        """
        if locator_type == 'id':
            elements = self.driver.find_elements_by_id(element)
        elif locator_type == 'name':
            elements = self.driver.find_elements_by_name(element)
        elif locator_type == 'xpath':
            elements = self.driver.find_elements_by_xpath(element)
        elif locator_type == 'class':
            elements = self.driver.find_elements_by_class_name(element)
        elif locator_type == 'tag':
            elements = self.driver.find_elements_by_tag_name(element)
        elif locator_type == 'css':
            elements = self.driver.find_elements_by_css_selector(element)
        elif locator_type == 'link':
            elements = self.driver.find_elements_by_link_text(element)
        elif locator_type == 'partial_link':
            elements = self.driver.find_elements_by_partial_link_text(element)
        else:
            raise Exception(f'Provided locator type {locator_type} is not supported !!')
        return elements

    @staticmethod
    def get_locator_type(locator_type):
        """
        This function is used to return the locator type
        :param locator_type:
        :return:
        """
        if locator_type == 'id':
            locator_type = By.ID
        elif locator_type == 'name':
            locator_type = By.NAME
        elif locator_type == 'xpath':
            locator_type = By.XPATH
        elif locator_type == 'class':
            locator_type = By.CLASS_NAME
        elif locator_type == 'tag':
            locator_type = By.TAG_NAME
        elif locator_type == 'css':
            locator_type = By.CSS_SELECTOR
        elif locator_type == 'link':
            locator_type = By.LINK_TEXT
        elif locator_type == 'partial_link':
            locator_type = By.PARTIAL_LINK_TEXT
        else:
            raise Exception(f'Provided locator type {locator_type} is not supported !!')

        return locator_type

    def click(self, element, locator_type):
        """
        This function is used to click on the buttons, radio button, checkbox etc. available on web page
        :param element:
        :param locator_type:
        """
        try:
            self.get_web_element(element, locator_type).click()
            self.wait_for(1)
        except(Exception, ValueError):
            self.wait_for(2)
            self.get_web_element(element, locator_type).click()
            self.wait_for(1)

    def explicit_click(self, element, locator_type):
        """
        This function is used to click on element till wait for explict condition meet
        :param element:
        :param locator_type:
        """
        element = WebDriverWait(self.driver, 60).until(
            ec.element_to_be_clickable((self.get_locator_type(locator_type), element)))
        element.click()

    def explicit_check_element_is_clickable(self, element, locator_type, time_out):
        """
        This function is used to check the element is clickable or not and wait till explict condition meet
        :param element:
        :param locator_type:
        :param time_out:
        """
        WebDriverWait(self.driver, time_out).until(
            ec.element_to_be_clickable((self.get_locator_type(locator_type), element)))

    def explicit_visibility_of_element(self, element, locator_type, time_out):
        """
        This function is used to check the visibility on element till wait for explict condition meet
        :param element:
        :param locator_type:
        :param time_out:
        """
        WebDriverWait(self.driver, time_out).until(
            ec.visibility_of_element_located((self.get_locator_type(locator_type), element)))

    def explicit_invisibility_of_element(self, element, locator_type, time_out):
        """
        Explicit wait till element is not visible
        :param element:
        :param locator_type:
        :return:
        """
        WebDriverWait(self.driver, time_out).until(
            ec.invisibility_of_element((self.get_locator_type(locator_type), element)))

    def set_text(self, element, locator_type, text):
        """
        This function is used to Enter the values in Text box
        :param element:
        :param locator_type:
        :param text:
        """
        self.get_web_element(element, locator_type).send_keys(text)

    def get_text(self, element, locator_type):
        """
        This function is used to get the text from Labels available on page
        :param element:
        :param locator_type:
        """
        return self.get_web_element(element, locator_type).text

    def get_value_from_textbox(self, element, locator_type):
        """
        This function is used to get the text from text box on web page
        :param element:
        :param locator_type:
        :return:
        """
        return self.get_web_element(element, locator_type).get_attribute('value')

    def clear_text(self, element, locator_type, action_type):
        """
        Function to clear the value from text box
        :param element:
        :param locator_type:
        :param action_type:
        """
        web_element = self.get_web_element(element, locator_type)
        if action_type == 'clear':
            web_element.clear()
        elif action_type == 'action':
            action = self.key_chains()
            action.move_to_element(self.get_web_element(element, locator_type)).perform()
            action.send_keys(Keys.END).perform()
            for i in range(len(web_element.get_attribute('value'))):
                action.send_keys(Keys.BACK_SPACE).perform()
        else:
            length = len(web_element.get_attribute('value'))
            web_element.send_keys(length * Keys.BACKSPACE)

    def is_element_present(self, element, locator_type):
        """
        This function is used to check the element is Present on web page or not
        :param element:
        :param locator_type:
        :return:
        """
        if len(self.get_elements(element, locator_type)) > 0:
            return True
        else:
            return False

    def is_element_display_on_screen(self, element, locator_type):
        """
        This function is used to check the element is display on web page or not
        :param element:
        :param locator_type:
        :return:
        """
        try:
            return self.get_web_element(element, locator_type).is_displayed()
        except Exception:
            return False

    def is_element_selected(self, element, locator_type):
        """
        This function is used to check the element is selected on web page or not
        :param element:
        :param locator_type:
        :return:
        """
        return self.get_web_element(element, locator_type).is_selected()

    def is_element_enabled(self, element, locator_type):
        """
        This function is used to check the element is enabled on web page or not
        :param element:
        :param locator_type:
        :return:
        """
        return self.get_web_element(element, locator_type).is_enabled()

    @staticmethod
    def wait_for(seconds):
        """
        This is function is used for hard wait
        :param seconds:
        """
        time.sleep(seconds)

    def wait_till_element_appear_on_screen(self, element, locator_type):
        """
        This function is used to wait for the element appear on the page
        """
        flag = False
        count = 1
        while flag is False and count <= 40:
            flag = self.is_element_display_on_screen(element, locator_type)
            self.wait_for(2)
            count += 1

    def wait_till_element_disappear_from_screen(self, element, locator_type):
        """
        This function is used to wait for the element disappear from the page
        """
        flag = True
        count = 1
        while flag and count <= 40:
            flag = self.is_element_display_on_screen(element, locator_type)
            self.wait_for(2)
            count += 1

    def scroll(self, pixel_x, pixel_y):
        """
        This function is used to scroll the web page with x and y pixel
        :param pixel_x:
        :param pixel_y:
        """
        self.driver.execute_script(f"window.scrollTo({pixel_x},{pixel_y})")

    def scroll_till_element(self, element, locator_type):
        """
        This function is used to scroll the page till visibility of element
        :param element:
        :param locator_type:
        """
        self.driver.execute_script("arguments[0].scrollIntoView();", self.get_web_element(element, locator_type))

    def scroll_complete_page(self):
        """
        This function is used to scroll the complete web page to bottom
        """
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_complete_page_top(self):
        """
        This function is used to scroll the complete web page bottom to top
        """
        self.driver.execute_script("window.scrollTo(document.body.scrollHeight, 0);")

    def scroll_mobile(self, x_press, y_press, x_move, y_move):
        """
        Function to scroll in mobile device as per coordinates
        """
        TouchAction(self.driver).press(x=x_press, y=y_press).move_to(x=x_move, y=y_move).release().perform()

    def key_chains(self):
        """
        Initialize action class/Keychain class
        """
        return ActionChains(self.driver)

    def screen_shot(self, file_name):
        """
        This function is used to capture the screen shot on web page/device
        :param file_name:
        """
        ss_path = f"{os.getcwd()}/screenshots/{file_name}.png"
        self.driver.get_screenshot_as_file(ss_path)
        return ss_path

    def allure_attach_jpeg(self, file_name):
        """
        This function is used to capture the screen shot on web page/device
        :param file_name:
        """
        with open(self.screen_shot(file_name), "rb") as image:
            byte_image = bytearray(image.read())
        allure.attach(byte_image, name=f"{file_name}.png", attachment_type=allure.attachment_type.PNG)

    def select_by_index(self, element, locator_type, index):
        """
        selects the option located by index in a drop down
        :param element:
        :param locator_type:
        :param index:
        """
        select = Select(self.get_web_element(element, locator_type))
        select.select_by_index(index)

    def select_by_text(self, element, locator_type, text):
        """
        selects the option located by text in a drop down
        :param element:
        :param locator_type:
        :param text:
        """
        select = Select(self.get_web_element(element, locator_type))
        select.select_by_visible_text(text)

    def move_to_element(self, element, locator_type):
        """
        move to the element by action key class
        :param element:
        :param locator_type:
        """
        action = self.key_chains()
        action.move_to_element(self.get_web_element(element, locator_type)).perform()

    def move_to_element_and_click(self, element, locator_type):
        """
        move to the element by action key class and then click
        :param element:
        :param locator_type:
        """
        action = self.key_chains()
        action.move_to_element(self.get_web_element(element, locator_type)).click(element, locator_type).perform()

    def enter_data_in_textbox_using_action(self, element, locator_type, text):
        """
        move to the element by action key class then click and then enter the value in text box
        :param element:
        :param locator_type:
        :param text
        """
        action = self.key_chains()
        action.move_to_element(self.get_web_element(element, locator_type)).click().send_keys(text).send_keys(
            Keys.TAB).perform()

    def switch_to_iframe(self, frame_reference):
        """
        Switch to iframe
        :param frame_reference:
        """
        self.driver.switch_to.frame(frame_reference)

    def switch_to_default_content(self):
        """
        Switch to default content
        """
        self.driver.switch_to.default_content()

    def switch_to_alert_and_dismiss(self):
        """
        Switch to Alert
        """
        self.driver.switch_to.alert().dismiss()

    def get_contexts(self):
        """
        Get the all available context in mobile screen
        :return:
        """
        return self.driver.contexts

    def set_context(self, contexts, context_name):
        """
        Set the context on mobile screen
        :param contexts:
        :param context_name:
        :return:
        """
        for context in contexts:
            if context == context_name:
                self.driver.switch_to.context(context)
                break

    def get_current_window(self):
        """
        Get Current Window
        :return:
        """
        return self.driver.current_window_handle

    def open_and_switch_to_new_tab(self, index):
        """
        Open and switch to new tab
        :param index
        :return:
        """
        self.driver.execute_script("window.open();")
        # switch to the new window which is second in window_handles array
        self.driver.switch_to.window(self.driver.window_handles[index])

    def close_tab_and_switch_to_main_tab(self, switch_window_name):
        """
        Close tab and switch to main tab
        :param switch_window_name:
        :return:
        """
        self.driver.close()
        self.driver.switch_to.window(switch_window_name)

    def grid_download_verification(self, file_name):
        """
        Download via Grid and Verify
        :return:
        """
        window = self.get_current_window()
        self.open_and_switch_to_new_tab(index=1)
        # open successfully
        self.open_website("chrome://downloads/")
        files = self.driver.execute_script(
            """
            var elements = document
            .querySelector('downloads-manager')
            .shadowRoot.querySelector('#downloadsList').items;
            if (elements.every(e => e.state === "COMPLETE"))
                return elements.map(elements =>elements.fileUrl || elements.file_url);
            """
        )
        if files[0].rsplit("/", 1)[-1].__contains__(file_name):
            self.close_tab_and_switch_to_main_tab(window)
            return True
        else:
            self.close_tab_and_switch_to_main_tab(window)
            return False

    def get_file_content(self):
        """
        Read the file content and save the content in local system
        :return:
        """
        window = self.get_current_window()
        self.open_and_switch_to_new_tab(index=1)
        self.open_website("chrome://downloads/")
        files = self.driver.execute_script(
            """
            var elements = document
            .querySelector('downloads-manager')
            .shadowRoot.querySelector('#downloadsList').items;
            if (elements.every(e => e.state === "COMPLETE"))
                return elements.map(elements =>elements.fileUrl || elements.file_url);
            """
        )
        path = files[0]
        elem = self.driver.execute_script(
            "var input = window.document.createElement('INPUT'); "
            "input.setAttribute('type', 'file'); "
            "input.hidden = true; "
            "input.onchange = function (e) { e.stopPropagation() }; "
            "return window.document.documentElement.appendChild(input); ")

        elem._execute('sendKeysToElement', {'value': [path.replace('file:/', '').replace('%20', ' ')],
                                            'text': path.replace('file:/', '').replace('%20', ' ')})
        result = self.driver.execute_async_script(
            "var input = arguments[0], callback = arguments[1]; "
            "var reader = new FileReader(); "
            "reader.onload = function (ev) { callback(reader.result) }; "
            "reader.onerror = function (ex) { callback(ex.message) }; "
            "reader.readAsDataURL(input.files[0]); "
            "input.remove(); "
            , elem)

        if not result.startswith('data:'):
            self.close_tab_and_switch_to_main_tab(window)
            raise Exception("Failed to get file content: %s" % result)
        content = base64.b64decode(result[result.find('base64,') + 7:])
        with open(os.path.basename(re.sub("%20(...)", "", files[0])), 'wb') as f:
            f.write(content)
        self.close_tab_and_switch_to_main_tab(window)

    def check_local_system_download(self, file_path):
        """
        Check local System Download
        :param file_path:
        :return:
        """
        file = pathlib.Path(file_path)
        flag = False
        count = 1
        while flag is False:
            flag = file.exists()
            if count <= 40 and flag is False:
                self.wait_for(2)
                count = count + 1
        return flag

    @staticmethod
    def stop_appium():
        """
        This function to stop the appium
        """
        run_cmd("killall node", wait=False)

    def submit(self):
        """
        Function to click enter in mobile soft keyboard
        """
        self.driver.execute_script("mobile:performEditorAction", {'action': 'search'})


if __name__ == "__main__":
    w = WebDriver(browser='chrome', remote='192.168.9.111', port='5432')
    w.open_website('http://www.yahoo.com')
    w.screen_shot('sample.png')
