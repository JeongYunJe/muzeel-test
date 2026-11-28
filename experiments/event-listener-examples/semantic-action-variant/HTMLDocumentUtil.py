import json
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium.webdriver import Chrome
from selenium.common.exceptions import WebDriverException
from .event_handling.Event import Event


class HTMLDocumentUtil:
    """Class which takes the page source and generates a list of all potential events.
    """
    def __init__(self, browser: Chrome, semantic_only=False):
        self.browser = browser
        self.doc = BeautifulSoup(self.browser.page_source, 'html.parser', multi_valued_attributes=None)
        self.semantic_only = semantic_only
        self._candidate_keys = set()
        self._semantic_keys = set()
        self.stats = {"native_listeners": 0, "semantic_candidates": 0, "duplicates_removed": 0}
        self.event_list = []
        self.global_xpath_map = {}
        self.dfs(self.doc.find_all("body")[0], "/html/body")
        # The original execution loop consumes candidates from the end.
        self.event_list.sort(key=lambda e: (e.event_type, e.xpath) in self._semantic_keys)

    def dfs(self, root: Tag, xpath: str) -> None:
        """Conducts a dfs traversal over the body of the page, for each element, it constructs an xpath and uses cdp
        to check which events are attached.

        Currently, link, script, style, svg, img, noscript elements are ignored and their descendants are not explored, because they cannot contain user interaction events.
        Also, the events attached to the body are ignored, but descendants are explored.

        Args:
            root (Tag): Root tag of dfs
            xpath (str): Starting xpath, for body, this is "/html/body"

        Potential Updates:
        Event hierarchy is not currently considered. Sometimes events are not attached to the element itself but one of its parents.
        To be able to properly get all events, it is important to consider parent events. However, this greatly increases the number of events to consider.
        Things to try:
        . Add events attached to the body to all children.
        . ML model that can identify events based on tag name and attributes. Generate data set from real user tests + cdp entries
        . Attempt to add predecessor events to child events (Note: this will be costly but worth a try)
        """
        if xpath != "/html/body":
            if not self.semantic_only:
                for listener in self.get_event_listeners_by_xpath(xpath):
                    self.stats["native_listeners"] += 1
                    self.add_candidate(listener["type"], xpath)
            action = self.semantic_action(root)
            if action and self.is_actionable(xpath):
                # Keep each query as a separate replayable action, so another
                # query cannot overwrite it before the exploration refresh.
                actions = (["search-cycle:a-f"] + ["fill:" + letter for letter in "abcdefghijklmnopqrstuvwxyz"]
                           if action == "fill" and self.is_search_input(root) else [action])
                for candidate_action in actions:
                    self.stats["semantic_candidates"] += 1
                    self.add_candidate(candidate_action, xpath, semantic=True)

        child_map = {}
        for child in root.contents:
            if child.name:
                tag_name = child.name

                if tag_name not in ["link", "script", "style", "svg", "img", "noscript"]:
                    curr_tag_index = child_map.get(tag_name, 0) + 1
                    child_map[tag_name] = curr_tag_index

                    if "id" in child.attrs:
                        child_xpath = "//{}[@id={}]".format(tag_name, self.xpath_literal(child['id']))
                        global_index_of_child = self.global_xpath_map.get(child_xpath, 0) + 1
                        self.global_xpath_map[child_xpath] = global_index_of_child
                        self.dfs(child, "({})[{}]".format(child_xpath, global_index_of_child))

                    elif "class" in child.attrs:
                        child_xpath = "//{}[@class={}]".format(tag_name, self.xpath_literal(child['class']))
                        global_index_of_child = self.global_xpath_map.get(child_xpath, 0) + 1
                        self.global_xpath_map[child_xpath] = global_index_of_child
                        self.dfs(child, "({})[{}]".format(child_xpath, global_index_of_child))

                    else:
                        self.dfs(child, "{}/{}[{}]".format(xpath, tag_name, curr_tag_index))

    DEDUPLICATE_ACTIONS = True

    @staticmethod
    def is_search_input(node):
        return node.name == "input" and (
            node.get("type", "text").lower() == "search"
            or "searchbox" in node.get("role", "").lower().split()
            or "search" in node.get("placeholder", "").lower()
            or "검색" in node.get("placeholder", ""))

    @staticmethod
    def xpath_literal(value):
        if "'" not in value:
            return "'" + value + "'"
        if '"' not in value:
            return '"' + value + '"'
        return "concat(" + ', "\'", '.join("'" + part + "'" for part in value.split("'")) + ")"

    def add_candidate(self, event_type, xpath, semantic=False):
        if self.DEDUPLICATE_ACTIONS and event_type in ("click", "mousedown", "mouseup"):
            event_type = "click"
        key = (event_type, xpath)
        if semantic:
            self._semantic_keys.add(key)
        if self.DEDUPLICATE_ACTIONS and key in self._candidate_keys:
            self.stats["duplicates_removed"] += 1
            return
        self._candidate_keys.add(key)
        self.event_list.append(Event(event_type, xpath))

    @staticmethod
    def semantic_action(node):
        tag = node.name
        kind = node.get("type", "text").lower()
        roles = node.get("role", "").lower().split()
        if tag == "input":
            if kind in ("button", "submit", "reset", "checkbox", "radio"):
                return "click"
            if kind in ("range", "number"):
                return "adjust"
            if kind in ("text", "search", "email", "password", "url", "tel"):
                return "fill"
            return None
        if tag == "textarea" or node.get("contenteditable", "false").lower() in ("", "true", "plaintext-only"):
            return "fill"
        if tag == "select":
            return "select"
        if tag == "button" or (tag == "a" and node.has_attr("href")) or any(r in roles for r in ("button", "tab")):
            return "click"
        return None

    def is_actionable(self, xpath):
        try:
            element = self.browser.find_element(By.XPATH, xpath)
            return element.is_displayed() and element.is_enabled() and not self.browser.execute_script(
                "return !!arguments[0].closest('[inert], [aria-disabled=true]')", element)
        except WebDriverException:
            return False

    def get_event_listeners_by_xpath(self, xpath: str) -> list:
        try:
            xpath_to_object_id_query = {"expression": "document.evaluate(" + json.dumps(xpath) + ",document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null).snapshotItem(0)"}
            object_id = self.browser.execute_cdp_cmd("Runtime.evaluate", xpath_to_object_id_query)['result']
            listeners = self.browser.execute_cdp_cmd("DOMDebugger.getEventListeners", object_id)
            return listeners['listeners']
        except WebDriverException:
            print("Trouble locating xpath", xpath)
            return []
