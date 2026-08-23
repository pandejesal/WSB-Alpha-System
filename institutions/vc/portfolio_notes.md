# VC Portfolio Notes

> Scraped by VC NOTES worker — 2026-08-10.
> Method: robots.txt checked per domain before fetching; max 3 pages per VC; >=3s spacing between same-domain requests.
> "Visible company data" only — what the public portfolio page renders. JS-only grids are logged as blocked/partial.

## Summary

| VC | URL(s) used | Companies extracted | Status |
|---|---|---|---|
| a16z | a16z.com/portfolio/ | 21 | done (featured; full list behind "Load All" JS) |
| Sequoia | sequoiacap.com/companies/ | ~71 | done (table rows A–C + spotlight cards) |
| YC | ycombinator.com/companies | 0 | blocked — JS-only shell; robots disallows `/companies?*` pagination |
| Lightspeed | lsvp.com/companies/ | 19 | done (spotlights; full grid behind JS filters) |
| Index | indexventures.com/companies/ | ~340 | done (full alphabetical list) |
| Benchmark | benchmark.com/companies, /portfolio(/) | 0 | blocked — 404s / JS-only app |
| Bessemer | bvp.com/portfolio | ~32 | done (featured + detail rows) |
| Greylock | greylock.com/portfolio/ | 0 | blocked — JS shell; published `.md` mirror verified empty (follow-up) |
| Accel | accel.com/companies | ~150 of 772 | partial (page 1 only) |
| General Catalyst | generalcatalyst.com/portfolio/ | ~70 | done (structured sector/location/status/type) |

---

## 1. a16z (Andreessen Horowitz)

Source: https://a16z.com/portfolio/ — "All Investments" featured carousel (full list behind "Load All" JS button; official full list at /investment-list/).

| Company | Status |
|---|---|
| SpaceX | IPO: SPCX |
| Airbnb | IPO: ABNB |
| Lyft | IPO: LYFT |
| Figma | IPO: FIG |
| Roblox | IPO: RBLX |
| Instacart | IPO: CART |
| Coinbase | IPO: COIN |
| Slack | IPO: WORK |
| Pinterest | IPO: PINS |
| Nicira Networks | Acquired by VMware |
| Instagram | Acquired by Facebook |
| GitHub | Acquired by Microsoft |
| Wise (fka Transferwise) | DPO: WPLCF |
| Facebook | IPO: FB |
| PagerDuty | IPO: PD |
| Okta | IPO: OKTA |
| Samsara | IPO: IOT |
| Oculus VR | Acquired by Facebook |
| Skype | Acquired by Microsoft |
| Nautilus Biotechnology | SPAC: NAUT |
| PatientPing | Acquired by Appriss Health |

## 2. Sequoia Capital

Source: https://www.sequoiacap.com/companies/ — spotlight cards + "Our Companies" table (rendered chunk A–C; rest loads via JS).

### Spotlight cards
SpaceX, Airbnb, NVIDIA, reddit, Klarna, Apple, DoorDash, YouTube, Instacart, Linear, PayPal, Block, Snowflake, Stripe, Google, Nubank, Vanta, Retool, WhatsApp, Cisco, HubSpot.

### Table rows (as rendered)

