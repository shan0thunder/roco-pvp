"""爬虫基类与工具函数"""

import time
import random
import logging
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from ..config import REQUEST_CONFIG, DEFAULT_HEADERS


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """爬虫基类，提供通用HTTP请求和解析能力"""

    def __init__(self, source_name: str = "base"):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.last_request_time = 0.0

    def _respect_rate_limit(self):
        """遵守请求频率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_CONFIG["delay_between_requests"]:
            sleep_time = REQUEST_CONFIG["delay_between_requests"] - elapsed
            # 加入随机抖动，避免被反爬
            sleep_time += random.uniform(0, 0.5)
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def fetch_page(
        self,
        url: str,
        params: Optional[Dict] = None,
        encoding: str = "utf-8",
    ) -> Optional[BeautifulSoup]:
        """
        获取页面并返回BeautifulSoup对象。

        Args:
            url: 目标URL
            params: URL查询参数
            encoding: 页面编码

        Returns:
            BeautifulSoup对象或None（失败时）
        """
        self._respect_rate_limit()

        for attempt in range(REQUEST_CONFIG["retries"]):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_CONFIG["timeout"],
                )
                response.raise_for_status()

                # 自动检测编码
                if response.encoding and response.encoding.lower() != "utf-8":
                    response.encoding = encoding

                return BeautifulSoup(response.text, "lxml")

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"请求失败 (尝试 {attempt + 1}/{REQUEST_CONFIG['retries']}): {url} - {e}"
                )
                if attempt < REQUEST_CONFIG["retries"] - 1:
                    time.sleep(REQUEST_CONFIG["retry_delay"] * (attempt + 1))
                else:
                    logger.error(f"最终失败: {url}")
                    return None

    def fetch_json(
        self,
        url: str,
        params: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """获取JSON API响应"""
        self._respect_rate_limit()

        for attempt in range(REQUEST_CONFIG["retries"]):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_CONFIG["timeout"],
                    headers={**DEFAULT_HEADERS, "Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"JSON请求失败 (尝试 {attempt + 1}/{REQUEST_CONFIG['retries']}): {url} - {e}"
                )
                if attempt < REQUEST_CONFIG["retries"] - 1:
                    time.sleep(REQUEST_CONFIG["retry_delay"] * (attempt + 1))
                else:
                    return None

    def clean_text(self, text: Optional[str]) -> str:
        """清理文本：去除多余空格、换行符等"""
        if not text:
            return ""
        return " ".join(text.strip().split())

    def extract_numbers(self, text: str) -> Optional[int]:
        """从文本中提取数字"""
        import re
        numbers = re.findall(r"\d+", text)
        return int(numbers[0]) if numbers else None

    @abstractmethod
    def scrape(self, **kwargs) -> Any:
        """子类必须实现的数据采集方法"""
        pass
