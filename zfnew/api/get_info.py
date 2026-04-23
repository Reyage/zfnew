# -*- coding: utf-8 -*-
"""
get_info.py - Data-retrieval module for the Zhengfang (正方) educational system.

This module provides the GetInfo class which wraps every read-only API
endpoint of the new-style Zhengfang management system.  Each method
performs one or more HTTP requests (GET or POST) and normalises the
JSON response into a plain Python dict or list so callers do not need
to know the raw field names used by the backend.

Supported operations
---------------------
* :meth:`get_pinfo`    – personal information (name, ID, college, …)
* :meth:`get_notice`   – school-wide announcements
* :meth:`get_message`  – personal inbox messages (e.g. course-change notices)
* :meth:`get_grade`    – academic grades for a given school year and term
* :meth:`get_schedule` – weekly course timetable
* :meth:`get_exam`     – examination schedule

Typical usage::

    from zfnew.api.get_info import GetInfo

    info = GetInfo(base_url='http://jwc.yourschool.edu.cn/', cookies=cookies)
    print(info.get_pinfo())
"""

from bs4 import BeautifulSoup
import re
import time
import requests
from urllib import parse


class GetInfo(object):
    """Retrieves student data from the Zhengfang educational management system.

    Every method uses the cookies obtained from a prior :class:`Login` call, so
    the server treats requests as coming from an authenticated session.

    Args:
        base_url (str): Root URL of the educational management system.
        cookies: Cookie jar (``requests.cookies.RequestsCookieJar``) returned
            by :attr:`Login.cookies` after a successful login.
    """

    def __init__(self, base_url, cookies):
        self.base_url = base_url
        # Minimal headers needed for the API calls; Referer is required by some
        # endpoints to pass the server-side anti-hotlink check.
        self.headers = {
            'Referer': base_url,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36'
        }
        self.cookies = cookies

    def get_pinfo(self):
        """Fetch the authenticated student's personal information.

        Calls the ``/xsxxxggl/xsxxwh_cxCkDgxsxx.html`` endpoint which returns
        a flat JSON object.  The raw Chinese field names (xm, xh, csrq, …) are
        mapped to descriptive English keys.

        Returns:
            dict: A dictionary with keys:
                ``name``, ``studentId``, ``brithday``, ``idNumber``,
                ``candidateNumber``, ``status``, ``collegeName``,
                ``majorName``, ``className``, ``entryDate``,
                ``graduationSchool``, ``domicile``, ``politicalStatus``,
                ``national``, ``education``, ``postalCode``.
        """
        url = parse.urljoin(self.base_url, '/xsxxxggl/xsxxwh_cxCkDgxsxx.html?gnmkdm=N100801')
        res = requests.get(url, headers=self.headers, cookies=self.cookies)
        jres = res.json()
        # Map the backend's abbreviated Chinese field names to readable English keys.
        res_dict = {
            'name': jres['xm'],                  # 姓名 – full name
            'studentId': jres['xh'],              # 学号 – student ID
            'brithday': jres['csrq'],             # 出生日期 – date of birth
            'idNumber': jres['zjhm'],             # 证件号码 – ID card / passport number
            'candidateNumber': jres['ksh'],       # 考生号 – college-entrance exam candidate number
            'status': jres['xjztdm'],             # 学籍状态 – enrolment status code
            'collegeName': jres['zsjg_id'],       # 招生机构 – admitting college/institute
            'majorName': jres['zszyh_id'],        # 招生专业 – major
            'className': jres['bh_id'],           # 班号 – class identifier
            'entryDate': jres['rxrq'],            # 入学日期 – enrolment date
            'graduationSchool': jres['byzx'],     # 毕业中学 – high-school graduated from
            'domicile': jres['hkszd'],            # 户口所在地 – registered domicile
            'politicalStatus': jres['zzmmm'],     # 政治面貌 – political affiliation
            'national': jres['mzm'],              # 民族 – ethnicity
            'education': jres['pyccdm'],          # 培养层次 – degree level (e.g. bachelor)
            'postalCode': jres['yzbm']            # 邮政编码 – postal/zip code
        }
        return res_dict

    def get_notice(self):
        """Fetch the list of school-wide announcements.

        Two announcement-list endpoints are queried in parallel, each
        returning a set of article links.  Each linked article is then
        fetched individually and its title, publisher, timestamp, view
        count, body text, and any attached document URLs are extracted
        with BeautifulSoup.

        Returns:
            list[dict]: Each element represents one notice and contains:
                ``title``, ``publisher``, ``ctime`` (creation time),
                ``vnum`` (view count), ``content`` (full article text),
                ``doc_urls`` (list of attached file URLs).
        """
        # Two separate endpoints that each expose a portion of the news feed.
        url_0 = parse.urljoin(self.base_url, '/xtgl/index_cxNews.html?localeKey=zh_CN&gnmkdm=index')
        url_1 = parse.urljoin(self.base_url, 'xtgl/index_cxAreaTwo.html?localeKey=zh_CN&gnmkdm=index')
        res_list = []
        url_list = []

        # Fetch both listing pages and collect all article-detail links.
        res_0 = requests.get(url_0, headers=self.headers, cookies=self.cookies)
        res_1 = requests.get(url_1, headers=self.headers, cookies=self.cookies)
        soup_0 = BeautifulSoup(res_0.text, 'lxml')
        soup_1 = BeautifulSoup(res_1.text, 'lxml')
        # Select only links whose href starts with '/xtgl/' to avoid picking up
        # navigation links to other system modules.
        url_list += [i['href'] for i in soup_0.select('a[href^="/xtgl/"]')]
        url_list += [i['href'] for i in soup_1.select('a[href^="/xtgl/"]')]

        for u in url_list:
            # Fetch each individual article page.
            _res = requests.get(self.base_url + u, headers=self.headers, cookies=self.cookies)
            _soup = BeautifulSoup(_res.text, 'lxml')

            # The article title is in the element with class 'text-center'.
            title = _soup.find(attrs={'class': 'text-center'}).string

            # The sub-header row contains publisher, publication time, and view count
            # formatted as "Label：Value" spans inside the '.news_title1' container.
            info = [i.string for i in _soup.select_one('[class="text-center news_title1"]').find_all('span')]
            publisher = re.search(r'：(.*)', info[0]).group(1)
            ctime = re.search(r'：(.*)', info[1]).group(1)
            vnum = re.search(r'：(.*)', info[2]).group(1)

            # The article body is inside the element with class 'news_con'.
            detailed = _soup.find(attrs={'class': 'news_con'})
            # Join all text nodes to get the full article text.
            content = ''.join(list(detailed.strings))
            # Collect download links for attached documents; their href starts
            # with '..' (relative) so we strip the leading '..' and prepend
            # the base URL.
            doc_urls = [self.base_url + i['href'][2:] for i in detailed.select('a[href^=".."]')]
            res_list.append({
                'title': title,
                'publisher': publisher,
                'ctime': ctime,
                'vnum': vnum,
                'content': content,
                'doc_urls': doc_urls
            })
        return res_list

    def get_message(self):
        """Fetch personal inbox messages (e.g. course-change notifications).

        Queries the message list endpoint with a POST request and returns up to
        1000 unread/read messages in reverse-chronological order.

        Returns:
            list[dict]: Each element contains:
                ``message`` (message body text) and
                ``ctime`` (creation timestamp string).
        """
        url = parse.urljoin(self.base_url, '/xtgl/index_cxDbsy.html?doType=query')
        data = {
            'sfyy': '0',                        # 是否已阅：0=全部, 1=未阅, 2=已阅
            'flag': '1',
            '_search': 'false',
            'nd': int(time.time()*1000),        # 当前毫秒时间戳，用于防缓存
            'queryModel.showCount': '1000',     # 每次最多返回条数
            'queryModel.currentPage': '1',      # 当前页码（从1开始）
            'queryModel.sortName': 'cjsj',      # 按创建时间排序
            'queryModel.sortOrder': 'desc',     # 时间倒序（最新消息优先）
            'time': '0'                         # 查询计数（首次为0）
        }
        res = requests.post(url, headers=self.headers, data=data, cookies=self.cookies)
        jres = res.json()
        # 'xxnr' = 消息内容 (message content), 'cjsj' = 创建时间 (creation time)
        res_list = [{'message': i['xxnr'], 'ctime': i['cjsj']} for i in jres['items']]
        return res_list

    # def get_elective_list(self):
    #     """获取选课名单信息"""
    #     pass
    #
    # def get_expriment_grade(self):
    #     """获取实验成绩信息"""
    #     pass

    def get_grade(self, year, term):
        """Fetch academic grades for a given school year and term.

        The backend uses a non-obvious term encoding:
        ``'1'`` (first semester) maps to ``'3'``, ``'2'`` (second semester)
        maps to ``'12'``, and ``'0'`` (full year) maps to ``''``.

        Args:
            year (str): Four-digit starting year of the academic year,
                e.g. ``'2019'`` for the 2019–2020 school year.
            term (str): Term selector – ``'1'`` for the first term,
                ``'2'`` for the second term, ``'0'`` for the full year.

        Returns:
            dict: When results are available, contains:
                ``name``, ``studentId``, ``schoolYear``, ``schoolTerm``,
                and a ``course`` list where each entry holds
                ``courseTitle``, ``teacher``, ``courseId``, ``className``,
                ``courseNature``, ``credit``, ``grade``, ``gradePoint``,
                ``gradeNature``, ``startCollege``, ``courseMark``,
                ``courseCategory``, ``courseAttribution``.

                Returns ``{}`` when no grade data exists for the given period.
        """
        url = parse.urljoin(self.base_url, '/cjcx/cjcx_cxDgXscj.html?doType=query&gnmkdm=N305005')
        # Translate the user-facing term number to the value expected by the API.
        if term == '1':      # 第一学期 – first semester
            term = '3'
        elif term == '2':    # 第二学期 – second semester
            term = '12'
        elif term == '0':    # 全学年 – entire academic year (empty string means "all terms")
            term = ''
        else:
            print('Please enter the correct term value！！！ ("0" or "1" or "2")')
            return {}
        data = {
            'xnm': year,                        # 学年数 – academic year (e.g. '2019')
            'xqm': term,                        # 学期数 – term code ('3', '12', or '')
            '_search': 'false',
            'nd': int(time.time()*1000),        # 当前毫秒时间戳
            'queryModel.showCount': '100',      # 每页最多条数
            'queryModel.currentPage': '1',
            'queryModel.sortName': '',
            'queryModel.sortOrder': 'asc',
            'time': '0'                         # 查询次数
        }
        res = requests.post(url, headers=self.headers, data=data, cookies=self.cookies)
        jres = res.json()
        if jres.get('items'):  # Guard against an empty 'items' list in the response.
            res_dict = {
                'name': jres['items'][0]['xm'],          # 姓名
                'studentId': jres['items'][0]['xh'],     # 学号
                'schoolYear': jres['items'][0]['xnm'],   # 学年
                'schoolTerm': jres['items'][0]['xqmmc'], # 学期名称
                'course': [{
                    'courseTitle': i['kcmc'],            # 课程名称
                    'teacher': i['jsxm'],                # 教师姓名
                    'courseId': i['kch_id'],             # 课程号
                    'className': i['jxbmc'],             # 教学班名称
                    'courseNature': i.get('kcxzmc', ''),  # 课程性质
                    'credit': i['xf'],                   # 学分
                    'grade': i['cj'],                    # 成绩
                    'gradePoint': i.get('jd', ''),           # 绩点
                    'gradeNature': i['ksxz'],            # 考试性质
                    'startCollege': i['kkbmmc'],         # 开课部门名称
                    'courseMark': i['kcbj'],             # 课程标记
                    'courseCategory': i['kclbmc'],       # 课程类别名称
                    'courseAttribution': i.get('kcgsmc', '')  # 课程归属
                } for i in jres['items']]}
            return res_dict
        else:
            return {}

    def get_schedule(self, year, term):
        """Fetch the weekly course timetable for a given school year and term.

        Returns two categories of courses:
        * ``normalCourse`` – regular classroom-scheduled courses.
        * ``otherCourses`` – supplementary or elective course descriptions
          stored as free-text strings in the ``sjkList`` array.

        Args:
            year (str): Four-digit starting year of the academic year.
            term (str): ``'1'`` for the first semester, ``'2'`` for the second.

        Returns:
            dict: Contains ``name``, ``studentId``, ``schoolYear``,
            ``schoolTerm``, ``normalCourse`` (list of course dicts), and
            ``otherCourses`` (list of strings).  Returns ``{}`` for invalid
            *term* values.

        Note:
            Each entry in ``normalCourse`` includes scheduling fields:
            ``courseSection`` (节次/period numbers), ``courseWeek``
            (周次/week mask string), ``campus``, ``courseRoom``, etc.
        """
        url = parse.urljoin(self.base_url, '/kbcx/xskbcx_cxXsKb.html?gnmkdm=N2151')
        # Translate term number to the API's internal encoding.
        if term == '1':      # 第一学期
            term = '3'
        elif term == '2':    # 第二学期
            term = '12'
        else:
            print('Please enter the correct term value！！！ ("1" or "2")')
            return {}
        data = {
            'xnm': year,   # 学年
            'xqm': term    # 学期
        }
        res = requests.post(url, headers=self.headers, data=data, cookies=self.cookies)
        jres = res.json()
        res_dict = {
            'name': jres['xsxx']['XM'],              # 姓名
            'studentId': jres['xsxx']['XH'],         # 学号
            'schoolYear': jres['xsxx']['XNM'],       # 学年
            'schoolTerm': jres['xsxx']['XQMMC'],     # 学期名称
            # 'kbList' contains the regular scheduled courses.
            'normalCourse': [{
                'courseTitle': i['kcmc'],            # 课程名称
                'teacher': i['xm'],                  # 教师姓名
                'courseId': i['kch_id'],             # 课程号
                'courseSection': i['jc'],            # 节次（第几节课）
                'courseWeek': i['zcd'],              # 周次（哪几周上课）
                'campus': i['xqmc'],                 # 校区名称
                'courseRoom': i['cdmc'],             # 上课地点
                'className': i['jxbmc'],             # 教学班名称
                'hoursComposition': i['kcxszc'],     # 课时组成
                'weeklyHours': i['zhxs'],            # 周学时
                'totalHours': i['zxs'],              # 总学时
                'credit': i['xf']                    # 学分
            } for i in jres['kbList']],
            # 'sjkList' contains free-form descriptions of other (non-standard) courses.
            'otherCourses': [i['qtkcgs'] for i in jres['sjkList']]
        }
        return res_dict

    # def get_classroom(self):
    #     """获取空教室信息"""
    #     url = parse.urljoin(self.base_url, '/cdjy/cdjy_cxKxcdlb.html?gnmkdm=N2155&layout=default')
    #     data = {
    #         'fwzt': 'cx',
    #         'xqh_id': '1',
    #         'xnm': '2019',
    #         'xqm': '3',
    #         'cdlb_id': '',
    #         'cdejlb_id': '',
    #         'qszws': '',
    #         'jszws': '',
    #         'cdmc': '',
    #         'lh': '',
    #         'qssd': '',
    #         'jssd': '',
    #         'qssj': '',
    #         'jssj': '',
    #         'jyfs': '0',
    #         'cdjylx': '',
    #         'zcd': '256',
    #         'xqj': '3',
    #         'jcd': '9',
    #         '_search': 'false',
    #         'nd': '1571744696313',
    #         'queryModel.showCount': '50',  # 最多条数
    #         'queryModel.currentPage': '1',
    #         'queryModel.sortName': 'cdbh',
    #         'queryModel.sortOrder': 'asc',
    #         'time': '1'
    #     }
    #     res = requests.post(url, headers=self.headers, data=data, cookies=self.cookies)
    #     return res

    def get_exam(self, year, term):
        """Fetch the examination schedule for a given school year and term.

        Args:
            year (str): Four-digit starting year of the academic year.
            term (str): ``'1'`` for the first semester, ``'2'`` for the second.

        Returns:
            dict: When exams are scheduled, contains ``name``, ``studentId``,
            ``schoolYear``, ``schoolTerm``, and an ``exams`` list where each
            entry holds ``courseTitle``, ``teacher``, ``courseId``,
            ``reworkMark``, ``selfeditingMark``, ``examName``, ``paperId``,
            ``examTime``, ``eaxmLocation``, ``campus``, ``examSeatNumber``.

            Returns ``{}`` when no exam data exists for the given period.
        """
        url = parse.urljoin(self.base_url, '/kwgl/kscx_cxXsksxxIndex.html?doType=query&gnmkdm=N358105')
        # Translate term number to the API's internal encoding.
        if term == '1':      # 第一学期
            term = '3'
        elif term == '2':    # 第二学期
            term = '12'
        else:
            print('Please enter the correct term value！！！ ("1" or "2")')
            return {}
        data = {
            'xnm': year,                        # 学年数
            'xqm': term,                        # 学期数（第一学期=3，第二学期=12）
            '_search': 'false',
            'nd': int(time.time() * 1000),      # 当前毫秒时间戳
            'queryModel.showCount': '100',      # 每页最多条数
            'queryModel.currentPage': '1',
            'queryModel.sortName': '',
            'queryModel.sortOrder': 'asc',
            'time': '0'                         # 查询次数
        }
        res = requests.post(url, headers=self.headers, data=data, cookies=self.cookies)
        jres = res.json()
        if jres.get('items'):  # Guard against an empty response.
            res_dict = {
                'name': jres['items'][0]['xm'],                  # 姓名
                'studentId': jres['items'][0]['xh'],             # 学号
                'schoolYear': jres['items'][0]['xnmc'][:4],     # 学年（取前4字符，如"2019"）
                'schoolTerm': jres['items'][0]['xqmmc'],         # 学期名称
                'exams': [{
                    'courseTitle': i['kcmc'],      # 课程名称
                    'teacher': i['jsxx'],          # 教师信息
                    'courseId': i['kch'],          # 课程号
                    'reworkMark': i['cxbj'],       # 重修标记
                    'selfeditingMark': i['zxbj'],  # 自学标记
                    'examName': i['ksmc'],         # 考试名称
                    'paperId': i['sjbh'],          # 试卷编号
                    'examTime': i['kssj'],         # 考试时间
                    'eaxmLocation': i['cdmc'],     # 考试地点
                    'campus': i['xqmc'],           # 校区名称
                    'examSeatNumber': i['zwh']     # 座位号
                } for i in jres['items']]}
            return res_dict
        else:
            return {}