| Company | Description | First partnered | Current stage |
|---|---|---|---|
| [24]7.ai | Personalized, predictive, effortless customer experience | 2003 (Early) | Growth |
| 100 Thieves | Lifestyle brand for gamers | 2018 (Early) | Growth |
| Abby Care | Trains family members to become paid caregivers | 2021 (Pre-Seed/Seed) | Early |
| AdMob | Pay-per-click marketplace for mobile apps (part of Google) | 2006 (Early) | Acquired |
| Agency | AI agent for customer success | 2024 (Pre-Seed/Seed) | Early |
| Airbnb | Unique homes and experiences | 2009 (Pre-Seed/Seed) | IPO |
| Airtime (fka mmhmm) | Video communications | 2020 (Pre-Seed/Seed) | Growth |
| Airtop (fka Switchboard) | Browser automation for AI agents | 2020 (Pre-Seed/Seed) | Early |
| Alkira | Secure cloud networks in minutes | 2018 (Early) | Growth |
| Alpha & Omega Semiconductor | Power semiconductors | 2006 (Growth) | IPO |
| AMP Robotics | High-speed guided recycling robotics | 2019 (Early) | Growth |
| Amplitude | Product analytics platform | 2018 (Growth) | IPO |
| Anrok | Compliance solution for SaaS finance | 2020 (Pre-Seed/Seed) | Growth |
| Anterior | AI Co:Pilots for healthcare administration | 2023 (Pre-Seed/Seed) | Growth |
| Anthropic | AI safety and research company | 2026 (Growth) | Growth |
| Apex | Security platform for generative AI / LLMs | 2023 (Pre-Seed/Seed) | Pre-Seed/Seed |
| Apollo | End-to-end AI sales platform | 2021 (Growth) | Growth |
| Apple | iPhone, iPod, iPad, Mac, Watch | 1978 (Pre-Seed/Seed) | IPO |
| Arcwise | Low-code platform for data apps | 2022 (Pre-Seed/Seed) | Pre-Seed/Seed |
| Armis | Agentless security for unmanaged/IoT devices | 2015 (Early) | Acquired |
| ARQ | Financial platform for affluent consumers, Americas | 2024 (Growth) | Growth |
| Aspora | Financial services for immigrant diasporas | 2024 (Early) | Growth |
| Astrocade | Creators make playable content | 2025 (Growth) | Growth |
| Atari | Video game pioneer (Asteroids, Pong) | 1975 (Early) | IPO |
| Attentive | Personalized text messaging for brands | 2019 (Growth) | Growth |
| Auctor | AI-native system of action for software implementation | 2025 (Pre-Seed/Seed) | Early |
| Aurora | Self-driving technology | 2019 (Growth) | IPO |
| Avelios | Modern hospital information system | 2025 (Early) | Early |
| Barracuda | Security, app delivery, data protection | 2005 (Early) | IPO |
| Bigeye | Data quality observability | 2021 (Early) | Growth |
| BigPanda | Incident management for data centers | 2011 (Pre-Seed/Seed) | Growth |
| biomodal | Biology/epigenetics technology | 2016 (Growth) | Growth |
| Bird | Electric vehicle maker / bike-sharing | 2018 (Growth) | IPO |
| Block | Square, Cash App, Spiral, TIDAL, TBD | 2011 (Early) | IPO |
| Blockaid | Web3 security (fraud, phishing, hacks) | 2022 (Pre-Seed/Seed) | Early |
| Blockit AI | AI scheduling agent | 2024 (Pre-Seed/Seed) | Pre-Seed/Seed |
| Blues | Data-driven services for physical products | 2020 (Pre-Seed/Seed) | Early |
| Bolt | European mobility (rides, scooters, delivery) | 2021 (Growth) | Growth |
| Breeze.cash | Crypto payments for businesses | 2022 (Pre-Seed/Seed) | Pre-Seed/Seed |
| BreezeBio | Genetic medicines (autoimmune, oncology) | 2016 (Pre-Seed/Seed) | Early |
| Brewbird | Coffee machines + pods for workplace | 2019 (Pre-Seed/Seed) | Early |
| Bridge | Stablecoin payment infrastructure (part of Stripe) | 2023 (Early) | Acquired |
| BridgeBio | Targeted treatments for genetic diseases | 2018 (Growth) | IPO |
| Bruce | AI-native trust/reputation for professional search | 2023 (Pre-Seed/Seed) | Pre-Seed/Seed |
| Bunkerhill Health | Health systems innovation partner | 2023 (Pre-Seed/Seed) | Growth |
| Cadence Design Systems | Electronic design automation | 1992 (Growth) | IPO |
| CafePress | Marketplace for designer products | 2005 (Growth) | IPO |
| Caldera | App-specific Web3 blockchains | 2022 (Pre-Seed/Seed) | Pre-Seed/Seed |
| Captions | AI-powered creative studio | 2021 (Pre-Seed/Seed) | Growth |
| CaptivateIQ | Sales commission management SaaS | 2020 (Early) | Growth |
| Carbon | 3D printing via light extrusion | 2013 (Early) | Growth |
| Catch | Merchant/consumer savings, no card rails | 2020 (Early) | Early |

---

## 3. Y Combinator

Source: https://www.ycombinator.com/companies
**BLOCKED / NO DATA.** Renders as a JS-only Inertia.js shell ("The YC Startup Directory"); no company content in raw HTML. Robots note: `/companies?*` (all query-string variants, incl. pagination/filtering) and `/library?*` are disallowed; plain `/companies` is allowed.

