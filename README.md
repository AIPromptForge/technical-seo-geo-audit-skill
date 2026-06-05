# Technical SEO GEO Audit Skill

**`technical-seo-geo-audit-skill`** is a ready-to-install Skill for technical SEO, GEO/AI-search readiness, and E-E-A-T audits. It gives Manus, Codex-style agents, and other AI workspaces a repeatable workflow for finding crawl, indexation, metadata, structured data, performance, trust, and AI-readability issues across one website or thousands of domains.

This repository is designed to be usable in two ways:

- **As a Skill**: download the repo and give the `technical-seo-audit/` folder to Manus or another Skill-compatible agent.
- **As a GitHub project**: use the included Python audit script to run fetch-only public checks and generate `report.md`, `issues.csv`, `pages.csv`, and `summary.json`.

The root of the repository also includes a standalone [`SKILL.md`](./SKILL.md), so an AI tool that scans GitHub repositories can detect and package the Skill immediately.

## What This Skill Does

The Skill helps answer one practical question:

> Can search engines and AI-search systems crawl, index, understand, trust, and reuse this website correctly?

It covers:

| Area | What it checks |
| --- | --- |
| Crawlability | status codes, redirects, robots.txt, blocked resources, soft 404 risk, internal link samples |
| Indexability | canonical tags, meta robots, X-Robots-Tag, sitemap consistency, noindex mistakes |
| Technical files | `robots.txt`, `sitemap.xml`, sitemap indexes, `llms.txt`, AI crawler policy |
| On-page SEO | title, meta description, H1-H6 structure, image alt, `html lang`, viewport, Open Graph |
| Structured data | JSON-LD/Microdata, invalid JSON-LD, Organization, WebSite, Product, SoftwareApplication, Article, FAQPage, HowTo, BreadcrumbList, VideoObject, Person |
| International SEO | hreflang presence, absolute URLs, language declarations, multilingual review workflow |
| Performance and security | HTTPS, HSTS, CSP, `X-Content-Type-Options`, Referrer-Policy, slow HTML response, 404/410 behavior |
| GEO / AI-search readiness | `llms.txt`, answer-first structure, TL;DR, freshness, entity consistency, factual density, multimodal text support |
| E-E-A-T | author expertise, real experience signals, third-party authority, privacy/terms/contact/about visibility, reputation checks |
| Private-data workflows | GSC, GA4, GTM, PageSpeed/CrUX, URL Inspection, sitemap submission, Core Web Vitals, server/CDN logs |

## Why It Is Different

Many SEO audit checklists blur together confirmed problems, best practices, and guesses. This Skill separates them.

| Evidence layer | Examples | How the Skill treats it |
| --- | --- | --- |
| Public crawl evidence | HTTP status, robots.txt, title, canonical, Schema, sitemap samples | Can be reported as confirmed when fetched successfully. |
| Private search data | GSC indexing, Google-selected canonical, manual actions, sitemap submission, URL Inspection | Marked as requiring user-provided exports, screenshots, or authorized browser access. |
| Field performance data | Core Web Vitals, CrUX, PageSpeed field data | Treated separately from lab or response-time hints. |
| Analytics data | organic landing pages, conversions, events, revenue | Used to prioritize business impact, not guessed from metadata alone. |
| GEO strategy | `llms.txt`, summaries, FAQ, entity consistency, freshness | Treated as AI-readability and content-clarity guidance, not guaranteed ranking or citation signals. |

## Repository Layout

```text
technical-seo-geo-audit-skill/
├── SKILL.md                         # Root-level Skill entry for GitHub/AI detection
├── README.md                        # Project and installation guide
├── LICENSE
├── requirements.txt
├── examples/
│   ├── sites.csv
│   ├── run_single_site.sh
│   └── run_batch_sites.sh
└── technical-seo-audit/
    ├── SKILL.md                     # Full Skill entry for Manus-style installation
    ├── references/
    │   ├── checklist.md             # Complete technical SEO/GEO/E-E-A-T checklist
    │   └── gsc_workflow.md          # GSC/GA4/PageSpeed/log workflow
    ├── scripts/
    │   └── technical_seo_audit.py   # Fetch-only audit script
    └── templates/
        ├── audit_report_template.md
        └── site_list_example.csv
```

