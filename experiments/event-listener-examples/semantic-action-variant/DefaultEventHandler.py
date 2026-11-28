from seleniumwire.webdriver import Chrome
from selenium.common.exceptions import NoSuchElementException, MoveTargetOutOfBoundsException, JavascriptException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from time import sleep
from .exceptions.InteractionBotException import InteractionBotException
from .EventHandler import EventHandler
from .Event import Event
from .BrowserInteractions import BrowserInteractions


class DefaultEventHandler(EventHandler):
    def __try_double_click(self, base_url, element):
        try:
            alert_closed = BrowserInteractions.close_alert_dismiss(self.browser)
            BrowserInteractions.close_extraneous_tabs(self.browser, 1)
            click_cnt = 0
            while not alert_closed and self.browser.current_url == base_url and click_cnt < 2:
                ActionChains(self.browser).move_to_element(element).click(element).perform()
                alert_closed = BrowserInteractions.close_alert_dismiss(self.browser)
                BrowserInteractions.close_extraneous_tabs(self.browser, 1)
                click_cnt += 1
        except:
            pass

    def set_browser(self, browser: Chrome) -> None:
        self.browser = browser

    def trigger_individual_event(self, event: Event) -> None:
        """This function triggers an individual event.

        Args:
            event (Event): Event to be triggered

        Raises:
            InteractionBotException: In case the event can't be triggered, we raise InteractionBotException
        
        Potential Updates:
        Checking if an error occurred after triggering an event may not be the best way of determining if an event, look for other methods.
        """
        xpath = event.xpath
        event_type = event.event_type
        element = self.find_element_by_xpath(xpath)
        try:
            if event_type == "search-cycle:a-f":
                element.click()
                # Backspace emits the input event React needs for controlled
                # fields. Keep the whole sequence in one replayable action;
                # do not refresh or await each search's completion here.
                self.browser.execute_script("arguments[0].select()", element)
                element.send_keys(Keys.BACKSPACE)
                for letter in "abcdef":
                    element.send_keys(letter)
                    sleep(0.05)
                    self.browser.execute_script("arguments[0].select()", element)
                    element.send_keys(Keys.BACKSPACE)
                    sleep(0.05)
                # Let the last transition finish before the outer loop refreshes.
                sleep(0.5)
            elif event_type == "fill" or (event_type.startswith("fill:") and event_type[5:] in "abcdefghijklmnopqrstuvwxyz" and len(event_type[5:]) == 1):
                element.click()
                element.clear()
                sample = (event_type[5:] if event_type.startswith("fill:") else
                          {"email": "muzeel@example.com", "url": "https://example.com", "tel": "01012345678"}.get(element.get_attribute("type"), "ABCD"))
                element.send_keys(sample)
            elif event_type == "select":
                choices = Select(element)
                for option in choices.options:
                    if option.is_enabled() and not option.is_selected():
                        choices.select_by_index(choices.options.index(option))
                        break
            elif event_type == "adjust":
                # WebElement.send_keys focuses this control. Clicking a range's
                # midpoint first would unintentionally select a large delay.
                element.send_keys(Keys.ARROW_RIGHT if element.get_attribute("type") == "range" else Keys.ARROW_UP)
            elif event_type in ["click", "mousedown", "mouseup", "focus", "blur"]:
                base_url = self.browser.current_url
                ActionChains(self.browser).move_to_element(element).click(element).perform()
                self.__try_double_click(base_url, element)

            elif event_type in ["mouseover", "mouseenter"]:
                ActionChains(self.browser).move_to_element(element).perform()

            elif event_type in ["mouseout", "mouseleave"]:
                ActionChains(self.browser).move_to_element(element).perform()
                ActionChains(self.browser).move_by_offset(100, 100).perform()

            elif event_type in ["keydown", "keypress", "keyup", "input", "change"]:
                ActionChains(self.browser).move_to_element(element).send_keys("ABCD").perform()

            elif event_type in ["dblclick"]:
                ActionChains(self.browser).move_to_element(element).double_click(element).perform()

            elif event_type in ["drag", "dragstart", "dragend"]:
                ActionChains(self.browser).move_to_element(element).drag_and_drop_by_offset(element, 100, 0).perform()

            elif event_type in ["baseEvent"]:
                print("Base event triggered")

            else:
                raise InteractionBotException
        except (MoveTargetOutOfBoundsException, JavascriptException):
            pass
        except Exception:
            BrowserInteractions.close_extraneous_tabs(self.browser, 1)
            raise InteractionBotException from None
        finally:
            BrowserInteractions.close_extraneous_tabs(self.browser, 1)

    def find_element_by_xpath(self, xpath: str) -> object:
        web_element_found = False
        element = None

        while not web_element_found:
            try:
                element = self.browser.find_element(By.XPATH, xpath)
                web_element_found = True
            except NoSuchElementException:
                raise InteractionBotException
            except:
                raise InteractionBotException

        return element