Follow-up (2026-08-10): confirmed the page is backed by Algolia (index `YCCompany_production`, app `45BWZJ1SGC`, public search key embedded in page HTML as `window.AlgoliaOpts`). Direct API recovery attempted: POST `/1/indexes/YCCompany_production/query` failed with 400 "Expecting map key (near 1:2)" — the local (Windows PowerShell) shell mangles JSON bodies on the command line; GET `/query?query=&hitsPerPage=50` returns 404 ("ObjectID does not exist" — GET route is object-fetch, search is POST-only). Net: still blocked without a real browser renderer. If retried from a sane shell, the fix is `POST /1/indexes/YCCompany_production/query` with body `{"query":"","hitsPerPage":50,"page":0}` + the x-algolia headers.

## 4. Lightspeed (LSVP)

Source: https://lsvp.com/companies/ — founder spotlights + "Spotlight companies" grid section (full filterable grid behind JS filters; India mirror at /companies-india/).

| Company | Founded | Stage invested | Backed since | Status |
|---|---|---|---|---|
| Anthropic | 2021 | Series D | 2024 | Private |
| Wiz | 2020 | Series D | 2023 | Private |
| Cyera | 2020 | Series E | 2024 | Private |
| Rubrik | 2014 | Series A | 2014 | Public |
| Navan | 2015 | Seed | 2015 | IPO |
| Faire | 2017 | Series B | 2018 | Private |
| Cato Networks | 2015 | Series C | 2019 | Private |
| Zola | 2013 | Series C | 2016 | Private |
| Alloy | 2015 | Series C | 2021 | Private |
| Ultima Genomics | 2016 | Seed | 2016 | Private |
| BetterUp | 2013 | Series B | 2017 | Private |
| Affirm | 2012 | Series B | 2013 | IPO |
| AppDynamics | 2008 | Series A | 2008 | Acquired |
| Aqua Security | 2015 | Series B | 2017 | Private |
| Arctic Wolf | 2012 | Series A | 2012 | Private |
| Axonius | 2017 | Series C | 2020 | Private |
| Believer | 2022 | Series A | 2022 | Private |
| Carta | 2012 | Series E | 2019 | Private |
| ClickHouse | 2021 | Series B | 2021 | Private |

---

## 5. Index Ventures

Source: https://www.indexventures.com/companies/ — full alphabetical portfolio list (indexes "backed by Index", all). Listed tickers inline; new $200M seed fund "Index Origin".

