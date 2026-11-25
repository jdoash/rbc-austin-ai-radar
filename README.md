# RBC + Austin, TX Senior Finance AI Radar

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-0051a5?style=flat-square&logo=python&logoColor=white)
![Zero API Keys](https://img.shields.io/badge/API%20Keys-None%20Required-047857?style=flat-square)
![Portals](https://img.shields.io/badge/Live%20Sources-RBC%20Workday%20%7C%20CNB%20%7C%20Ashby%20%7C%20Indeed%20%7C%20LinkedIn-002855?style=flat-square)
![Target](https://img.shields.io/badge/Focus-20--Yr%20Finance%20%2B%20AI%20(Austin%2C%20TX)-ffd200?style=flat-square&labelColor=002855)

A turnkey multi-portal job scraper and local interactive web dashboard tailored for a **20-year financial services leader** targeting **AI Strategy, AI Enablement, Wealth/Capital Markets AI, and AI Governance roles connected to RBC** while living in **Austin, Texas**.

![RBC + Austin AI Radar Dashboard Preview](docs/dashboard_preview.png)

---

## Quick Start

### Option A: Zero-Install Browser View (Instant, No Python or Git Needed)
1. Click **Code -> Download ZIP** at the top of this page and unzip the folder.
2. Double-click `outputs/rbc_austin_ai_board.html` to open the pre-loaded interactive board directly in Chrome, Safari, or Edge.
   * Full keyword search, lane filtering, posting excerpts, and persistent **Starred Shortlist** work out of the box offline.

### Option B: Live Local Dashboard & One-Click Scraper

#### Windows
```bat
git clone https://github.com/jdoash/rbc-austin-ai-radar.git
cd rbc-austin-ai-radar
.\run.bat
```
*(Or simply double-click `run.bat` inside File Explorer.)*

#### macOS / Linux
```bash
git clone https://github.com/jdoash/rbc-austin-ai-radar.git
cd rbc-austin-ai-radar
chmod +x run.sh
./run.sh
```

Both launchers automatically create an isolated `.venv`, install `requests` + `python-jobspy` (with an automatic fallback to core `requests` on locked machines), launch the local web server at **`http://127.0.0.1:8787`**, and open your browser.

---

## Why This Architecture? (Solving the 4-Day RTO Constraint)

Since September 2025, standard corporate and tech requisitions at RBC carry a **4-days-per-week in-office hybrid policy**, which means almost zero W-2 AI roles are posted externally as blanket "US Remote." To work on meaningful **RBC / Tier-1 Banking AI mandates from Austin, TX**, this radar tracks all **6 real-world entry lanes** side by side:

| Lane | Target Employers & Feeds | Location / RTO Mechanics | Strategy Angle |
| :--- | :--- | :--- | :--- |
| **1. Direct RBC / CNB Austin + AI** | RBC Workday (`RBCGLOBAL1`), City National Bank | Austin, TX or explicit US-Remote | Immediate alert whenever a direct W-2 Austin or remote AI requisition opens |
| **2. RBC Strategic AI Partners** | **Cohere** (*North for Banking*), **Conquest Planning** (*SAM*), **Factory**, **Solace** | Remote (US / Central) or Austin, TX (Zero bank RTO) | Build and deploy GenAI directly into RBC Wealth Management & Capital Markets from the partner side |
| **3. Banking AI Consulting & SOWs** | Tier-1 Financial Services AI & Model Risk (`SR 11-7`) practices (Indeed + LinkedIn) | Austin, TX Hybrid or US-Remote | Lead multi-quarter AI transformation SOWs inside Tier-1 banks without FTE location locks |
| **4. RBC US Senior Finance + AI** | RBC US Wealth Management (Minneapolis HQ) & Capital Markets (NY / JC / Charlotte) | Spoke-Office / Executive Travel Pitch | Pitch badge-in seating at RBC Wealth Management Austin (`5301 Southwest Pkwy, Suite 300`) or Dallas + monthly hub travel |
| **5. RBC / CNB Texas Precedents** | City National Rochdale & RBC Texas corporate postings | Confirmed `Remote - Texas` or Dallas/Houston | Proves active Texas payroll and remote field territory codes already used inside RBC US |
| **6. RBC AI Executive Blueprints** | RBC Toronto HQ (`Senior Director, AI Business Enablement`, `Operations AI Readiness`) | Mandate Reference | Exact charter language RBC uses when hiring 20-year business leaders to run AI adoption |

---

## Key Features

* **Live Multi-Source Scraping (Zero API Keys):** Queries RBC Global Workday's JSON endpoints, City National Bank's careers API, Ashby partner boards (`Cohere`, `Factory`), and `JobSpy` (`Indeed USA` + `LinkedIn`) in parallel.
* **Seniority & Domain Scoring (`Fit 65-97`):** Automatically filters out junior/intern/unrelated engineering noise and ranks Director, VP, Managing Director, Principal, and Practice Lead roles by Austin viability and AI depth.
* **Actionable Per-Card Playbook Notes:** Every card surfaces extracted salary bands, matched AI context quotes from the posting body, and the specific Austin/spoke-office positioning angle.
* **Browser-Saved Shortlist & Excel CSV Export:** Star roles into a persistent browser shortlist (`localStorage`) or click **Download CSV** (`UTF-8 BOM` formatted for clean opening in Microsoft Excel).

---

## How to Tweak It for Your Own Search

Everything lives in a single readable file (`rbc_austin_radar.py`) so it is easy to customize:

* **Add or change AI / Finance keywords:** Edit `AI_REGEX` (line 65) or seniority filters in `classify_and_score()` (line 485).
* **Add more Ashby / partner companies:** Append `(slug, display_name, note)` tuples inside `scrape_ashby_partners()` (line 293).
* **Adjust Indeed / LinkedIn search queries or target cities:** Edit the `queries` list inside `scrape_jobspy_ecosystem_and_sow()` (line 356) to swap `"Austin, TX"` or tune boolean title strings.
* **CLI flags:**
  ```bash
  python rbc_austin_radar.py --serve          # Interactive local web server on http://127.0.0.1:8787
  python rbc_austin_radar.py --quick          # Fast ~15s API refresh (RBC + CNB + Ashby; preserves SOW cache)
  python rbc_austin_radar.py                  # Full scrape (APIs + Indeed USA + LinkedIn) + open HTML
  python rbc_austin_radar.py --port 8890      # Custom local server port
  ```

---

## Repository Layout

```text
rbc-austin-ai-radar/
|-- rbc_austin_radar.py               # Self-contained scraper, scorer, HTML builder, and local web server
|-- run.bat                           # One-click Windows launcher (.venv + dependencies + server)
|-- run.sh                            # One-click macOS / Linux launcher
|-- requirements.txt                  # Python dependencies (requests, python-jobspy)
|-- docs/
|   `-- dashboard_preview.png         # Front-page UI preview
`-- outputs/
    |-- rbc_austin_ai_board.html      # Standalone zero-dependency interactive HTML dashboard
    |-- rbc_austin_ai_jobs.csv        # Excel-ready spreadsheet export (pay bands, AI quotes, URLs)
    `-- rbc_austin_ai_jobs.json       # Structured JSON snapshot + scrape metadata
```
