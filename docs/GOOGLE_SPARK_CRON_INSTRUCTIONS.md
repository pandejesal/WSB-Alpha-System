# Google Spark Cron Instructions — WSB Alpha System Research Tracker

**Schedule**: Thrice daily (06:00, 14:00, 22:00 UTC)  
**Target Google Doc**: `1Q6eRu71t8uSio6wQQDQZZmGLtwUfe6FCBBIF9VefqWs`  
**Project Repo**: https://github.com/pandejesal/WSB-Alpha-System  
**Private Strategies Repo**: https://github.com/pandejesal/WSB-Alpha-Strategies (git submodule at `./strategies/`)  

---

## Task 1: GitHub Repository & Tool Discovery

### Search Strategy (execute in order)

1. **GitHub Search Queries** (use `gh api /search/repositories` or GitHub web search):
   ```
   # Reddit / WSB scrapers (updated in last 90 days)
   topic:reddit-scraper pushed:>2025-06-01 stars:>50
   topic:wallstreetbets pushed:>2025-06-01
   reddit api wrapper python pushed:>2025-06-01 stars:>100
   
   # Financial sentiment NLP (FinBERT, transformers)
   topic:finbert pushed:>2025-06-01
   topic:financial-sentiment pushed:>2025-06-01
   transformers finance sentiment pushed:>2025-06-01 stars:>200
   
   # Retail alpha / quant backtesting engines
   topic:backtesting-engine pushed:>2025-06-01 stars:>100
   topic:quantitative-trading pushed:>2025-06-01 language:python
   vectorized-backtest python pushed:>2025-06-01
   
   # Ticker disambiguation / entity resolution
   ticker disambiguation python pushed:>2025-06-01
   company name resolution financial pushed:>2025-06-01
   
   # Algorithmic execution frameworks (Alpaca-focused)
   alpaca-trade-api python pushed:>2025-06-01
   topic:algorithmic-trading execution pushed:>2025-06-01
   ```

2. **Filter Criteria** (apply programmatically):
   - **Must have**: Active maintenance (commit < 30 days ago), MIT/Apache-2.0/BSD license, Python 3.10+ support
   - **Must NOT have**: Abandoned (> 6 months no commits), GPL/viral license, no tests, security advisories
   - **Relevance scoring**: Weight by stars, recent activity, issue responsiveness, docs quality

3. **Select 2-3 High-Quality Repos** per run with:
   - Primary features (bullet list)
   - Tech stack (language, key deps, architecture)
   - Specific relevance to WSB Alpha System (map to our modules: `src/sentiment/`, `src/execution/`, `src/backtest/`, `src/data/reddit/`)
   - Integration effort estimate (hours)
   - Clickable GitHub link + clone command

### Output Format (append to Doc Section 1)

```markdown
### [YYYY-MM-DD HH:MM UTC] — Repository Discovery Run #N

| Repo | Stars | Last Commit | License | Relevance | Integration Effort |
|------|-------|-------------|---------|-----------|-------------------|
| [owner/repo](url) | ⭐XXX | YYYY-MM-DD | MIT | High/Med/Low | X hrs |

#### [owner/repo](url)
**Features**: [3-5 bullets]  
**Stack**: Python 3.11, [key deps]  
**WSB Alpha Mapping**: `src/sentiment/` → FinBERT fine-tuning; `src/data/reddit/` → Pushshift replacement  
**Clone**: `git clone https://github.com/owner/repo.git && cd repo && pip install -e .`  
**Verdict**: [Adopt / Evaluate / Monitor / Reject] — [1-line rationale]

---

```

---

## Task 2: Quantitative Research & Paper Discovery

### Search Strategy (execute in order)

1. **arXiv Searches** (use `export.arxiv.org/api/query`):
   ```
   # Retail sentiment alpha (last 180 days)
   cat:q-fin.ST+AND+abs:retail+sentiment+AND+submittedDate:[20250301 TO *]
   cat:q-fin.TR+AND+abs:wallstreetbets+OR+abs:reddit+AND+submittedDate:[20250301 TO *]
   cat:q-fin.CP+AND+abs:social+media+hype+AND+submittedDate:[20250301 TO *]
   
   # Sentiment decay / predictive modeling
   cat:q-fin.ST+AND+abs:sentiment+decay+OR+abs:predictive+modeling+AND+submittedDate:[20250301 TO *]
   
   # Market anomaly backtests
   cat:q-fin.TR+AND+abs:anomaly+backtest+AND+submittedDate:[20250301 TO *]
   cat:q-fin.GN+AND+abs:momentum+reversal+retail+AND+submittedDate:[20250301 TO *]
   ```

2. **Semantic Scholar** (for citations + related work):
   ```
   https://api.semanticscholar.org/graph/v1/paper/search?query=wallstreetbets+sentiment+alpha&fields=title,authors,year,citationCount,externalIds&limit=10
   https://api.semanticscholar.org/graph/v1/paper/search?query=retail+investor+sentiment+decay&fields=title,authors,year,citationCount&limit=10
   ```

3. **SSRN / Quant Blogs** (targeted searches):
   - SSRN: "wallstreetbets" OR "reddit sentiment" OR "retail order flow" (last 180 days)
   - QuantConnect Blog, QuantStart, Alpha Architect, Flirting with Models — search "retail sentiment"

4. **Alternative Datasets** (track new releases):
   - Pushshift / Arctic Shift dumps
   - Kaggle WSB datasets (new versions)
   - Polygon.io / Alpaca news sentiment feeds
   - RavenPack / Refinitiv retail sentiment (if free tier)

### Selection Criteria (2-3 per run)
- **Methodology rigor**: Peer-reviewed or preprint with clear identification strategy
- **Data sources**: Must be reproducible (public data or replicable collection)
- **Empirical findings**: Out-of-sample results, statistical significance reported
- **Actionable takeaways**: Direct mapping to WSB Alpha System components:
  - `src/sentiment/` — NLP model improvements
  - `src/backtest/` — Walk-forward / permutation test methodologies
  - `src/risk/` — Regime-aware position sizing
  - `src/execution/` — Slippage / market impact models

### Output Format (append to Doc Section 2)

```markdown
### [YYYY-MM-DD HH:MM UTC] — Research Discovery Run #N