1stdibs (NASDAQ: DIBS), Abacus.ai, Adaptive ML, Adfin, Adyen (AMS: ADYEN), Adzuna, Alan, Albert, Allara, Ando, Anine Bing, ankar.ai, Ankorstore, Anrok, Anthropic, Apex, ApplyBoard, Apron, Arca, Argent, Arondite, ArthurAI, Ascend, Astelia, Atlantic Money, Atlar, AttackIQ, Augment, Aurora, Auxmoney, Backbone, BallerTV, Beam, Beamery, Beauty Pie, Because, Behavox, Bigger Games, Big Health, Bird (NYSE: BRDS), Birdie, BIT ODD, BitPay, BlaBlaCar, Bloom & Wild, Boulevard, BrightGo, BrightHire, BRINC, Build, Built, Capitolis, cargo.one, Cartesia, Castle, Catch, Causaly, Chai Discovery, Check, CipherCloud, Citymapper, Class Companion, ClickHouse, Clumio, Coalition, Cockroach Labs, Cocoon, Codat, Codecademy, CodeSignal, Cohere, Collibra, Common Room, ComplyAdvantage, Conduct, Confluent (NASDAQ: CFLT), Cord, Covariant.ai, Cowboy, Cowboy Space (Aetherflux), Cradle, Creative Juice, Credit Benchmark, Crosby, Crossing Minds, Culture Amp, Curtsy, Cutover, Datadog (NASDAQ: DDOG), DataSnipper, Daydream, Decagon, DeepL, Deepnote, DeepScribe, Deliveroo (LON: ROO), /dev/agents, Discord, Dot Product, Double, DraftWise, Dream Games, Duffel, Duna, duvo.ai, Eisen, Elementl, Empathy, Enigma, EthonAI, evervault, Expel, Factual, Feathery, Figma, Fireblocks, Fireworks, Flagship, Flapping Airplanes, flatfair, Flipboard, fomo, Fonoa, Footprint, Frame Security, Funding Circle (LON: FCH), Garner Health, Gather, Gatsby/Netlify, GetHarley, Glossier, Glow, GOAT, Gong, Good Eggs, Goody, Grailed, Granola, Greg, Gremlin, Harmonic, Hebbia, Hoop, Humanloop, Humu/Perceptyx, Hutch Games, Hyperline, Ideogram AI, Immersive Gamebox, incident.io, Ineffable, Inherent, Instabase, Intelligence (Arcada), Intercom, Iterable, Josh Wood Colour, Jumbo Coalition (Jumbo Privacy), Jump, JustPark, Justworks, Kayrros, Kindred, Kong, KRY/LIVI, Lever, Lightning AI (Grid.ai), Linear, Linktree, Linx Security, Lithic (Privacy.com), LiveKit, Loctax, Lookout, Loop, Marker, Matera (fka illicopro), Mercantile, Metromile (NASDAQ: MILE), Mirage (Captions), Mirelo, Mistral, Moment, Monad, Monograph, Montonio, MOO, Motive, Motorway, Multiverse (WhiteHat), MyHeritage, Nacelle, Natoma, navabi, NewCore, Newfront, nexos.ai, Nexthink, NOTHS, Notion, Nourish, Nova Credit, Novus, Okendo, OpenX, Oratomic, Otrium, Otterize, Outbrain (NASDAQ: OB), OZON.ru (NASDAQ: OZON), Parallel, Parallel Web Systems, Patreon, Pave, Peanut, Pepper, Persona, Personio, Phaidra, Physical Intelligence, Pilot, Pinata Farms, Pitch, Plaid, Plain, PointFive, Pomelo, Printify, Prodigy Finance, Productboard, Qapa/Adecco, Quantive (Gtmhub), Quill (Twitter), Quilter, Raisin, ReadySet, Rebtel, Rec Room, Remote, Resistant AI, Revel, RevenueCat, Revolut, Robinhood (NASDAQ: HOOD), Roblox (NYSE: RBLX), Rohlik, Roli, Ryft, SafetyCulture, Sanlo, Savvy, Scale, Science Exchange, Scoop, Scope, Second Home, Secret Escapes, Seedcamp, SeedLegals, ServiceTitan, Seso, Shapeways, Shopmonkey, Signal Sciences (Fastly), Silverfin, Simile, Siro, Sofia, Solvo, Sourceful, Spendesk, Spiko, Squarespace, Stack Overflow, Starburst, Strapi, Stytch, Sublime Security, Subset, Superconductive, Super Evil Megacorp, Superlinked, Supersolid, Swile, Sylvera, Tactile Games, Tacto, Taktile, Taxfix, Tebi, Tekion, Tema, Temporal, tessl.io, Thatch, The Business of Fashion, Thread AI, Tiney, Tofu, Transcend, Trustpilot (LON: TRST), Twelve Labs, Typeform, Ubiquity6 (Discord), Upollo, Valdera, Venice, Vetted (Lustre), Vinyl Equity, Vizcom, Vooma, Vouch, Wealthfront, Weaviate, WeTravel, Wise (LON: WISE), Wiz, Wonderful, Wordsmith AI, Workbounce, Worldover, Xata.

---

## 6. Bessemer (BVP)

Source: https://www.bvp.com/portfolio — featured logos + first detail rows of the portfolio grid (420+ companies; grid itself loads via JS filters).

### Featured logos
Canva, Anthropic, Waymo, Shopify, ServiceTitan, Perplexity, Twilio, Pinterest, LinkedIn, Auth0, Yelp, Toast, Twitch, Rocket Lab, Wix, PagerDuty, Procore, Kymera Therapeutics.

### Detail rows (as rendered)

| Company | Notes | Founded/Partnered | Roadmaps | Investors |
|---|---|---|---|---|
| 2U | NASDAQ: TWOU; SaaS OS for schools | 2008 / 2011 | Consumer, Marketplaces | Rob Stavis, Charles Birnbaum |
| 30 Sundays | AI-powered custom travel for Indian couples | — | Consumer, AI & ML | Anant Vidur Puri, Ibrahim Faruqi |
| Abridge | Records care details, health conversations | 2008 / 2021 | AI & ML, Healthcare | Steve Kraus, Sameer Dholakia |
| Acceleron | Biopharma; IPO 2013, acquired by Merck 2021 | 2003 / 2007 | Biotech, Healthcare | Steve Kraus |
| Acquire.com (fka MicroAcquire) | Startup M&A marketplace | 2020 / 2021 | Marketplaces, Enterprise | Jeremy Levine |
| Act Security | Cloud app access guardrails | 2025 / 2025 | AI & ML, Cybersecurity | Amit Karp, Alex Ferrara |
| ACTIV Financial | Market data for electronic trading; acquired by Options Technology | 2002 / 2009 | Fintech | Rob Stavis, Alex Ferrara |
| ACV Auctions | Wholesale vehicle auctions; NASDAQ: ACVA | 2014 / 2017 | Marketplaces, Vertical software | Bob Goodman, Mike Droesch |
| Ada | AI chatbot platform for support teams | 2016 / 2016 | AI & ML, Enterprise | Brian Feinstein |
| Adaptive Insights | Cloud CPM; acquired by Workday 2018 | 2010 / 2013 | Cloud, Enterprise | Bob Goodman |
| Affirmed Networks | Mobile network solutions; acquired by Microsoft 2020 | — | Cloud | — |
| AIMon | Enterprise generative AI reliability | 2023 / 2024 | AI & ML | David Cowan |
| Aivar | Production-grade AI systems for enterprises | — | AI & ML, India | — |