## Install As A Manus Skill

Download or clone the repository, then copy the complete Skill folder:

```bash
cp -a technical-seo-audit /home/ubuntu/skills/technical-seo-audit
```

In Manus or another compatible AI workspace, ask:

```text
Please use technical-seo-audit to audit https://example.com for technical SEO, GEO, and E-E-A-T issues. Prioritize P0/P1/P2 problems and include evidence, impact, recommended fixes, and verification methods.
```

For batch screening:

```text
Please use technical-seo-audit to audit the websites in this CSV. Focus on robots.txt, sitemap.xml, HTTPS, redirects, canonical, noindex, title, H1, Schema, 404 behavior, llms.txt, and P0/P1 technical blockers. Return issues.csv, pages.csv, summary.json, and a short executive summary.
```

## Install From GitHub Into An AI Agent

If your AI tool can read GitHub repositories, give it this instruction:

```text
Install or load this repository as a Skill. Use the root SKILL.md as the entry point. The complete Skill package and supporting files are in technical-seo-audit/. When auditing a website, run the fetch-only script first, then load references/checklist.md, references/gsc_workflow.md, and templates/audit_report_template.md as needed.
```

If the tool only accepts a folder, give it:

```text
technical-seo-audit/
```

If the tool only accepts one file, give it:

```text
SKILL.md
```

Then also provide the repository URL so it can load the supporting references, scripts, and templates.

## Use As A Command-Line Audit Tool

The bundled script is fetch-only. It publicly requests target pages, never logs in, never submits forms, never changes Search Console or analytics settings, and never requests indexing.

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Audit One Website

```bash
python technical-seo-audit/scripts/technical_seo_audit.py \
  --url https://example.com \
  --max-pages 30 \
  --output-dir ./output/example-audit
```

### Audit Many Websites

Create a CSV:

```csv
url,group,notes
https://example.com,main,single-site example
https://www.example.org,competitor,competitor example
```

Run:

```bash
python technical-seo-audit/scripts/technical_seo_audit.py \
  --input examples/sites.csv \
  --max-pages 5 \
  --concurrency 5 \
  --output-dir ./output/batch-audit
```

For third-party websites, keep concurrency low. For owned websites, start with `--concurrency 3` to `5`, then increase only if the server is stable.

## Output Files

| File | What it contains | Best used for |
| --- | --- | --- |
| `report.md` | readable summary, priority table, top findings | fast review by SEO, product, and engineering teams |
| `issues.csv` | site, page, category, check, severity, evidence, recommendation | filtering P0/P1 issues, spreadsheet import, BI dashboards |
| `pages.csv` | page-level metadata, canonical, robots, Schema, hreflang, alt, OG, viewport, word count, trust-link hits | finding template-level SEO patterns |
| `summary.json` | site-level issue counts, severity distribution, crawl metadata | automation, monitoring, downstream processing |

## Priority Model

| Priority | Meaning | Typical examples |
| --- | --- | --- |
| P0 | Critical issue that can block crawl, indexation, or site availability | production site disallowed in robots.txt, homepage unavailable, widespread 5xx, HTTP final URL for production homepage, security/manual action |
| P1 | Serious issue affecting indexing, canonicalization, structured-data validity, trust, or large URL sets | core pages noindex, broken canonical, sitemap full of 4xx/5xx or redirects, soft 404, invalid JSON-LD, HTTP not redirecting to HTTPS |
| P2 | Important issue affecting search understanding, crawl efficiency, rich-result eligibility, UX, or operational quality | missing title/canonical/H1/lang/viewport, weak hreflang, missing key Schema, high alt-missing ratio, slow HTML response, missing HSTS |
| P3 | Enhancement, GEO/AI-readability, content quality, analytics, or manual strategy item | missing `llms.txt`, weak TL;DR, stale content, thin E-E-A-T proof, incomplete OG image, meta description length issues, unclear AI crawler policy |

## Recommended Audit Flows

