import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


ALLOWED_OUTPUT_FORMATS = {"markdown"}
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; EcommerceRAGAgent/0.1)"
NOT_SPECIFIED = "Not specified"


@dataclass
class ProductKnowledge:
    name: str = NOT_SPECIFIED
    description: str = NOT_SPECIFIED
    category: str = NOT_SPECIFIED
    price: str = NOT_SPECIFIED
    variants: str = NOT_SPECIFIED
    usage_notes: str = NOT_SPECIFIED


@dataclass
class PolicyKnowledge:
    shipping: str = NOT_SPECIFIED
    returns: str = NOT_SPECIFIED
    refunds: str = NOT_SPECIFIED
    processing_time: str = NOT_SPECIFIED
    exchanges: str = NOT_SPECIFIED
    cancellations: str = NOT_SPECIFIED
    contact: str = NOT_SPECIFIED


@dataclass
class StoreKnowledge:
    source_url: str
    products: list[ProductKnowledge]
    policy: PolicyKnowledge
    faq: list[dict]


class StoreKnowledgeError(Exception):
    def __init__(self, code: str, suggestion: str, store_url: str = ""):
        super().__init__(suggestion)
        self.code = code
        self.suggestion = suggestion
        self.store_url = store_url

    def as_dict(self) -> dict:
        return {
            "error": self.code,
            "store_url": self.store_url,
            "suggestion": self.suggestion,
        }


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            self._href = attrs_dict.get("href")
            self._text_parts = []

    def handle_data(self, data):
        if self._href:
            self._text_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            text = normalize_whitespace(" ".join(self._text_parts))
            if text:
                self.links.append({"href": self._href, "text": text})
            self._href = None
            self._text_parts = []


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            cleaned = normalize_whitespace(data)
            if cleaned:
                self.parts.append(cleaned)

    def text(self) -> str:
        return normalize_whitespace(" ".join(self.parts))


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def validate_store_url(store_url: str) -> str:
    if not store_url:
        raise StoreKnowledgeError(
            "MISSING_STORE_URL",
            "Please provide a valid e-commerce store URL.",
        )

    parsed = urllib.parse.urlparse(store_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise StoreKnowledgeError(
            "INVALID_STORE_URL",
            "Please provide a public http or https store URL.",
            store_url,
        )

    return store_url


def fetch_text(url: str, timeout: int = 15) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise StoreKnowledgeError(
            "STORE_FETCH_FAILED",
            "Check the URL or try again later.",
            url,
        ) from exc

    if "text" not in content_type and "json" not in content_type and "html" not in content_type:
        return body.decode(charset, errors="replace")

    return body.decode(charset, errors="replace")


def extract_links(html: str, base_url: str) -> list[dict]:
    parser = LinkExtractor()
    parser.feed(html)
    results = []
    seen = set()
    for link in parser.links:
        absolute = urllib.parse.urljoin(base_url, link["href"])
        key = (absolute, link["text"].lower())
        if key in seen:
            continue
        seen.add(key)
        results.append({"url": absolute, "text": link["text"]})
    return results


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.text()


def try_fetch_shopify_products(store_url: str) -> list[ProductKnowledge]:
    products_url = urllib.parse.urljoin(store_url.rstrip("/") + "/", "products.json?limit=50")
    try:
        payload = json.loads(fetch_text(products_url))
    except (StoreKnowledgeError, json.JSONDecodeError):
        return []

    products = []
    for item in payload.get("products", []):
        variants = item.get("variants") or []
        prices = sorted({variant.get("price") for variant in variants if variant.get("price")})
        variant_names = [
            variant.get("title")
            for variant in variants
            if variant.get("title") and variant.get("title") != "Default Title"
        ]
        products.append(
            ProductKnowledge(
                name=item.get("title") or NOT_SPECIFIED,
                description=html_to_text(item.get("body_html") or "") or NOT_SPECIFIED,
                category=item.get("product_type") or NOT_SPECIFIED,
                price=", ".join(prices) if prices else NOT_SPECIFIED,
                variants=", ".join(variant_names) if variant_names else NOT_SPECIFIED,
                usage_notes=NOT_SPECIFIED,
            )
        )

    return products


def extract_json_ld_products(html: str) -> list[ProductKnowledge]:
    products = []
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for script in scripts:
        try:
            data = json.loads(script.strip())
        except json.JSONDecodeError:
            continue

        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            graph = entry.get("@graph") if isinstance(entry, dict) else None
            candidates = graph if isinstance(graph, list) else [entry]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                if candidate.get("@type") != "Product":
                    continue
                offers = candidate.get("offers") or {}
                price = offers.get("price") if isinstance(offers, dict) else NOT_SPECIFIED
                products.append(
                    ProductKnowledge(
                        name=candidate.get("name") or NOT_SPECIFIED,
                        description=normalize_whitespace(candidate.get("description") or "") or NOT_SPECIFIED,
                        category=candidate.get("category") or NOT_SPECIFIED,
                        price=str(price) if price else NOT_SPECIFIED,
                        variants=NOT_SPECIFIED,
                        usage_notes=NOT_SPECIFIED,
                    )
                )

    return products


def extract_link_based_products(html: str, store_url: str) -> list[ProductKnowledge]:
    links = extract_links(html, store_url)
    product_links = []
    seen_names = set()
    for link in links:
        url_lower = link["url"].lower()
        text = link["text"]
        if "/products/" not in url_lower and "/listing/" not in url_lower:
            continue
        if len(text) < 3 or text.lower() in seen_names:
            continue
        seen_names.add(text.lower())
        product_links.append(
            ProductKnowledge(
                name=text,
                description=NOT_SPECIFIED,
                category=NOT_SPECIFIED,
                price=NOT_SPECIFIED,
                variants=NOT_SPECIFIED,
                usage_notes=f"Product URL: {link['url']}",
            )
        )
        if len(product_links) >= 20:
            break

    return product_links


def extract_products(html: str, store_url: str) -> list[ProductKnowledge]:
    products = try_fetch_shopify_products(store_url)
    if products:
        return products

    products = extract_json_ld_products(html)
    if products:
        return products

    return extract_link_based_products(html, store_url)


def pick_policy_links(html: str, store_url: str) -> dict:
    keywords = {
        "shipping": ("shipping", "delivery"),
        "returns": ("return", "returns"),
        "refunds": ("refund", "refunds"),
        "exchanges": ("exchange", "exchanges"),
        "cancellations": ("cancel", "cancellation"),
        "contact": ("contact", "support"),
    }
    matches = {}
    for link in extract_links(html, store_url):
        text = f"{link['text']} {link['url']}".lower()
        for field, terms in keywords.items():
            if field not in matches and any(term in text for term in terms):
                matches[field] = link["url"]
    return matches


def summarize_policy_text(text: str, max_chars: int = 700) -> str:
    if not text:
        return NOT_SPECIFIED
    return text[:max_chars].rstrip() if len(text) > max_chars else text


def extract_policy(html: str, store_url: str) -> PolicyKnowledge:
    policy_links = pick_policy_links(html, store_url)
    values = {}

    for field, url in policy_links.items():
        try:
            values[field] = summarize_policy_text(html_to_text(fetch_text(url)))
        except StoreKnowledgeError:
            values[field] = NOT_SPECIFIED

    homepage_text = html_to_text(html)
    if "processing" in homepage_text.lower() and "processing_time" not in values:
        values["processing_time"] = summarize_policy_text(homepage_text)

    return PolicyKnowledge(**{field: values.get(field, NOT_SPECIFIED) for field in PolicyKnowledge.__dataclass_fields__})


def generate_faq(products: list[ProductKnowledge], policy: PolicyKnowledge) -> list[dict]:
    product_names = [product.name for product in products if product.name != NOT_SPECIFIED]
    product_answer = ", ".join(product_names[:8]) if product_names else NOT_SPECIFIED

    return [
        {"question": "What products does this store sell?", "answer": product_answer},
        {"question": "How long does shipping take?", "answer": policy.shipping},
        {"question": "Does the store accept returns?", "answer": policy.returns},
        {"question": "Does the store offer refunds?", "answer": policy.refunds},
        {"question": "How can customers contact the store?", "answer": policy.contact},
    ]


def escape_markdown_table(value: str) -> str:
    return normalize_whitespace(value).replace("|", "\\|") or NOT_SPECIFIED


def products_to_markdown(knowledge: StoreKnowledge) -> str:
    lines = [
        "# Products",
        "",
        f"Source URL: {knowledge.source_url}",
        "",
        "| Name | Description | Category | Price | Variants | Usage Notes |",
        "|---|---|---|---|---|---|",
    ]
    products = knowledge.products or [ProductKnowledge()]
    for product in products:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_markdown_table(product.name),
                    escape_markdown_table(product.description),
                    escape_markdown_table(product.category),
                    escape_markdown_table(product.price),
                    escape_markdown_table(product.variants),
                    escape_markdown_table(product.usage_notes),
                ]
            )
            + " |"
        )

    return "\n".join(lines).strip() + "\n"