| Paper / Dataset | Source | Date | Citations | Relevance |
|-----------------|--------|------|-----------|-----------|
| [Title](url) | arXiv/SSRN/Blog | YYYY-MM-DD | XXX | High/Med/Low |

#### [Title](url) — [arXiv:XXXX.XXXXX / SSRN:XXXXXX]
**Authors**: [names]  
**Methodology**: [2-3 sentences: identification strategy, data, model]  
**Data**: [source, period, frequency, sample size]  
**Key Finding**: [1-sentence quantitative result with numbers]  
**WSB Alpha Takeaway**:  
- [Specific code/module change: e.g., "Add regime-filter to `src/sentiment/finbert.py` using VIX threshold from Section 4.2"]  
- [Backtest protocol adoption: e.g., "Adopt their combinatorial CV from Section 3.1 for `scripts/run_full_backtest.py`"]  
- [Risk control: e.g., "Incorporate their sentiment decay half-life (X days) into `src/risk/sentiment_decay.py`"]  
**Verdict**: [Implement / Prototype / Archive / Reject] — [1-line rationale]

---

```

---

## Quality Gates (both tasks)

Before appending to Google Doc, verify:
- [ ] All links are clickable (test with `curl -I`)
- [ ] No duplicate entries from previous runs (dedupe by URL)
- [ ] Timestamp in UTC ISO format
- [ ] Relevance scores justified with specific WSB Alpha System module references
- [ ] Integration effort is realistic (not "trivial" for complex repos)

---

## Google Docs API Integration (for Google Spark)

```python
# Minimal append snippet for Google Spark
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

DOC_ID = "1Q6eRu71t8uSio6wQQDQZZmGLtwUfe6FCBBIF9VefqWs"
SCOPES = ["https://www.googleapis.com/auth/documents"]

def append_to_section(doc_id, section_header, markdown_content):
    creds = Credentials.from_authorized_user_file("google_token.json", SCOPES)
    service = build("docs", "v1", credentials=creds)
    
    # 1. Find section index (search for header)
    doc = service.documents().get(documentId=doc_id).execute()
    # ... locate section_header in doc['body']['content']
    
    # 2. Insert markdown as formatted text at end of section
    requests = [{
        "insertText": {
            "location": {"index": section_end_index},
            "text": markdown_content
        }
    }]
    service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
```

---

## Deduplication Logic

Maintain local SQLite cache (`research_cache.db`) with:
```sql
CREATE TABLE repo_discovery (
    url TEXT PRIMARY KEY,
    title TEXT,
    discovered_at TEXT,
    verdict TEXT,
    section INTEGER  -- 1 or 2
);
```
Check before each append; skip if URL exists.

---

## Monitoring & Alerting

- **Failure alert**: If Google Docs API returns 4xx/5xx, log to `logs/google_spark_cron.log` and email via `gmail send`
- **Success metric**: Count new unique repos/papers per run; target ≥1 high-relevance per run
- **Quarterly review**: Export Doc to markdown, run `python scripts/audit_research_tracker.py` to identify stale entries (> 180 days no follow-up)

---

## Integration with WSB Alpha System Workflow

| Discovery Output | Downstream Action | Owner |
|------------------|-------------------|-------|
| High-relevance repo | Jules PR: `feat: integrate {repo} into src/{module}/` | Jules |
| New sentiment paper | Prime evolution: add FinBERT variant to `hunts/` | Prime |
| Backtest methodology | OpenCode swarm: validate against our `evolve_real.py` gates | OpenCode |
| Execution framework | Antigravity refactor: modernize `src/execution/alpaca_executor.py` | Antigravity |

---

*Generated for Google Spark thrice-daily cron. Update this file when WSB Alpha System architecture changes.*