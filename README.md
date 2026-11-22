# RBC + Austin, TX Senior Finance AI Radar

A turnkey multi-portal job scraper and local web radar built for a **20-year financial services leader** targeting **AI-related roles connected to RBC** (Royal Bank of Canada, RBC Wealth Management US, RBC Capital Markets, City National Bank, City National Rochdale, and RBC's strategic AI and consulting ecosystem) while living in **Austin, Texas**.

## Why This Radar Exists

Since September 2025, RBC enforces a **4-days-per-week in-office hybrid policy** across standard corporate and tech roles, meaning almost zero W-2 tech/AI requisitions are posted as blanket "US Remote." To live in **Austin, TX** and do meaningful **RBC AI work**, this tool tracks all **6 real-world entry lanes** in one place:

1. **Direct RBC / City National Bank Austin, TX or US-Remote + AI** (alerts immediately whenever a direct W-2 match drops)
2. **RBC Strategic AI Partners Hiring in Austin / US-Remote (Zero Bank RTO)**
   * **Cohere:** Co-developer with RBC of *North for Banking* (RBC's enterprise GenAI platform across Wealth Management and Capital Markets)
   * **Conquest Planning:** Backed by RBC; builds *Strategic Advice Manager (SAM)*, the AI financial planning engine deployed across wealth advisors
   * **Factory:** Enterprise agentic AI platform naming Royal Bank of Canada (RBC) and Blackstone as flagship customers, hiring in Austin/Central US
   * **Solace:** Real-time event-driven data backbone powering agentic AI inside RBC Capital Markets
3. **Banking & Wealth AI Consulting / SOW Directors (Austin & US-Remote)**
   * Senior Financial Services AI Strategy, AI Governance, and Model Risk (`SR 11-7`) roles at Tier-1 advisory partners that staff remote US consultants onto RBC transformation programs without FTE location locks
4. **RBC US Senior Finance + AI (Spoke-Office Negotiation Targets)**
   * Director and VP roles in **US Wealth Management** (Minneapolis HQ) and **Capital Markets** (NY / Jersey City / Charlotte), paired with the **Austin Spoke-Office pitch** (badge-in seating at RBC Wealth Management's regulated Austin branch at `5301 Southwest Parkway, Building 2, Suite 300, Austin, TX 78735` or the Dallas corporate hub)
5. **RBC / CNB Texas & US-Remote Precedents**
   * Live postings proving where RBC and City National Rochdale actively approve `Remote - Texas` territory codes and Dallas/Houston corporate payroll
6. **RBC "AI Business Enablement" Executive Blueprints**
   * Canadian HQ executive AI charters (`Senior Director, AI Business Enablement`, `Director, Operations AI Readiness`) showing the exact mandate language RBC uses when hiring 20-year finance veterans into AI leadership

---

## Quick Start (One-Click Launch)

### Windows
Double-click `run.bat` (or run in PowerShell / Command Prompt):
```bat
git clone https://github.com/jdoash/rbc-austin-ai-radar.git
cd rbc-austin-ai-radar
.\run.bat
```

### macOS / Linux
```bash
git clone https://github.com/jdoash/rbc-austin-ai-radar.git
cd rbc-austin-ai-radar
chmod +x run.sh
./run.sh
```

Both launchers automatically create a local `.venv`, install dependencies (`requests` and `python-jobspy`), start the local interactive dashboard at **`http://127.0.0.1:8787`**, and open your browser.

---

## CLI Options

If you prefer running commands directly:

```bash
# Launch interactive local web app (includes 1-click Live Scrape buttons, Starred Shortlist, and CSV export)
python rbc_austin_radar.py --serve

# Run a fast ~15-second API scrape (RBC Workday + City National Bank + Cohere + Factory) and open static HTML
python rbc_austin_radar.py --quick

# Run full scrape (adds Indeed USA + LinkedIn Banking AI SOW sweep) and open static HTML
python rbc_austin_radar.py
```

## Output Files

Every scrape updates three files in `outputs/`:
* `outputs/rbc_austin_ai_board.html` (standalone zero-dependency interactive HTML board)
* `outputs/rbc_austin_ai_jobs.csv` (spreadsheet export with pay bands, AI snippets, and Austin playbook notes)
* `outputs/rbc_austin_ai_jobs.json` (structured JSON feed)