def policy_to_markdown(knowledge: StoreKnowledge) -> str:
    lines = [
        "# Policy",
        "",
        f"Source URL: {knowledge.source_url}",
        "",
        "## Shipping",
        "",
        knowledge.policy.shipping,
        "",
        "## Returns",
        "",
        knowledge.policy.returns,
        "",
        "## Refunds",
        "",
        knowledge.policy.refunds,
        "",
        "## Processing Time",
        "",
        knowledge.policy.processing_time,
        "",
        "## Exchanges",
        "",
        knowledge.policy.exchanges,
        "",
        "## Cancellations",
        "",
        knowledge.policy.cancellations,
        "",
        "## Contact",
        "",
        knowledge.policy.contact,
    ]

    return "\n".join(lines).strip() + "\n"


def faq_to_markdown(knowledge: StoreKnowledge) -> str:
    lines = [
        "# FAQ",
        "",
        f"Source URL: {knowledge.source_url}",
        "",
    ]
    for item in knowledge.faq:
        lines.extend([f"## Q: {item['question']}", "", f"A: {item['answer']}", ""])

    return "\n".join(lines).strip() + "\n"


def knowledge_to_files(knowledge: StoreKnowledge) -> dict[str, str]:
    return {
        "products.md": products_to_markdown(knowledge),
        "policy.md": policy_to_markdown(knowledge),
        "faq.md": faq_to_markdown(knowledge),
    }


