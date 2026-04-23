# -*- coding: utf-8 -*-
"""
choose.py - Selenium-based course-selection helper (prototype / legacy).

.. warning::
    This module relies on the **old** Zhengfang system's Selenium-driven
    interface and is not compatible with the new-style JSON API used by
    the rest of the package.  It is kept here for reference only and is
    **not** imported by the package's public API (``zfnew/api/__init__.py``).

The function below demonstrates how course selection was automated using
a web browser controlled by Selenium WebDriver.  It opens a second tab,
navigates to the course-selection page, and attempts to click through the
UI to enrol in a specific course identified by a hard-coded student ID.
"""


def choose_course(browser):
    """Attempt to auto-select a course using a Selenium WebDriver instance.

    .. deprecated::
        This function targets the old-style (ASP.NET) Zhengfang front end
        and will not work with the new Vue/JSON-based system.

    Algorithm overview:
      1. Open a new browser tab and navigate to the course-selection page.
      2. Click the "快速选课" (quick course enrolment) button.
      3. Click the "校公选课" (school-wide elective) category button.
      4. Switch to the newly opened window and select the first available
         list-box item, then confirm.
      5. Return to the selection window and iterate over all course-group
         links in the table row for period 12 (row index 12 in the grid).
      6. For each group, look for a class with ID ``'151188019'``; if found,
         click it and stop.

    Args:
        browser: A Selenium ``WebDriver`` instance that is already logged in
            to the educational management system.

    Note:
        The XPath selectors and hard-coded student ID (``'151188019'``) in
        this function are specific to a single user's setup and will need to
        be changed before this function is useful for anyone else.
    """
    # Open a new browser tab and switch focus to it.
    browser.execute_script('window.open()')
    browser.switch_to_window(browser.window_handles[1])

    # Navigate to the course-selection page for the specific student.
    # The URL encodes the student's ID (xh) and name (xm) directly.
    browser.get('http://jwc.xhu.edu.cn/xsxk.aspx?xh=3120170807112&xm=%C1%CE%CE%C4%BA%C0&gnmkdm=N121101')

    # Click the "快速选课" (Quick Course Selection) link at the top of the page.
    browser.find_element_by_xpath('/html/body/h2/a').click()

    # Click the "校公选课" (School-wide Elective) button to switch to that category.
    browser.find_element_by_xpath('//*[@id="Button2"]').click()

    # The previous click opens a third window for the school-wide elective list.
    browser.find_element_by_xpath('//*[@id="Button2"]').click()
    browser.switch_to_window(browser.window_handles[2])

    # Select the first item in the elective list-box and confirm the selection.
    browser.find_element_by_xpath('//*[@id="ListBox1"]/option').click()
    browser.find_element_by_xpath('//*[@id="Button1"]').click()

    # Switch back to the course-selection window (index 1).
    browser.switch_to_window(browser.window_handles[1])

    # Count how many course-group links exist inside row 12 of the course grid.
    # (The XPath length() function is not used here; instead the raw XPath
    # string is inspected – this is a known limitation of this prototype code.)
    n = len('//*[@id="kcmcgrid"]/tbody/tr[12]/td/b/*')
    index = False

    # Iterate over each course-group link (starting at index 2 because index 1
    # is the group header, not a selectable class).
    for i in range(2, n + 1):
        browser.find_element_by_xpath(
            '//*[@id="kcmcgrid"]/tbody/tr[12]/td/b/a[' + str(i) + ']'
        ).click()

        # After clicking the group link, the class list is populated.
        # Look for the target class by its ID number.
        for son in browser.find_elements_by_xpath('//*[@id="kcmcgrid"]/tbody/tr/td[1]/a'):
            if son.text == '151188019':
                son.click()      # Enrol in the found class.
                index = True
                break

        # Exit the outer loop as soon as the target class has been enrolled in.
        while index:
            break
