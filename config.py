import os

# 默认浏览器和驱动路径（与exe同目录下的 chrome-win64 文件夹）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROME_PATH = os.path.join(BASE_DIR, "chrome-win64", "chrome.exe")
CHROME_DRIVER_PATH = os.path.join(BASE_DIR, "chromedriver.exe")

# 默认输出文件
DEFAULT_OUTPUT_FILE = os.path.join(BASE_DIR, "results.xlsx")

# 默认最大翻页数
DEFAULT_MAX_PAGES = 60

# 反爬延迟设置
DELAY_TYPE_FIXED = "fixed"
DELAY_TYPE_RANDOM = "random"
DEFAULT_DELAY_TYPE = DELAY_TYPE_FIXED
DEFAULT_FIXED_DELAY = 2
DEFAULT_RANDOM_MIN = 2
DEFAULT_RANDOM_MAX = 5