def knowledge_to_markdown(knowledge: StoreKnowledge) -> str:
    return "\n\n".join(knowledge_to_files(knowledge).values()).strip() + "\n"


def generate_store_knowledge(store_url: str, output_format: str = "markdown") -> dict:
    if output_format not in ALLOWED_OUTPUT_FORMATS:
        raise StoreKnowledgeError(
            "INVALID_OUTPUT_FORMAT",
            "Please choose markdown.",
            store_url,
        )

    validated_url = validate_store_url(store_url)
    html = fetch_text(validated_url)
    products = extract_products(html, validated_url)
    if not products:
        products = [ProductKnowledge()]

    policy = extract_policy(html, validated_url)
    knowledge = StoreKnowledge(
        source_url=validated_url,
        products=products,
        policy=policy,
        faq=generate_faq(products, policy),
    )

    return {
        "store_url": validated_url,
        "output_format": output_format,
        "files": knowledge_to_files(knowledge),
        "markdown": knowledge_to_markdown(knowledge),
        "product_count": len([product for product in products if product.name != NOT_SPECIFIED]),
    }


def artifact_id_for_url(store_url: str) -> str:
    digest = hashlib.sha256(store_url.encode("utf-8")).hexdigest()[:16]
    return f"store-{digest}"


def save_markdown_artifact(markdown: str, store_url: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_id = artifact_id_for_url(store_url)
    path = output_dir / f"{artifact_id}.md"
    path.write_text(markdown, encoding="utf-8")
    return {"artifact_id": artifact_id, "path": path}


def save_knowledge_files(files: dict[str, str], store_url: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_id = artifact_id_for_url(store_url)
    artifact_dir = output_dir / artifact_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    for filename, content in files.items():
        path = artifact_dir / filename
        path.write_text(content, encoding="utf-8")
        paths[filename] = path

    zip_path = output_dir / f"{artifact_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, path in paths.items():
            archive.write(path, arcname=filename)

    return {"artifact_id": artifact_id, "paths": paths, "zip_path": zip_path}
