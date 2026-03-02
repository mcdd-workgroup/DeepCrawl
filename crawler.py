import threading
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
import re

class ZhiLianCrawler:
    def __init__(self, driver, output_file, max_pages=None, max_jobs=None,
                 stop_event=None, callback=None, delay_config=None):
        """
        :param driver: Selenium WebDriver 实例
        :param output_file: Excel 输出路径
        :param max_pages: 最大翻页数（None 表示不限制）
        :param max_jobs: 最大岗位数（None 表示不限制）
        :param stop_event: threading.Event 用于停止爬取
        :param callback: 回调函数，用于更新GUI，接收参数 (page, total_jobs, current_job_title)
        :param delay_config: 延迟配置字典，例如 {'type':'fixed', 'value':2} 或 {'type':'random', 'min':2, 'max':5}
        """
        self.driver = driver
        self.output_file = output_file
        self.max_pages = max_pages
        self.max_jobs = max_jobs
        self.stop_event = stop_event or threading.Event()
        self.callback = callback
        # 默认延迟配置（固定2秒）
        self.delay_config = delay_config or {'type': 'fixed', 'value': 2}
        self.all_jobs = []  # 存储 {'title': , 'job_info': , 'description': }

    def _get_delay(self):
        """根据配置返回本次需要等待的秒数（浮点数）"""
        cfg = self.delay_config
        if cfg.get('type') == 'fixed':
            return cfg.get('value', 2)
        elif cfg.get('type') == 'random':
            min_val = cfg.get('min', 2)
            max_val = cfg.get('max', 5)
            return random.uniform(min_val, max_val)
        else:
            return 2  # 默认

    def _check_stop(self):
        """检查是否收到停止信号"""
        if self.stop_event.is_set():
            print("收到停止信号，爬取终止")
            return True
        return False

    def _update_callback(self, page, total_jobs, current_title=""):
        """调用回调函数（如果存在）"""
        if self.callback:
            self.callback(page, total_jobs, current_title)

    def extract_job_links_from_page(self):
        """从当前搜索页提取所有职位详情页链接"""
        links = []
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.joblist-box__item a.jobinfo__name'))
            )
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, '.joblist-box__item a.jobinfo__name')
            for elem in job_elements:
                href = elem.get_attribute('href')
                if href and '/jobdetail/' in href:
                    links.append(href)
        except Exception as e:
            print(f"提取职位链接失败: {e}")
        return links

    def extract_job_data_from_detail(self, url):
        """
        访问详情页，提取岗位名称、职位信息（所有 li 合并）、职位描述。
        返回字典 {'title': , 'job_info': , 'description': }
        """
        print(f"正在访问详情页: {url}")
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.describtion__detail-content'))
            )
        except Exception as e:
            print(f"详情页描述区域未出现: {e}")
            return None

        soup = BeautifulSoup(self.driver.page_source, 'html.parser')

        # 提取岗位名称
        title_elem = soup.select_one('h1.summary-plane__title')
        title = title_elem.get_text(strip=True) if title_elem else ''

        # 提取整个职位信息块：ul.summary-plane__info 下所有 li 的文本
        job_info_parts = []
        ul_info = soup.select_one('ul.summary-plane__info')
        if ul_info:
            li_list = ul_info.find_all('li')
            for li in li_list:
                text = li.get_text(strip=True)
                if text:
                    job_info_parts.append(text)
        job_info = ' '.join(job_info_parts)

        # 提取职位描述
        desc_elem = soup.select_one('.describtion__detail-content')
        description = desc_elem.get_text(separator='\n').strip() if desc_elem else ''

        return {
            'title': title,
            'job_info': job_info,
            'description': description
        }

    def go_to_next_page(self):
        """尝试点击“下一页”按钮，返回是否成功"""
        try:
            # 多种定位方式
            next_btn = None
            selectors = [
                (By.XPATH, '//a[contains(text(),"下一页")]'),
                (By.CSS_SELECTOR, '.soupager__btn:not(.soupager__btn--disable)'),
                (By.XPATH, '//a[@rel="next"]'),
            ]
            for by, selector in selectors:
                elements = self.driver.find_elements(by, selector)
                for el in elements:
                    if el.is_displayed() and 'disable' not in el.get_attribute('class'):
                        next_btn = el
                        break
                if next_btn:
                    break

            if not next_btn:
                return False

            next_btn.click()
            # 使用配置的延迟等待新页面加载
            time.sleep(self._get_delay())
            return True
        except Exception as e:
            print(f"翻页失败: {e}")
            return False

    def run(self):
        """主爬取逻辑，从当前页面开始"""
        page_num = 1
        total_jobs = 0

        while True:
            if self._check_stop():
                break

            print(f"正在处理第 {page_num} 页")
            self._update_callback(page_num, total_jobs)

            # 获取本页所有职位链接
            job_links = self.extract_job_links_from_page()
            if not job_links:
                print("本页无职位链接，可能已到最后一页")
                break

            # 遍历本页每个职位
            for link in job_links:
                if self._check_stop():
                    break

                job_data = self.extract_job_data_from_detail(link)
                if job_data and job_data['description']:
                    self.all_jobs.append(job_data)
                    total_jobs += 1
                    self._update_callback(page_num, total_jobs, job_data['title'])
                else:
                    print(f"职位 {link} 描述提取失败，跳过")

                # 返回搜索页
                self.driver.back()
                # 使用配置的延迟
                delay = self._get_delay()
                time.sleep(delay)

                # 等待搜索页重新加载
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.joblist-box__item'))
                    )
                except:
                    print("返回搜索页后等待职位列表超时，尝试刷新")
                    self.driver.refresh()
                    time.sleep(delay)

            # 检查是否达到最大岗位数
            if self.max_jobs is not None and total_jobs >= self.max_jobs:
                print(f"已达到最大岗位数 {self.max_jobs}，停止爬取")
                break

            # 检查是否达到最大页数
            if self.max_pages is not None and page_num >= self.max_pages:
                print(f"已达到最大页数 {self.max_pages}，停止翻页")
                break

            # 翻到下一页
            if not self.go_to_next_page():
                print("没有下一页或翻页失败，停止")
                break

            page_num += 1

        # 保存到 Excel
        if self.all_jobs:
            df = pd.DataFrame(self.all_jobs)
            df.columns = ['岗位名称', '职位信息', '职位描述']
            df.to_excel(self.output_file, index=False, engine='openpyxl')
            print(f"数据已保存到: {self.output_file}")
        else:
            print("未获取到任何职位数据")