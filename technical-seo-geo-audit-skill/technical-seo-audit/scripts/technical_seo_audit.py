#!/usr/bin/env python3
"""Technical SEO audit helper for Manus skills.

This script performs deterministic, fetch-only checks for one website or many websites.
It does not log in, submit forms, call paid APIs, or execute remote code. It is intended
for scalable first-pass technical SEO screening; use Search Console, PageSpeed Insights,
and manual review for items that require private or field data.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import traceback
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; ManusTechnicalSEOAudit/1.0; +https://manus.im; "
    "fetch-only SEO diagnostics)"
)
AI_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot", "ChatGPT-User"]
SCHEMA_RECOMMENDED = {
    "Organization", "WebSite", "WebPage", "BreadcrumbList", "Product",
    "SoftwareApplication", "Article", "BlogPosting", "FAQPage", "HowTo", "VideoObject",
}
SECURITY_HEADERS = {
    "strict-transport-security": "启用 HSTS，强制 HTTPS。",
    "content-security-policy": "配置 CSP，降低 XSS 与数据注入风险。",
    "x-content-type-options": "设置 X-Content-Type-Options: nosniff。",
    "referrer-policy": "设置 Referrer-Policy，控制来源信息泄露。",
}


@dataclass
class Issue:
    site: str
    page: str
    category: str
    check: str
    severity: str
    evidence: str
    recommendation: str


@dataclass
class PageSummary:
    site: str
    url: str
    status_code: Optional[int]
    final_url: str
    response_ms: Optional[int]
    title: str = ""
    title_len: int = 0
    description_len: int = 0
    description: str = ""
    h1_count: int = 0
    lang: str = ""
    canonical: str = ""
    meta_robots: str = ""
    x_robots_tag: str = ""
    noindex: bool = False
    viewport: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    image_count: int = 0
    missing_alt_count: int = 0
    schema_types: str = ""
    hreflang_count: int = 0
    internal_links: int = 0
    word_count: int = 0
    trust_link_hits: str = ""


@dataclass
class SiteResult:
    site: str
    started_at: str
    pages: List[PageSummary] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return raw
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parsed = urllib.parse.urlparse(raw)
    if not parsed.netloc:
        return raw
    return urllib.parse.urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", "", parsed.query, ""))


def origin(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def same_host(a: str, b: str) -> bool:
    return urllib.parse.urlparse(a).netloc.lower() == urllib.parse.urlparse(b).netloc.lower()


def clean_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def add_issue(result: SiteResult, page: str, category: str, check: str, severity: str, evidence: str, recommendation: str) -> None:
    result.issues.append(Issue(result.site, page, category, check, severity, clean_text(evidence)[:600], recommendation))


def fetch(session: requests.Session, url: str, timeout: int) -> Tuple[Optional[requests.Response], Optional[str], Optional[int]]:
    start = time.perf_counter()
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return resp, None, elapsed_ms
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return None, f"{type(exc).__name__}: {exc}", elapsed_ms


def parse_jsonld_types(obj: Any) -> List[str]:
    found: List[str] = []
    if isinstance(obj, dict):
        typ = obj.get("@type")
        if isinstance(typ, str):
            found.append(typ)
        elif isinstance(typ, list):
            found.extend(str(x) for x in typ)
        for value in obj.values():
            found.extend(parse_jsonld_types(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(parse_jsonld_types(item))
    return found


def extract_schema_types(soup: BeautifulSoup) -> List[str]:
    types: List[str] = []
    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        raw = script.string or script.get_text(" ")
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
            types.extend(parse_jsonld_types(data))
        except Exception:
            types.append("INVALID_JSON_LD")
    for tag in soup.find_all(attrs={"itemtype": True}):
        value = tag.get("itemtype", "")
        if value:
            types.append(value.rstrip("/").split("/")[-1])
    return sorted(set(t for t in types if t))


def get_meta_content(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": re.compile(f"^{re.escape(name)}$", re.I)})
    return clean_text(tag.get("content")) if tag and tag.get("content") else ""


def get_meta_property(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", attrs={"property": re.compile(f"^{re.escape(prop)}$", re.I)})
    return clean_text(tag.get("content")) if tag and tag.get("content") else ""


def get_meta_name_or_property(soup: BeautifulSoup, key: str) -> str:
    value = get_meta_content(soup, key)
    if value:
        return value
    return get_meta_property(soup, key)


def rel_contains(value: Any, token: str) -> bool:
    if isinstance(value, list):
        return token.lower() in [str(x).lower() for x in value]
    return token.lower() in str(value or "").lower().split()


def classify_trust_link(text: str, href: str) -> Optional[str]:
    haystack = f"{text} {href}".lower()
    patterns = {
        "privacy": r"privacy|隐私|私隱|個人情報|datenschutz",
        "terms": r"terms|tos|conditions|条款|條款|利用規約",
        "contact": r"contact|support|help|联系|聯絡|联系我们|聯繫我們",
        "about": r"about|company|team|关于|關於|公司|团队|團隊",
    }
    for label, pattern in patterns.items():
        if re.search(pattern, haystack, re.I):
            return label
    return None


def visible_word_count(soup: BeautifulSoup) -> int:
    for bad in soup(["script", "style", "noscript", "template"]):
        bad.extract()
    text = clean_text(soup.get_text(" "))
    if re.search(r"[\u4e00-\u9fff]", text):
        zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        latin_words = len(re.findall(r"\b[a-zA-Z][a-zA-Z0-9'-]*\b", text))
        return zh_chars + latin_words
    return len(re.findall(r"\b\w+\b", text))


def normalize_for_compare(url: str) -> str:
    p = urllib.parse.urlparse(url)
    path = p.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urllib.parse.urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", p.query, ""))


def analyze_page(result: SiteResult, session: requests.Session, url: str, timeout: int, base_origin: str) -> Tuple[Optional[PageSummary], List[str]]:
    resp, err, elapsed = fetch(session, url, timeout)
    if err or resp is None:
        add_issue(result, url, "抓取与可访问性", "页面无法访问", "P0", err or "请求失败", "检查 DNS、TLS、服务器防火墙与超时配置，确保搜索引擎可访问。")
        return None, []

    final_url = resp.url
    content_type = resp.headers.get("content-type", "")
    status = resp.status_code
    if status >= 400:
        add_issue(result, url, "抓取与可访问性", "页面返回错误状态码", "P0" if status >= 500 else "P1", f"HTTP {status}", "修复服务器错误、失效链接或错误的路由配置。")
    if len(resp.history) > 2:
        add_issue(result, final_url, "URL 规范化", "重定向链过长", "P2", f"重定向次数 {len(resp.history)}", "将旧 URL 直接 301 到最终规范 URL，减少抓取浪费和延迟。")
    if elapsed and elapsed > 1500:
        add_issue(result, final_url, "性能", "HTML 响应较慢", "P2", f"首个 HTML 响应约 {elapsed}ms", "优化服务器响应时间、缓存、CDN 与后端渲染路径。")

    if "html" not in content_type.lower():
        summary = PageSummary(result.site, url, status, final_url, elapsed)
        return summary, []

    soup = BeautifulSoup(resp.text, "html.parser")
    links: List[str] = []
    trust_hits: Set[str] = set()
    for a in soup.find_all("a", href=True):
        raw_href = a.get("href")
        href = urllib.parse.urljoin(final_url, raw_href)
        href = urllib.parse.urldefrag(href)[0]
        trust_label = classify_trust_link(clean_text(a.get_text(" ")), raw_href or href)
        if trust_label:
            trust_hits.add(trust_label)
        if href.startswith(base_origin) or same_host(href, base_origin):
            links.append(href)

    title = clean_text(soup.title.string if soup.title and soup.title.string else "")
    desc = get_meta_content(soup, "description")
    keywords = get_meta_content(soup, "keywords")
    robots_meta = get_meta_content(soup, "robots").lower()
    xrobots = resp.headers.get("x-robots-tag", "").lower()
    noindex = "noindex" in robots_meta or "noindex" in xrobots
    canonical_tags = soup.find_all("link", attrs={"rel": lambda v: rel_contains(v, "canonical")})
    canonical_tag = canonical_tags[0] if canonical_tags else None
    canonical = urllib.parse.urljoin(final_url, canonical_tag.get("href", "").strip()) if canonical_tag and canonical_tag.get("href") else ""
    html = soup.find("html")
    lang = html.get("lang", "").strip() if html else ""
    h_tags = [(int(tag.name[1]), clean_text(tag.get_text(" "))) for tag in soup.find_all(re.compile(r"^h[1-6]$", re.I))]
    h1_count = sum(1 for level, _ in h_tags if level == 1)
    imgs = soup.find_all("img")
    missing_alt = [img for img in imgs if img.get("alt") is None]
    hreflangs = soup.find_all("link", attrs={"rel": lambda v: rel_contains(v, "alternate"), "hreflang": True})
    schema_types = extract_schema_types(soup)
    wc = visible_word_count(BeautifulSoup(resp.text, "html.parser"))
    viewport = get_meta_content(soup, "viewport")
    og_title = get_meta_property(soup, "og:title")
    og_description = get_meta_property(soup, "og:description")
    og_image = get_meta_property(soup, "og:image")

    summary = PageSummary(
        site=result.site,
        url=url,
        status_code=status,
        final_url=final_url,
        response_ms=elapsed,
        title=title,
        title_len=len(title),
        description_len=len(desc),
        description=desc,
        h1_count=h1_count,
        lang=lang,
        canonical=canonical,
        meta_robots=robots_meta,
        x_robots_tag=xrobots,
        noindex=noindex,
        viewport=viewport,
        og_title=og_title,
        og_description=og_description,
        og_image=og_image,
        image_count=len(imgs),
        missing_alt_count=len(missing_alt),
        schema_types=", ".join(schema_types),
        hreflang_count=len(hreflangs),
        internal_links=len(set(links)),
        word_count=wc,
        trust_link_hits=", ".join(sorted(trust_hits)),
    )

    if not title:
        add_issue(result, final_url, "源代码标签", "缺少 title", "P1", "未找到 <title>", "为每个可索引页面添加唯一、描述性 title。")
    elif len(title) < 15 or len(title) > 65:
        add_issue(result, final_url, "源代码标签", "title 长度异常", "P2", f"长度 {len(title)}，内容：{title}", "将 title 控制在可读且不易截断的范围，通常约 50–60 个英文字符或相近显示宽度。")
    if not desc:
        add_issue(result, final_url, "源代码标签", "缺少 meta description", "P2", "未找到 meta description", "为重要页面添加唯一、自然、有点击吸引力的描述。")
    elif len(desc) > 170 or len(desc) < 50:
        add_issue(result, final_url, "源代码标签", "meta description 长度异常", "P3", f"长度 {len(desc)}", "保持描述简洁完整，避免过短或被搜索结果截断。")
    if keywords and len(keywords) > 160:
        add_issue(result, final_url, "源代码标签", "meta keywords 冗长", "P3", f"长度 {len(keywords)}", "该标签对现代搜索排名价值很低，如保留应保持简洁，避免关键词堆砌。")
    if not canonical:
        add_issue(result, final_url, "URL 规范化", "缺少 canonical", "P2", "未找到 rel=canonical", "为重要可索引页面设置自引用或指向首选版本的 canonical。")
    elif len(canonical_tags) > 1:
        add_issue(result, final_url, "URL 规范化", "存在多个 canonical", "P1", f"canonical 数量 {len(canonical_tags)}", "每个页面只保留一个明确 canonical，避免规范化信号冲突。")
    elif not canonical.lower().startswith("http"):
        add_issue(result, final_url, "URL 规范化", "canonical 不是绝对 URL", "P2", canonical, "使用完整绝对 URL，避免环境或路径解析错误。")
    elif normalize_for_compare(canonical) != normalize_for_compare(final_url) and not noindex:
        add_issue(result, final_url, "URL 规范化", "canonical 指向非自身 URL", "P3", f"canonical={canonical}", "确认该页面是否确实为重复页；若不是，应改为自引用 canonical。")
    if not viewport:
        add_issue(result, final_url, "移动端与渲染", "缺少 viewport", "P2", "未找到 meta viewport", "为响应式页面添加合理 viewport，例如 width=device-width, initial-scale=1。")
    if h1_count == 0:
        add_issue(result, final_url, "内容结构", "缺少 H1", "P2", "未找到 H1", "每个核心页面应有一个清晰 H1，反映页面主要主题。")
    elif h1_count > 1:
        add_issue(result, final_url, "内容结构", "多个 H1", "P2", f"H1 数量 {h1_count}", "通常保留一个主 H1，其余主视觉标题改为 H2 或普通文本。")
    last_level = 0
    for level, text in h_tags:
        if last_level and level - last_level > 1:
            add_issue(result, final_url, "内容结构", "标题层级跳跃", "P3", f"从 H{last_level} 跳到 H{level}: {text[:80]}", "按 H1 > H2 > H3 的逻辑组织内容，帮助搜索引擎和用户理解结构。")
            break
        last_level = level
    if imgs and len(missing_alt) / max(len(imgs), 1) > 0.25:
        add_issue(result, final_url, "图片 SEO", "图片 alt 缺失比例高", "P2", f"{len(missing_alt)}/{len(imgs)} 张图片缺少 alt", "为传达信息的图片添加描述性 alt；装饰性图片可使用空 alt。")
    if not lang:
        add_issue(result, final_url, "国际化", "缺少 html lang", "P2", "<html> 未声明 lang", "在 html 标签中声明页面主要语言，例如 en、zh-CN。")
    if noindex:
        add_issue(result, final_url, "索引控制", "页面被 noindex", "P1", f"robots meta={robots_meta}; x-robots-tag={xrobots}", "确认该页面是否应被索引；如为核心页面，移除 noindex。")
    if "INVALID_JSON_LD" in schema_types:
        add_issue(result, final_url, "结构化数据", "JSON-LD 无法解析", "P1", "存在无效 JSON-LD", "修复 JSON-LD 语法，并用 Rich Results Test 或 Schema Markup Validator 验证。")
    if not schema_types and wc > 300:
        add_issue(result, final_url, "结构化数据", "缺少结构化数据", "P2", "未发现 JSON-LD/Microdata", "根据页面类型添加 Organization、WebSite、BreadcrumbList、Article、Product、FAQPage、HowTo 等。")
    if len(hreflangs) > 0:
        bad = [x for x in hreflangs if not x.get("href", "").startswith("http")]
        if bad:
            add_issue(result, final_url, "国际化", "hreflang URL 非绝对地址", "P2", f"发现 {len(bad)} 个相对 hreflang", "hreflang href 应使用完整 URL，并确保双向互链。")
    if (og_title == "" or og_description == "" or og_image == "") and (wc > 300 or "Article" in schema_types or "BlogPosting" in schema_types):
        missing_og = [name for name, value in [("og:title", og_title), ("og:description", og_description), ("og:image", og_image)] if not value]
        add_issue(result, final_url, "内容展示", "Open Graph 信息不完整", "P3", f"缺少 {', '.join(missing_og)}", "为核心落地页和内容页配置 Open Graph title、description、image，提升分享和预览质量。")
    if og_image == "" and ("Article" in schema_types or "BlogPosting" in schema_types):
        add_issue(result, final_url, "内容展示", "文章缺少 og:image", "P3", "未发现 og:image", "为文章页配置代表性分享图，有助于社交平台与搜索预览。")
    if wc < 120 and status == 200 and not noindex:
        add_issue(result, final_url, "内容质量/索引风险", "可索引页面正文过少", "P3", f"估算词/字数 {wc}", "人工确认该页面是否为薄内容、路由壳页面或 JS 渲染依赖页面。")
    if wc > 900:
        text = soup.get_text("\n")
        if not re.search(r"TL;?DR|Too long;? didn't read|摘要|要点", text, re.I):
            add_issue(result, final_url, "GEO/AI 可读性", "长内容缺少 TL;DR 或摘要", "P3", f"估算词/字数 {wc}", "在长文开头加入 2–3 句摘要，便于 AI 与用户快速理解。")
        if not re.search(r"last\s*updated|updated on|最近更新|最后更新|更新日期", text, re.I):
            add_issue(result, final_url, "GEO/内容新鲜度", "长内容缺少更新时间", "P3", f"估算词/字数 {wc}", "为核心长内容显式标注 Last Updated 或最近更新日期。")
    return summary, links


def analyze_robots(result: SiteResult, session: requests.Session, site_origin: str, timeout: int) -> List[str]:
    url = site_origin.rstrip("/") + "/robots.txt"
    resp, err, _ = fetch(session, url, timeout)
    sitemaps: List[str] = []
    if err or resp is None:
        add_issue(result, url, "核心技术文件", "robots.txt 无法访问", "P1", err or "请求失败", "在根目录提供 robots.txt，至少不要误封核心页面，并声明 Sitemap。")
        return sitemaps
    if resp.status_code == 404:
        add_issue(result, url, "核心技术文件", "缺少 robots.txt", "P2", "HTTP 404", "建议添加 robots.txt，明确抓取策略与 Sitemap 地址。")
        return sitemaps
    if resp.status_code >= 400:
        add_issue(result, url, "核心技术文件", "robots.txt 返回错误", "P1", f"HTTP {resp.status_code}", "确保 robots.txt 可被搜索引擎稳定访问。")
        return sitemaps
    text = resp.text
    result.meta["robots_txt_url"] = url
    if not resp.encoding or resp.encoding.lower() not in {"utf-8", "ascii"}:
        add_issue(result, url, "核心技术文件", "robots.txt 编码不明确", "P3", f"encoding={resp.encoding}", "使用 UTF-8 编码并保持每条规则独占一行。")
    for line in text.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemaps.append(line.split(":", 1)[1].strip())
    if not sitemaps:
        add_issue(result, url, "核心技术文件", "robots.txt 未声明 Sitemap", "P2", "未发现 Sitemap: 指令", "在 robots.txt 中加入完整 Sitemap URL。")
    if re.search(r"(?im)^\s*user-agent\s*:\s*\*\s*$[\s\S]{0,200}?^\s*disallow\s*:\s*/\s*$", text):
        add_issue(result, url, "核心技术文件", "robots.txt 可能全站禁止抓取", "P0", "User-agent: * + Disallow: /", "立即确认是否误封生产站核心页面。")
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(url)
    try:
        rp.parse(text.splitlines())
        for bot in ["Googlebot", "Googlebot-Image", "Bingbot", "*"]:
            if not rp.can_fetch(bot, site_origin.rstrip("/") + "/"):
                sev = "P0" if bot in {"Googlebot", "*"} else "P1"
                add_issue(result, url, "核心技术文件", f"robots.txt 阻止 {bot} 抓取首页", sev, f"{bot} cannot fetch /", "确认生产站首页和核心模板没有被 robots.txt 误封。")
    except Exception as exc:  # noqa: BLE001
        add_issue(result, url, "核心技术文件", "robots.txt 解析异常", "P2", f"{type(exc).__name__}: {exc}", "检查 robots.txt 语法，确保规则能被主流爬虫正确解析。")
    missing_ai = [bot for bot in AI_BOTS if not re.search(rf"(?im)^\s*user-agent\s*:\s*{re.escape(bot)}\s*$", text)]
    if len(missing_ai) == len(AI_BOTS):
        add_issue(result, url, "GEO/AI 爬虫", "未显式声明 AI 爬虫策略", "P3", "未发现 GPTBot/ClaudeBot/PerplexityBot 等 User-agent", "按品牌策略显式允许或限制 AI 爬虫，避免策略不透明。")
    return sitemaps


def parse_sitemap_urls(xml_text: str) -> Tuple[List[str], bool]:
    urls: List[str] = []
    is_index = False
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except Exception:
        return urls, is_index
    tag = root.tag.split("}")[-1].lower()
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if tag == "sitemapindex":
        is_index = True
        for loc in root.findall(f".//{ns}loc"):
            if loc.text:
                urls.append(loc.text.strip())
    else:
        for loc in root.findall(f".//{ns}loc"):
            if loc.text:
                urls.append(loc.text.strip())
    return urls, is_index


def analyze_sitemaps(result: SiteResult, session: requests.Session, site_origin: str, sitemap_urls: List[str], timeout: int) -> List[str]:
    candidates = sitemap_urls or [site_origin.rstrip("/") + "/sitemap.xml"]
    page_urls: List[str] = []
    checked = 0
    for sm in candidates[:5]:
        resp, err, _ = fetch(session, sm, timeout)
        checked += 1
        if err or resp is None or resp.status_code >= 400:
            add_issue(result, sm, "核心技术文件", "Sitemap 无法访问", "P2", err or f"HTTP {getattr(resp, 'status_code', 'NA')}", "确保 sitemap.xml 可访问，并在 robots.txt 与 GSC/Bing Webmaster Tools 中提交。")
            continue
        if len(resp.content) > 50 * 1024 * 1024:
            add_issue(result, sm, "核心技术文件", "Sitemap 超过 50MB", "P1", f"大小 {len(resp.content)} bytes", "拆分 Sitemap 并使用 sitemap index。")
        locs, is_index = parse_sitemap_urls(resp.text)
        if not locs:
            add_issue(result, sm, "核心技术文件", "Sitemap 未解析出 URL", "P1", "未找到 loc", "检查 XML 格式、命名空间与内容生成逻辑。")
            continue
        if len(locs) > 50000 and not is_index:
            add_issue(result, sm, "核心技术文件", "Sitemap URL 数超过 50,000", "P1", f"URL 数 {len(locs)}", "拆分为多个 Sitemap 并使用 Sitemap 索引文件。")
        if is_index:
            sub_pages = analyze_sitemaps(result, session, site_origin, locs[:5], timeout)
            page_urls.extend(sub_pages)
        else:
            page_urls.extend(locs)
    result.meta["sitemap_candidates_checked"] = checked
    result.meta["sitemap_url_count_sampled"] = len(page_urls)
    for url in page_urls[:20]:
        resp, err, _ = fetch(session, url, timeout)
        if err or resp is None:
            add_issue(result, url, "核心技术文件", "Sitemap 中 URL 无法访问", "P1", err or "请求失败", "从 Sitemap 移除无法访问 URL，或修复页面可访问性。")
        elif resp.status_code in {301, 302, 307, 308} or resp.history:
            add_issue(result, url, "核心技术文件", "Sitemap 包含重定向 URL", "P2", f"最终 URL {resp.url}", "Sitemap 应包含规范且返回 200 的最终 URL。")
        elif resp.status_code >= 400:
            add_issue(result, url, "核心技术文件", "Sitemap 包含错误 URL", "P1", f"HTTP {resp.status_code}", "从 Sitemap 移除 4xx/5xx URL。")
    return page_urls


def analyze_llms(result: SiteResult, session: requests.Session, site_origin: str, timeout: int) -> None:
    url = site_origin.rstrip("/") + "/llms.txt"
    resp, err, _ = fetch(session, url, timeout)
    if err or resp is None or resp.status_code == 404:
        add_issue(result, url, "GEO/AI 可读性", "缺少 llms.txt", "P3", err or "HTTP 404", "如业务依赖 AI 搜索与 LLM 引用，建议在根目录提供 llms.txt。")
        return
    if resp.status_code >= 400:
        add_issue(result, url, "GEO/AI 可读性", "llms.txt 返回错误", "P2", f"HTTP {resp.status_code}", "确保 /llms.txt 可公开访问。")
        return
    ctype = resp.headers.get("content-type", "")
    text = resp.text.strip()
    if "text" not in ctype.lower() and "markdown" not in ctype.lower():
        add_issue(result, url, "GEO/AI 可读性", "llms.txt Content-Type 不理想", "P3", ctype, "建议以 text/plain 或 text/markdown 输出。")
    if not re.search(r"^#\s+\S+", text, re.M):
        add_issue(result, url, "GEO/AI 可读性", "llms.txt 缺少 H1", "P2", "未发现 Markdown H1", "使用唯一 H1 标识网站或项目名称。")
    if not re.search(r"^>\s+", text, re.M):
        add_issue(result, url, "GEO/AI 可读性", "llms.txt 缺少摘要引用块", "P3", "未发现 > 引用块", "在 H1 后加入 2–3 句摘要引用块，帮助 AI 快速理解业务。")
    if not re.search(r"^##\s+", text, re.M):
        add_issue(result, url, "GEO/AI 可读性", "llms.txt 缺少 H2 分组", "P3", "未发现 Markdown H2", "用 H2 将产品、文档、博客、集成指南等分组。")
    if not re.search(r"\[[^\]]+\]\(https?://[^)]+\)", text):
        add_issue(result, url, "GEO/AI 可读性", "llms.txt 缺少 Markdown 链接", "P2", "未发现 [title](URL)", "在每个分组下提供高质量、干净版本内容链接。")


def analyze_site_level(result: SiteResult, session: requests.Session, site_url: str, timeout: int) -> str:
    site_origin = origin(site_url)
    host = urllib.parse.urlparse(site_url).netloc
    http_url = "http://" + host + "/"
    http_resp, _, _ = fetch(session, http_url, timeout)
    if http_resp is not None and http_resp.url.startswith("http://") and http_resp.status_code < 400:
        add_issue(result, http_url, "HTTPS 与安全", "HTTP 未强制跳转 HTTPS", "P1", f"最终 URL {http_resp.url}", "将所有 HTTP 请求 301 到 HTTPS 规范版本。")
    home_resp, err, _ = fetch(session, site_url, timeout)
    if err or home_resp is None:
        add_issue(result, site_url, "抓取与可访问性", "首页无法访问", "P0", err or "请求失败", "先修复站点根入口可访问性。")
        return site_origin
    result.meta["home_final_url"] = home_resp.url
    result.meta["home_status_code"] = home_resp.status_code
    final_origin = origin(home_resp.url)
    headers = {k.lower(): v for k, v in home_resp.headers.items()}
    if not home_resp.url.startswith("https://"):
        add_issue(result, home_resp.url, "HTTPS 与安全", "首页最终不是 HTTPS", "P0", home_resp.url, "生产官网应使用有效 HTTPS，并将 HTTP 版本永久重定向到 HTTPS。")
    for h, rec in SECURITY_HEADERS.items():
        if h not in headers:
            sev = "P2" if h in {"strict-transport-security", "x-content-type-options"} else "P3"
            add_issue(result, home_resp.url, "安全头信息", f"缺少 {h}", sev, "响应头未发现", rec)
    not_found_url = final_origin.rstrip("/") + f"/__seo_audit_404_test_{int(time.time())}"
    nf_resp, nf_err, _ = fetch(session, not_found_url, timeout)
    if nf_err or nf_resp is None:
        add_issue(result, not_found_url, "自定义 404", "404 测试无法完成", "P3", nf_err or "请求失败", "确认不存在页面能稳定返回正确状态码。")
    elif nf_resp.status_code not in {404, 410}:
        add_issue(result, not_found_url, "自定义 404", "不存在页面未返回 404/410", "P1", f"HTTP {nf_resp.status_code}", "避免 soft 404；不存在 URL 应返回 404 或 410，同时展示友好导航。")
    return final_origin


def crawl_site(site: str, max_pages: int, timeout: int, user_agent: str) -> SiteResult:
    site_url = normalize_url(site)
    result = SiteResult(site=site_url, started_at=datetime.now(timezone.utc).isoformat())
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    try:
        final_origin = analyze_site_level(result, session, site_url, timeout)
        sitemaps = analyze_robots(result, session, final_origin, timeout)
        sitemap_pages = analyze_sitemaps(result, session, final_origin, sitemaps, timeout)
        analyze_llms(result, session, final_origin, timeout)
        queue: deque[str] = deque()
        seen: Set[str] = set()
        queue.append(final_origin.rstrip("/") + "/")
        for sm_url in sitemap_pages[: max(0, max_pages // 2)]:
            if same_host(sm_url, final_origin):
                queue.append(sm_url)
        while queue and len(result.pages) < max_pages:
            url = queue.popleft()
            norm = normalize_for_compare(url)
            if norm in seen:
                continue
            seen.add(norm)
            page, links = analyze_page(result, session, url, timeout, final_origin)
            if page:
                result.pages.append(page)
            for link in links:
                if len(seen) + len(queue) >= max_pages * 4:
                    break
                if same_host(link, final_origin) and normalize_for_compare(link) not in seen:
                    queue.append(link)
        if not result.pages:
            add_issue(result, site_url, "抓取与可访问性", "未能抓取任何 HTML 页面", "P0", "页面样本数 0", "检查首页、robots、JS 渲染、WAF 与服务端可访问性。")
        schema_counter = Counter()
        for p in result.pages:
            for typ in [x.strip() for x in p.schema_types.split(",") if x.strip()]:
                schema_counter[typ] += 1
        indexable_pages = [p for p in result.pages if p.status_code and p.status_code < 400 and not p.noindex]
        title_groups: Dict[str, List[str]] = {}
        desc_groups: Dict[str, List[str]] = {}
        canonical_groups: Dict[str, List[str]] = {}
        for p in indexable_pages:
            if p.title:
                title_groups.setdefault(p.title.lower(), []).append(p.final_url)
            if p.description:
                desc_groups.setdefault(p.description.lower(), []).append(p.final_url)
            if p.canonical:
                canonical_groups.setdefault(normalize_for_compare(p.canonical), []).append(p.final_url)
        for title, urls in title_groups.items():
            if len(urls) > 1:
                add_issue(result, urls[0], "源代码标签", "可索引页面 title 重复", "P2", f"{len(urls)} 个样本页面共用 title：{title[:120]}", "按页面搜索意图和模板变量生成唯一、描述性 title。")
        for desc, urls in desc_groups.items():
            if len(urls) > 1:
                add_issue(result, urls[0], "源代码标签", "可索引页面 meta description 重复", "P3", f"{len(urls)} 个样本页面共用 description：{desc[:120]}", "为核心页面提供唯一描述；低价值分页或筛选页可结合 noindex/canonical 策略。")
        for canonical, urls in canonical_groups.items():
            unique_pages = {normalize_for_compare(u) for u in urls}
            if len(unique_pages) > 1 and len(urls) > 1:
                add_issue(result, urls[0], "URL 规范化", "多个可索引样本指向同一 canonical", "P2", f"canonical={canonical}; pages={len(urls)}", "确认这些页面是否确实是重复页；若是核心独立页面，应改为各自自引用 canonical。")
        if result.pages and not any(t in schema_counter for t in ["Organization", "WebSite"]):
            add_issue(result, result.meta.get("home_final_url", site_url), "结构化数据", "站点级 Organization/WebSite Schema 缺失", "P2", f"发现 Schema 类型：{dict(schema_counter)}", "在首页或全站布局中添加 Organization 与 WebSite Schema，强化品牌实体。")
        trust_hit_set = set()
        for p in result.pages:
            trust_hit_set.update(x.strip() for x in p.trust_link_hits.split(",") if x.strip())
        missing_trust = [x for x in ["privacy", "terms", "contact", "about"] if x not in trust_hit_set]
        if result.pages and len(missing_trust) >= 2:
            add_issue(result, result.meta.get("home_final_url", site_url), "E-E-A-T/信任信号", "样本页面缺少关键可信入口", "P3", f"未明显发现：{', '.join(missing_trust)}", "人工确认页脚或导航是否提供 Privacy Policy、Terms、Contact、About 等信任入口。")
    except Exception as exc:  # noqa: BLE001
        add_issue(result, site_url, "运行错误", "审计脚本异常", "P0", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:1000]}", "检查目标站点响应、脚本依赖或输入格式后重试。")
    result.meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    result.meta["page_count"] = len(result.pages)
    result.meta["issue_count"] = len(result.issues)
    return result


def read_sites(args: argparse.Namespace) -> List[str]:
    sites: List[str] = []
    if args.url:
        sites.append(args.url)
    if args.input:
        path = Path(args.input)
        if not path.exists():
            raise SystemExit(f"Input file not found: {path}")
        if path.suffix.lower() == ".csv":
            with path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    key = "url" if "url" in reader.fieldnames else reader.fieldnames[0]
                    for row in reader:
                        if row.get(key):
                            sites.append(row[key])
                else:
                    f.seek(0)
                    for row in csv.reader(f):
                        if row:
                            sites.append(row[0])
        else:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    sites.append(line)
    unique: List[str] = []
    seen: Set[str] = set()
    for s in sites:
        norm = normalize_url(s)
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(norm)
    if not unique:
        raise SystemExit("No URL provided. Use --url or --input.")
    return unique


def write_outputs(results: List[SiteResult], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    issues_path = out_dir / "issues.csv"
    pages_path = out_dir / "pages.csv"
    summary_path = out_dir / "summary.json"
    report_path = out_dir / "report.md"

    with issues_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["site", "page", "category", "check", "severity", "evidence", "recommendation"])
        writer.writeheader()
        for r in results:
            for i in r.issues:
                writer.writerow(i.__dict__)
    with pages_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(PageSummary.__dataclass_fields__.keys()))
        writer.writeheader()
        for r in results:
            for p in r.pages:
                writer.writerow(p.__dict__)
    summary = []
    for r in results:
        sev = Counter(i.severity for i in r.issues)
        cat = Counter(i.category for i in r.issues)
        summary.append({"site": r.site, "pages": len(r.pages), "issues": len(r.issues), "severity": dict(sev), "categories": dict(cat), "meta": r.meta})
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("# Technical SEO Audit Report\n")
    lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}\n")
    lines.append("## Executive Summary\n")
    lines.append("| Site | Pages Sampled | Issues | P0 | P1 | P2 | P3 |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in results:
        sev = Counter(i.severity for i in r.issues)
        lines.append(f"| {r.site} | {len(r.pages)} | {len(r.issues)} | {sev.get('P0', 0)} | {sev.get('P1', 0)} | {sev.get('P2', 0)} | {sev.get('P3', 0)} |")
    lines.append("\n## Priority Issues\n")
    priority = sorted([i for r in results for i in r.issues], key=lambda x: {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(x.severity, 9))[:100]
    lines.append("| Severity | Site | Category | Check | Page | Evidence | Recommendation |\n| --- | --- | --- | --- | --- | --- | --- |")
    for i in priority:
        lines.append(f"| {i.severity} | {i.site} | {i.category} | {i.check} | {i.page} | {i.evidence.replace('|', '/')} | {i.recommendation.replace('|', '/')} |")
    lines.append("\n## Output Files\n")
    lines.append("| File | Purpose |\n| --- | --- |")
    lines.append("| `issues.csv` | 可筛选的完整问题清单，适合批量网站排优先级。 |")
    lines.append("| `pages.csv` | 页面级标签、Schema、索引与内容结构样本。 |")
    lines.append("| `summary.json` | 机器可读汇总，可用于后续自动化或 BI。 |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch-only technical SEO audit for one or many sites.")
    parser.add_argument("--url", help="Single site URL to audit.")
    parser.add_argument("--input", help="CSV/TXT file containing site URLs. CSV should have a url column or URL in the first column.")
    parser.add_argument("--output-dir", default=f"technical_seo_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}", help="Output directory.")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum HTML pages to sample per site.")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of sites to audit concurrently.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds.")
    parser.add_argument("--user-agent", default=DEFAULT_UA, help="HTTP User-Agent string.")
    args = parser.parse_args()

    sites = read_sites(args)
    out_dir = Path(args.output_dir).resolve()
    results: List[SiteResult] = []
    workers = max(1, min(args.concurrency, len(sites)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(crawl_site, site, args.max_pages, args.timeout, args.user_agent): site for site in sites}
        for fut in as_completed(futures):
            site = futures[fut]
            try:
                result = fut.result()
            except Exception as exc:  # noqa: BLE001
                result = SiteResult(site=site, started_at=datetime.now(timezone.utc).isoformat())
                add_issue(result, site, "运行错误", "站点审计失败", "P0", f"{type(exc).__name__}: {exc}", "检查输入 URL 与网络状态后重试。")
            results.append(result)
            print(f"Finished {site}: {len(result.pages)} pages, {len(result.issues)} issues", file=sys.stderr)
    results.sort(key=lambda r: r.site)
    write_outputs(results, out_dir)
    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