| Scenario | Recommended flow |
| --- | --- |
| Quick health check | crawl 10-30 pages, fix P0/P1/P2 first |
| Deep single-site audit | script output + checklist + GSC/GA4/PageSpeed/Schema Validator + manual review |
| Large batch screening | crawl 3-5 pages per domain, rank by P0/P1 count, export CSV/JSON |
| SaaS website | prioritize SoftwareApplication/Product Schema, pricing/signup/demo pages, docs, E-E-A-T, entity consistency |
| Ecommerce website | prioritize Product/offers/reviews, category pagination, filter parameters, price/availability consistency |
| Multilingual website | prioritize hreflang self-reference, return links, `x-default`, language-specific canonical logic |
| Blog or publisher | prioritize Article/BlogPosting, author bios, dates, internal links, freshness, summaries, FAQ where useful |
| Documentation site | prioritize JS rendering, index coverage, versioned docs canonical, `llms.txt`, code blocks, steps, and answer-first headings |

## What The Script Can Confirm

The fetch-only script can confirm:

- homepage availability and final URL
- HTTP to HTTPS behavior
- response status and redirect chain length
- basic response timing
- security headers
- 404/410 behavior for a random missing URL
- robots.txt availability, Sitemap declarations, broad disallow risk
- sitemap accessibility, URL count limits, sampled sitemap URL status
- llms.txt availability and basic Markdown structure
- title, meta description, meta keywords length
- canonical presence, multiple canonical tags, non-self canonical patterns
- meta robots and X-Robots-Tag noindex
- H1 count and heading-level jumps
- image alt coverage
- `html lang`
- viewport and Open Graph metadata
- JSON-LD/Microdata types and invalid JSON-LD
- hreflang basic presence and absolute URL issues
- duplicate title, duplicate description, and shared canonical patterns in sampled pages
- visible-word-count thin-content hints
- privacy, terms, contact, and about link hints in sampled pages

## What Requires Private Data

These items require Search Console, analytics, logs, screenshots, or authorized browser access:

- whether Google has indexed a URL
- Google-selected canonical
- URL Inspection render and crawl result
- Search Console page indexing reasons
- Sitemap submission status inside GSC
- Core Web Vitals field data and URL groups
- manual actions and security issues
- organic landing-page traffic and conversions
- crawl budget and bot behavior from server/CDN logs
- GA4/GTM event and conversion integrity

The Skill is designed to label these clearly as “needs private data confirmation” instead of pretending a public crawl can prove them.

## GEO And AI-Search Notes

This repository uses a careful GEO stance:

- `llms.txt` is useful as an AI-readable site map and content guide, especially for documentation, SaaS, API, and knowledge-heavy sites.
- `llms.txt` should not be described as a guaranteed ranking, indexing, AI Overviews, or LLM citation signal.
- FAQ, TL;DR, answer-first headings, and clear entity descriptions improve human and machine readability, but they should match real visible content.
- Structured data must describe content that users can actually see on the page.
- Google AI features still depend on foundational Search requirements: crawlable, indexable, reliable, helpful, people-first content.

## Common Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `--url` | none | single website URL |
| `--input` | none | CSV or TXT file containing URLs; CSV should include a `url` column |
| `--output-dir` | auto-generated | output directory |
| `--max-pages` | `10` | maximum sampled HTML pages per site |
| `--concurrency` | `5` | number of sites audited concurrently |
| `--timeout` | `15` | HTTP request timeout in seconds |
| `--user-agent` | built-in | custom fetch User-Agent |

## Official Calibration Sources

- [Google Search Central: SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Google Search Central: Crawling and indexing](https://developers.google.com/search/docs/crawling-indexing)
- [Google Search Central: robots.txt specification](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec)
- [Google Search Central: Build and submit a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google Search Central: Structured data intro](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data)
- [Google Search Central: AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)
- [Google Search Central Blog: FAQ and HowTo rich result changes](https://developers.google.com/search/blog/2023/08/howto-faq-changes)
- [web.dev: Interaction to Next Paint](https://web.dev/articles/inp)
- [llms.txt proposal](https://llmstxt.org/)

## Safety

Use this tool responsibly. For third-party websites, keep crawl volume low and avoid stress testing. For login-required checks, request exports, screenshots, or explicit owner authorization. Never change DNS, robots.txt, GSC, GA4, GTM, CMS, CDN, or indexing settings without direct permission from the site owner.

## License

MIT License. See [`LICENSE`](./LICENSE).
