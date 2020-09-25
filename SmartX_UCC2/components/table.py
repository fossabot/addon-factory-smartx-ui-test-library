from ..components.base_component import BaseComponent
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import re
import time
from selenium.common import exceptions

class Table(BaseComponent):
    """
    Component: Table
    Base class of Input & Configuration table
    """
    def __init__(self, browser, container, mapping=dict()):
        """
            :param browser: The selenium webdriver
            :param container: Container in which the table is located. Of type dictionary: {"by":..., "select":...}
            :param mapping= If the table headers are different from it's html-label, provide the mapping as dictionary. For ex, {"Status": "disabled"}
        """
        super(Table, self).__init__(browser, container)
        self.header_mapping = mapping
        self.elements.update({
            "rows": {
                "by": By.CSS_SELECTOR,
                "select": container["select"] + " tr.apps-table-tablerow"
            },
            "header": {
                "by": By.CSS_SELECTOR,
                "select": container["select"] + " th"
            },
            "action_values": {
                "by": By.CSS_SELECTOR,
                "select": " .dropdown-menu.open li a"
            },
            "col": {
                "by": By.CSS_SELECTOR,
                "select": container["select"] + " td.col-{column}"
            },
            "action": {
                "by": By.CSS_SELECTOR,
                "select": container["select"] + " a.dropdown-toggle"
            },
            "action_list": {
                "by": By.CSS_SELECTOR,
                "select": ".dropdown-menu.open li a"
            },
            "edit": {
                "by": By.CSS_SELECTOR,
                "select": "a.edit"
            },
            "clone": {
                "by": By.CSS_SELECTOR,
                "select": "a.clone"
            },
            "delete": {
                "by": By.CSS_SELECTOR,
                "select": "a.delete"
            },
            "delete_prompt": {
                "by": By.CSS_SELECTOR,
                "select": ".modal-dialog div.delete-prompt"
            },
            "delete_btn": {
                "by": By.CSS_SELECTOR,
                "select": ".modal-dialog .submit-btn"
            },
            "delete_cancel": {
                "by": By.CSS_SELECTOR,
                "select": ".modal-dialog .cancel-btn"
            },
            "delete_close": {
                "by": By.CSS_SELECTOR,
                "select": ".modal-dialog button.close"
            },
            "delete_loading": {
                "by": By.CSS_SELECTOR,
                "select": ".modal-dialog .msg-loading"
            },
            "waitspinner": {
                "by": By.CSS_SELECTOR,
                "select": container["select"] + " div.shared-waitspinner"
            },
            "count": {
                "by": By.CSS_SELECTOR,
                "select": container["select"] +" .shared-collectioncount"
            },
            "filter": {
                "by": By.CSS_SELECTOR,
                "select": container["select"] + " input.search-query"
            },
            "filter_clear": {
                "by": By.CSS_SELECTOR,
                "select": container["select"] + " a.control-clear"
            }
        })

    def get_count_title(self):
        """
        Get the count mentioned in the table title
        """
        return self.count.text

    def get_row_count(self):
        """
        Count the number of rows in the page.
        """
        return len(list(self._get_rows()))

    def get_headers(self):
        """
        Get list of headers from the table
        """
        return [each.text for each in self.get_elements("header")]

    def get_sort_order(self):
        """
        Get the column-header which is sorted rn.
        Warning: It depends on the class of the headers and due to it, the returned result might give wrong answer.
        :returns : a dictionary with the "header" & "ascending" order
        """
        for each_header in self.get_elements("header"):
            if re.search(r"\basc\b", each_header.get_attribute("class")):
                return {
                    "header": each_header.text.lower(),
                    "ascending": True
                }
            elif re.search(r"\bdesc\b", each_header.get_attribute("class")):
                return {
                    "header": each_header.text.lower(),
                    "ascending": False
                }

    def sort_column(self, column, ascending=True):
        """
        Sort a column in ascending or descending order
            :param column: The header of the column which should be sorted
            :param ascending: True if the column should be sorted in ascending order, False otherwise
        """
        for each_header in self.get_elements("header"):
            
            if each_header.text.lower() == column.lower():
                if "asc" in each_header.get_attribute("class") and ascending:
                    # If the column is already in ascending order, do nothing
                    return
                elif "asc" in each_header.get_attribute("class") and not ascending:
                    # If the column is in ascending order order and we want to have descending order, click on the column-header once
                    each_header.click()
                    self._wait_for_loadspinner()
                    return
                elif "desc" in each_header.get_attribute("class") and not ascending:
                    # If the column is already in descending order, do nothing
                    return
                elif "desc" in each_header.get_attribute("class") and ascending:
                    # If the column is in descending order order and we want to have ascending order, click on the column-header once
                    each_header.click()
                    self._wait_for_loadspinner()
                    return
                else:
                    # The column was not sorted before
                    if ascending:
                        # Click to sort ascending order
                        each_header.click()
                        self._wait_for_loadspinner()
                        return
                    else:
                        # Click 2 times to sort in descending order

                        #Ascending
                        each_header.click()
                        self._wait_for_loadspinner()
                        #Decending
                        # The existing element changes (class will be changed), hence, it can not be referenced again.
                        # So we need to get the headers again and do the same process.
                        self.sort_column(column, ascending=False)
                        return
        

    def _wait_for_loadspinner(self):
        """
        There exist a loadspinner when sorting/filter has been applied. This method will wait until the spinner is dissapeared 
        """
        try:
            self.wait_for("waitspinner")
            self.wait_until("waitspinner")
        except:
            print("Waitspinner did not appear")

    def get_table(self):
        """
        Get whole table in dictionary form. The row_name will will be the key and all header:values will be it's value.
        {row_1 : {header_1: value_1, . . .}, . . .}
        """
        table = dict()
        headers = self.get_headers()
        for each_row in self._get_rows():
            row_name = self._get_column_value(each_row, "name")
            table[row_name] = dict()
            for each_col in headers:
                each_col = each_col.lower()
                if each_col:
                        table[row_name][each_col] = self._get_column_value(each_row, each_col) 
        return table

    def get_cell_value(self, name, column):
        """
        Get a specific cell value.
            :param name: row_name of the table
            :param column: column header of the table
        """
        _row = self._get_row(name)
        return self._get_column_value(_row, column)
    
    def get_column_values(self, column):
        """
        Get list of values of  column
            :param column: column header of the table
        """
        for each_row in self._get_rows():
            yield self._get_column_value(each_row, column)

    def get_list_of_actions(self, name):
        """
        Get list of possible actions for a specific row
        :param name: The name of the row
        """
        _row = self._get_row(name)
        _row.find_element(*self.elements["action"].values()).click()
        return [each_element.text for each_element in self.get_elements("action_list")]

    def edit_row(self, name):
        """
        Edit the specified row. It will open the edit form(entity). The opened entity should be interacted with instance of entity-class only.
            :param name: row_name of the table
        """
        _row = self._get_row(name)
        _row.find_element(*self.elements["action"].values()).click()
        self.edit.click()

    def clone_row(self, name):
        """
        Clone the specified row. It will open the edit form(entity). The opened entity should be interacted with instance of entity-class only.
            :param name: row_name of the table
        """
        _row = self._get_row(name)
        _row.find_element(*self.elements["action"].values()).click()
        self.clone.click()

    def delete_row(self, name, cancel=False, close=False):
        """
        Delete the specified row. Clicking on delete will open a pop-up. Delete the row if neither of (cancel, close) specified.
            :param name: row_name of the table
            :param cancel: if provided, after the popup is opened, click on cancel button and Do Not delete the row
            :param close:  if provided, after the popup is opened, click on close button and Do Not delete the row
        """

        # Click on action
        _row = self._get_row(name)
        _row.find_element(*self.elements["action"].values()).click()

        # Click on delete action
        self.delete.click()
        self.wait_for("delete_prompt")

        if cancel:
            self.delete_cancel.click()
            self.wait_until("delete_cancel")
            return True
        elif close:
            self.delete_close.click()
            self.wait_until("delete_close")
            return True           
        else:
            self.delete_btn.click()
            self.wait_for("delete_loading")
            self.wait_until("delete_loading")
            
            
    def set_filter(self, filter_query):
        """
        Provide a string in table filter.
            :param filter_query: query of the filter
            :returns : resultant list of filtered row_names
        """
        self.filter.clear()
        self.filter.send_keys(filter_query)
        time.sleep(1)
        self._wait_for_loadspinner()
        return self.get_column_values("name")

    def clean_filter(self):
        """
        Clean the filter textbox
        """
        self.filter.clear()
        time.sleep(1)
        self._wait_for_loadspinner()

    def _get_column_value(self, row, column):
        """
        Get the column from a specific row provided.
        :param row: the webElement of the row
        :param column: the header name of the column
        """
        col = self.elements["col"].copy()
        if column.lower() in self.header_mapping:
            column = self.header_mapping[column.lower()]
        col["select"] = col["select"].format(column=column.lower())
        return row.find_element(*col.values()).text

    def _get_rows(self):
        """
        Get list of rows
        """
        for each_row in self.get_elements("rows"):
            yield each_row

    def _get_row(self, name):
        """
        Get the specified row.
        :param name: row name 
        """
        for each_row in self._get_rows():
            if self._get_column_value(each_row, "name") == name:
                return each_row
        else:
            raise ValueError("{} row not found in table".format(name)) 

    def get_action_values(self, name):
        _row = self._get_row(name)
        _row.find_element(*self.elements["action"].values()).click()
        return [each.text for each in self.get_elements("action_values")]