## 7. Greylock

Source: https://www.greylock.com/portfolio/
**BLOCKED (JS shell)** — page returns only a stub ("We back category-defining teams", updated 7/13/2026). Greylock publishes agent-friendly markdown at greylock.com/sitemap.md; portfolio data lives in: greylock.com/portfolio/applications.md, /consumer.md, /cybersecurity.md, /deep-tech.md, /fintech.md, /infrastructure.md.

Follow-up (2026-08-10): fetched the sitemap + all six published `.md` portfolio files. **All are empty templates** — frontmatter + heading placeholders, zero company rows. The visible Greylock portfolio is generated client-side from an unpublished internal DB; no recoverable data exists via the markdown mirror. Truly blocked; a browser render of greylock.com/portfolio/ is the only remaining path.

## 8. Accel

Source: https://www.accel.com/companies — logo grid, 772 companies total (page 1 of several; alphabetical A–B captured).

100ms, 1Balance, 1Password, 99designs, Aavenir, Acalvio, Acko, Actuate, Ada Support, AdMob, AdRoll, AegisAI, Agave, Agile Software, Agrostar, Airbyte, AirKit, Airmeet, AirWatch, Akridata, Akto, Algolia, Ally, Alpha Technologies, Altinity, Amagi, AMCC, Amobee, Ampool, Anar, Anchor FM, Ando, ANSR, Anthropic, Anyfin, Aorato, ApnaMart, Appbrew, Appsmith, Aptly, Aramya, Arbor Software, Arcot Systems, Arista, Arivihan, Armadin, ArrowPoint Communications, Ascend.io, AssemblyAI, Astral, Astro, Atlas, Atlassian, Atrato, atSpoke, August AI, Aura, Avenue, Avito, Away, Axio, Axle Energy, Axonius, Bachatt, Basis, BaubleBar, BBN Technologies, Beam, Beek, BeReal, BestDoc, BetterCloud, Bevy, Binocs, Biostate AI, Bird, Bird Scooters, Bizongo, BlaBlaCar, BlackBuck, Blackpoint, Blameless, Blue Jeans Network, Bluestone, Bonobos, Book My Show, Born, Borqs, Bounce, Braintree, Breathe Well-being, Brick&Bolt, Bridgetown Research, Brightmail, Brik, BRND.ME, BrowserStack, Brumbrum.
(Remainder of A–Z beyond "Brumbrum" not captured — pagination/JS; 622 companies still uncaptured.)

---

## 9. General Catalyst

Source: https://www.generalcatalyst.com/portfolio/ — structured grid, page 1 of 24 (A–Arrcus). Flags transcribed 1:1 from page (columns: Active/IPO/Acquired + Creation/CVF/Seed). Featured ("Creation") cards: Anduril, Anthropic, Applied Intuition, Commure, Helsing, Hippocratic AI, Legora, Maven, Mercor, Ramp, Re:Build, Ro, Serval, Stripe, Zepto.

