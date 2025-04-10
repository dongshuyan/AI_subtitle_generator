import os
import logging
from datetime import datetime

def setup_logger(logger_name="subtitle_generator", log_dir="logs", level=logging.INFO):
    """
    初始化日志记录器，每次运行创建新的日志文件。

    参数：
      - logger_name: 日志记录器名称
      - log_dir: 日志存放文件夹
      - level: 日志级别
    返回：
      - logging.Logger 对象
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"log_{timestamp}.log")

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if not logger.handlers:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    
    return logger
