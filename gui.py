import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config
from crawler import ZhiLianCrawler

class CrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("招聘信息爬取软件")
        self.root.geometry("700x700")
        self.root.resizable(False, False)

        self.driver = None
        self.crawler_thread = None
        self.stop_event = threading.Event()
        self.monitor_running = False
        self.stop_monitor = threading.Event()
        self.monitor_thread = None

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 设置图标（可选，需要准备 icon.ico 文件）
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass

    def create_widgets(self):
        # 浏览器控制区域
        browser_frame = ttk.LabelFrame(self.root, text="浏览器控制", padding=10)
        browser_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(browser_frame, text="打开浏览器", command=self.open_browser).pack(side=tk.LEFT, padx=5)
        self.browser_status = ttk.Label(browser_frame, text="浏览器未打开", foreground="red")
        self.browser_status.pack(side=tk.LEFT, padx=20)

        # 参数设置区域
        param_frame = ttk.LabelFrame(self.root, text="爬取参数", padding=10)
        param_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(param_frame, text="最大页数（留空表示不限）:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.max_pages_var = tk.StringVar(value=str(config.DEFAULT_MAX_PAGES))
        ttk.Entry(param_frame, textvariable=self.max_pages_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(param_frame, text="最大岗位数（留空表示不限）:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.max_jobs_var = tk.StringVar()
        ttk.Entry(param_frame, textvariable=self.max_jobs_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(param_frame, text="输出文件:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.output_file_var = tk.StringVar(value=config.DEFAULT_OUTPUT_FILE)
        ttk.Entry(param_frame, textvariable=self.output_file_var, width=50).grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=2)
        ttk.Button(param_frame, text="浏览", command=self.choose_output_file).grid(row=2, column=3, padx=5)

        # 延迟设置区域
        delay_frame = ttk.LabelFrame(self.root, text="延迟设置（秒）", padding=10)
        delay_frame.pack(fill=tk.X, padx=10, pady=5)

        self.delay_type = tk.StringVar(value=config.DEFAULT_DELAY_TYPE)

        fixed_radio = ttk.Radiobutton(delay_frame, text="固定延迟", variable=self.delay_type, value=config.DELAY_TYPE_FIXED)
        fixed_radio.grid(row=0, column=0, sticky=tk.W, pady=2)

        random_radio = ttk.Radiobutton(delay_frame, text="随机延迟", variable=self.delay_type, value=config.DELAY_TYPE_RANDOM)
        random_radio.grid(row=1, column=0, sticky=tk.W, pady=2)

        # 固定延迟输入
        ttk.Label(delay_frame, text="固定值(秒):").grid(row=0, column=1, padx=5, sticky=tk.E)
        self.fixed_delay_var = tk.StringVar(value=str(config.DEFAULT_FIXED_DELAY))
        ttk.Entry(delay_frame, textvariable=self.fixed_delay_var, width=10).grid(row=0, column=2, sticky=tk.W)

        # 随机延迟范围输入
        ttk.Label(delay_frame, text="最小值(秒):").grid(row=1, column=1, padx=5, sticky=tk.E)
        self.random_min_var = tk.StringVar(value=str(config.DEFAULT_RANDOM_MIN))
        ttk.Entry(delay_frame, textvariable=self.random_min_var, width=10).grid(row=1, column=2, sticky=tk.W)

        ttk.Label(delay_frame, text="最大值(秒):").grid(row=1, column=3, padx=5, sticky=tk.E)
        self.random_max_var = tk.StringVar(value=str(config.DEFAULT_RANDOM_MAX))
        ttk.Entry(delay_frame, textvariable=self.random_max_var, width=10).grid(row=1, column=4, sticky=tk.W)

        # 控制按钮
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_btn = ttk.Button(control_frame, text="开始爬取", command=self.start_crawl, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(control_frame, text="停止", command=self.stop_crawl, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # 进度显示
        progress_frame = ttk.LabelFrame(self.root, text="进度", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.progress_text = scrolledtext.ScrolledText(progress_frame, height=15, state=tk.DISABLED)
        self.progress_text.pack(fill=tk.BOTH, expand=True)

        self.page_label = ttk.Label(progress_frame, text="当前页: 0")
        self.page_label.pack(anchor=tk.W)

        self.jobs_label = ttk.Label(progress_frame, text="已获取岗位数: 0")
        self.jobs_label.pack(anchor=tk.W)

    def log(self, message):
        """在日志区域添加信息，同时输出到控制台"""
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state=tk.DISABLED)
        self.root.update()
        print(message)

    def choose_output_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="results.xlsx"
        )
        if filename:
            self.output_file_var.set(filename)

    def _is_browser_alive(self):
        """检查浏览器是否仍然存活，并且至少有一个窗口句柄有效"""
        if not self.driver:
            return False
        try:
            handles = self.driver.window_handles
            return len(handles) > 0
        except:
            return False

    def _monitor_browser(self):
        while not self.stop_monitor.is_set():
            if self.driver and not self._is_browser_alive():
                self.root.after(0, self._on_browser_closed)
                break
            time.sleep(1)

    def _on_browser_closed(self):
        self.driver = None
        self.browser_status.config(text="浏览器未打开", foreground="red")
        self.start_btn.config(state=tk.DISABLED)
        self.log("检测到浏览器已关闭。")
        self.stop_monitor.set()

    def open_browser(self):
        try:
            chrome_options = Options()
            chrome_options.binary_location = config.CHROME_PATH
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

            service = Service(executable_path=config.CHROME_DRIVER_PATH)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })

            self.driver.get("https://www.zhaopin.com")
            self.browser_status.config(text="浏览器已打开", foreground="green")
            self.start_btn.config(state=tk.NORMAL)
            self.log("浏览器已打开，请手动登录并进入搜索结果页，然后点击“开始爬取”。")

            self.stop_monitor.clear()
            self.monitor_thread = threading.Thread(target=self._monitor_browser, daemon=True)
            self.monitor_thread.start()
        except Exception as e:
            messagebox.showerror("错误", f"无法启动浏览器:\n{str(e)}")

    def validate_page(self):
        """验证当前页面是否为有效的搜索结果页（等待职位列表出现）"""
        self.log("执行 validate_page...")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.joblist-box__item'))
            )
            self.log("validate_page 成功：找到职位列表元素")
            return True
        except Exception as e:
            self.log(f"validate_page 失败：{e}")
            return False

    def check_login(self):
        """简单检查是否已登录（通过头像元素）"""
        self.log("执行 check_login...")
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.header-nav__c-login .c-login__top__photo'))
            )
            self.log("check_login 成功：已登录")
            return True
        except:
            self.log("check_login 失败：未检测到登录状态")
            return False

    def start_crawl(self):
        self.log(">>> start_crawl 被调用")

        # 首先检查浏览器对象是否存在
        if not self.driver:
            self.log("浏览器对象不存在")
            messagebox.showerror("错误", "浏览器未打开，请先打开浏览器。")
            return

        # 尝试修复窗口句柄：如果当前窗口无效，自动切换到第一个可用的窗口
        try:
            handles = self.driver.window_handles
            self.log(f"当前窗口句柄数: {len(handles)}")
            if not handles:
                self.log("没有可用的窗口句柄，浏览器可能已关闭")
                self._on_browser_closed()
                messagebox.showerror("错误", "没有可用的浏览器窗口，请重新打开浏览器。")
                return

            # 检查当前窗口是否有效
            try:
                self.driver.title  # 如果当前窗口已关闭，这里会抛出异常
            except:
                self.log("当前窗口已关闭，尝试切换到其他窗口...")
                self.driver.switch_to.window(handles[0])
                self.log(f"已切换到窗口: {handles[0]}")

            # 再次确认当前窗口有效
            self.driver.title
        except Exception as e:
            self.log(f"窗口检查/切换时出错: {e}")
            if not self._is_browser_alive():
                self._on_browser_closed()
            messagebox.showerror("错误", f"浏览器窗口操作失败:\n{str(e)}\n请重新打开浏览器。")
            return

        # 确保浏览器存活
        if not self._is_browser_alive():
            self.log("浏览器已关闭或没有可用窗口")
            messagebox.showerror("错误", "浏览器已关闭或没有可用窗口，请重新打开浏览器。")
            return

        self.log("浏览器存活检查通过")

        try:
            # 记录当前页面信息
            current_title = self.driver.title
            current_url = self.driver.current_url
            self.log(f"当前页面标题: {current_title}")
            self.log(f"当前页面URL: {current_url}")

            # 验证当前页面是否为搜索结果页
            if not self.validate_page():
                self.log("验证失败：不是搜索结果页")
                messagebox.showerror("错误",
                    f"当前页面不是有效的搜索结果页。\n\n"
                    f"页面标题: {current_title}\n"
                    f"URL: {current_url}\n\n"
                    "请确保当前标签页是智联招聘的搜索结果页（例如 https://www.zhaopin.com/sou/...）\n"
                    "且页面已完全加载。")
                return

            self.log("页面验证通过")

            # 检查是否已登录（可选）
            if not self.check_login():
                self.log("警告：未检测到登录状态，但继续执行")

            # 获取参数
            max_pages = self.max_pages_var.get().strip()
            max_pages = int(max_pages) if max_pages else None
            self.log(f"最大页数: {max_pages}")

            max_jobs = self.max_jobs_var.get().strip()
            max_jobs = int(max_jobs) if max_jobs else None
            self.log(f"最大岗位数: {max_jobs}")

            output_file = self.output_file_var.get().strip()
            if not output_file:
                output_file = config.DEFAULT_OUTPUT_FILE
            self.log(f"输出文件: {output_file}")

            # 获取延迟配置
            delay_type = self.delay_type.get()
            if delay_type == config.DELAY_TYPE_FIXED:
                try:
                    fixed_val = float(self.fixed_delay_var.get())
                    if fixed_val < 0:
                        messagebox.showerror("错误", "固定延迟不能为负数")
                        return
                    delay_config = {'type': config.DELAY_TYPE_FIXED, 'value': fixed_val}
                    self.log(f"固定延迟: {fixed_val}秒")
                except ValueError:
                    messagebox.showerror("错误", "固定延迟必须为数字")
                    return
            else:  # random
                try:
                    min_val = float(self.random_min_var.get())
                    max_val = float(self.random_max_var.get())
                    if min_val < 0 or max_val < 0:
                        messagebox.showerror("错误", "延迟不能为负数")
                        return
                    if min_val > max_val:
                        messagebox.showerror("错误", "最小值不能大于最大值")
                        return
                    delay_config = {'type': config.DELAY_TYPE_RANDOM, 'min': min_val, 'max': max_val}
                    self.log(f"随机延迟: {min_val}~{max_val}秒")
                except ValueError:
                    messagebox.showerror("错误", "随机延迟范围必须为数字")
                    return

            self.stop_event.clear()

            # 导入并创建爬虫
            from crawler import ZhiLianCrawler
            crawler = ZhiLianCrawler(
                driver=self.driver,
                output_file=output_file,
                max_pages=max_pages,
                max_jobs=max_jobs,
                stop_event=self.stop_event,
                callback=self.update_progress,
                delay_config=delay_config
            )

            self.log("创建爬虫实例成功，启动线程...")
            self.crawler_thread = threading.Thread(target=crawler.run)
            self.crawler_thread.start()

            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.log("爬取开始...")

            self.check_thread()
            self.log("start_crawl 执行完毕")
        except Exception as e:
            import traceback
            error_msg = f"start_crawl 异常: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            messagebox.showerror("错误", f"程序内部错误:\n{str(e)}")

    def stop_crawl(self):
        self.stop_event.set()
        self.log("正在停止爬取...")

    def check_thread(self):
        if self.crawler_thread and self.crawler_thread.is_alive():
            self.root.after(500, self.check_thread)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.log("爬取已完成或已停止。")

    def update_progress(self, page, total_jobs, current_title=""):
        self.page_label.config(text=f"当前页: {page}")
        self.jobs_label.config(text=f"已获取岗位数: {total_jobs}")
        if current_title:
            self.log(f"已获取: {current_title}")

    def on_closing(self):
        self.stop_monitor.set()
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.destroy()