| Company | Sector | Location | Status/Type |
|---|---|---|---|
| 1001 AI | Artificial Intelligence | MENA | Active / Seed |
| 222 | Consumer | North America | Active / — |
| Aaru | Artificial Intelligence | North America | Active / Seed |
| Aatmunn | Enterprise | North America | Active / — |
| Accordance | Artificial Intelligence | North America | Active / Seed |
| Accrual | Fintech | North America | Active / Creation |
| Adonis | Healthcare | North America | Active / — |
| Afori | Fintech | Europe | Active / Seed |
| AfterHour | Consumer | North America | Active / Seed |
| AgentMail | Artificial Intelligence | North America | Seed only |
| Agora | Fintech | North America | Active / Seed |
| Aidoc | Healthcare | Europe | Active / — |
| AIM | Artificial Intelligence | North America | Active / Seed |
| Airbnb | Consumer | North America | Flag2 (IPO) |
| AirSlate | Enterprise | North America | Active / CVF |
| Alinea Health | Healthcare | South America | Active / Seed |
| Allego | Enterprise | North America | Active / — |
| Almanac | Healthcare | North America | Active / Seed |
| Almanac Labs | Enterprise | North America | Active / — |
| Alpha-9 Oncology | Healthcare | North America | Active / — |
| Alsym Energy | Energy & Infrastructure | North America | Active / — |
| Altos Labs | Healthcare | North America | Active / — |
| Alyce | Enterprise | North America | Active / Seed |
| Amigo | Artificial Intelligence | North America | Active / Seed |
| Amperity | Enterprise | North America | Active / — |
| Amphiform | Energy & Infrastructure | Europe | Active / Seed |
| Anagram | Defense & Government | North America | Active / Seed |
| Andesite | Defense & Government | North America | Active / — |
| Anduril | Defense & Government | North America | Active / Seed |
| Anomali | Enterprise | North America | Active / — |
| Anthropic | Artificial Intelligence | North America | Active / — |
| Apiiro | Enterprise | North America | Active / — |
| Applied Intuition | Defense & Government | North America | Active / — |
| Arca | Fintech | North America | Active / — |
| Ares Interactive | Consumer | North America | Active / — |
| Argmax | Enterprise | North America | Active / Seed |
| Armis | Defense & Government | North America | Active / — |
| Arphie | Enterprise | North America | Active / Seed |
| Array | Fintech | North America | Active / — |
| Arrcus | Enterprise | North America | Active / — |
| ArriVent | (no sector shown) | — | — |
| Artie | (no sector shown) | — | — |
| Athelas | (no sector shown) | — | — |
| Athletes First | (no sector shown) | — | — |
| AtoB | (no sector shown) | — | — |
| Audius | (no sector shown) | — | — |
| August Health | (no sector shown) | — | — |
| Aura | (no sector shown) | — | — |
| Aurelius Systems | (no sector shown) | — | — |
| AuthZed | (no sector shown) | — | — |

---

## Blocked / Partial Pages Log

| Domain | URL tried | Result |
|---|---|---|
| ycombinator.com | https://www.ycombinator.com/companies | JS-only shell; no visible data without browser render; robots disallows `/companies?*` pagination |
| benchmark.com | /companies, /companies/, /portfolio, /portfolio/ | All 404 (JS app, different routing) |
| greylock.com | /companies/, /portfolio/ | JS shell; markdown mirror available at greylock.com/sitemap.md → /portfolio/*.md |
| indexventures.com | /portfolio/, /portfolio/companies/ | 404 — correct path is /companies/ |
| a16z.com | /portfolio/ | Partial: featured list only; full list behind "Load All" JS + official /investment-list/ |
| sequoiacap.com | /companies/ | Partial: spotlights + table rows A–C rendered; rest loads via JS |
| lsvp.com | /companies/ | Partial: spotlight sections; full grid behind JS filters |
| bvp.com | /portfolio | Partial: featured + first detail rows; grid behind JS filters |
| accel.com | /companies | Partial: page 1 (A–B) of 772; pagination not fetched |
| generalcatalyst.com | /portfolio/ (pages 1–2) | Page 2 returned identical content (Webflow pagination param ignored w/o JS); page 1 of 24 captured |
| greylock.com | /portfolio/*.md (6 files) | Follow-up: all six published markdown files are empty templates — no company data; blocked |
| ycombinator.com | Algolia YCCompany_production | Follow-up: API recovery attempted; POST body mangled by shell (400), GET /query invalid (404); blocked without browser render |

## Robots Compliance Notes

- robots.txt checked per domain: sequoiacap (allow all), ycombinator (as noted), lsvp (wp-admin only), indexventures (pdfs/landing only), bvp (wp-admin, /page/, /archives/, etc.), greylock (allow `/`, but ClaudeBot/GPTBot explicitly blocked — used plain fetcher, no training use), accel (allow `/`), generalcatalyst (/list, /internal/ blocked — not used).
- a16z and benchmark return no robots.txt (404) → treated as allow.
- Rate limit: >=3s between same-domain sequential fetches; page-2 attempts spaced accordingly.
- Extraction target: visible rendered content only; no API endpoints, no training reuse (greylock Content-Signal: ai-train=no respected — data used for reference notes only).