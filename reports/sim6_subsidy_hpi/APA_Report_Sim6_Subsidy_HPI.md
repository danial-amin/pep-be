# Human Intervention, Policy-Action Structure, and Profile-to-Response Traceability in a Finnish EV Subsidy Simulation

**Simulation case:** PEP simulation ID 6 (*Finnish Electric Market*)  
**Replication set:** simulation IDs 53–62 (10 runs)  
**Report date:** November 17, 2026  
**Data location:** `reports/sim6_subsidy_hpi/data/`

---

## Abstract

This report analyses a completed Persona Ecosystem Playground (PEP) multi-persona simulation on implementing an electric-vehicle (EV) subsidy policy in Finland (simulation ID 6), then tests the stability of the main qualitative findings with ten protocol-matched replications on the current PEP engine (IDs 53–62). Three analyses are reported: (1) human intervention (HPI) effects, (2) policy-action comparison, and (3) profile-to-response traceability. In the original run, four personas converged on a complementary five-item action package; a single facilitator probe (“What about the subsidy”) added almost no design detail. Across ten replications with the current engine (blind openings; anti-echo prompting), personas opened with **genuine priority conflicts** (vehicle price vs charging infrastructure vs rural range), agree-first openings fell to 0%, and the same thin probe still failed to elicit eligibility rules, amounts, or caps in 9/10 runs. Profile anchors remained visible—especially for the rural farm-owner persona—without stored retrieval evidence. Implications for using PEP logs in intervention and policy analyses are discussed.

---

## 1. Introduction

Interactive persona simulations are increasingly used to pressure-test policy ideas before field deployment. For such logs to support research claims, analysts need to know (a) whether facilitator interventions change the substance of discussion, (b) whether proposed actions are merely different or genuinely conflicting, and (c) whether stated reasons are traceable to documented persona attributes (and, where available, retrieved evidence).

This report focuses on one archived Finnish EV subsidy discussion stored in the production PEP database (Railway Postgres) and a controlled re-run series designed to confirm or qualify the original case findings.

### 1.1 Research questions

1. **HPI:** What did the researcher ask, how did personas respond before and after, and what new information appeared after the follow-up?
2. **Policy actions:** What actions were proposed, for whom, with what instruments and eligibility/priority logic, and which proposals conflict versus merely differ?
3. **Traceability:** Do stated reasons correspond to documented persona attributes? (Retrieved-evidence logs are unavailable for multi-persona simulations.)

---

## 2. Method

### 2.1 Original case (simulation 6)

| Field | Value |
|---|---|
| ID / name | 6 / *Finnish Electric Market* |
| Created / completed | 2026-02-01 (UTC) |
| Goal | “Find a way to implement a subsidy policy for the electronic vehicle acceptance in the country” |
| Personas (set 11) | Liisa Nieminen (65, retired teacher, Rovaniemi); Juho Laakso (50, farm owner, Jyväskylä); Aino Virtanen (35, environmental consultant, Turku); Mikko Salminen (28, software developer, Helsinki) |
| Turns / messages | `max_turns=10`, `current_turn=10`; **10 persona messages + 1 human message** |
| Human intervention | Turn 7: “What about the subsidy” |
| Stored outputs | `summary`, five `key_insights`, five `action_items` |
| Engine | Earlier PEP simulation stack (per-message turn numbering; rapid consensus style) |

Full transcript: `data/original_transcript.csv` and `data/original_messages.json`.  
Persona profiles: `data/original_participants.json`.

### 2.2 Replication protocol (simulations 53–62)

Ten new simulations were created via the production API with the same goal, the same four persona IDs (65, 67, 66, 64), and the same facilitator text inserted after **six** persona messages.

| Parameter | Setting |
|---|---|
| `max_turns` | 3 (= three full rounds × 4 personas ≈ **12 persona messages**) |
| `max_duration_seconds` | 600 |
| Intervention | After 6 persona messages: “What about the subsidy” |
| Post-processing | Stop run; generate summary (`action_items`, unresolved disagreements) |
| Engine note | Current PEP engine: blind openings, anti-echo / stance-accountability prompts, round-based turn caps |

**Important caveat.** Replications confirm findings under the *current* engine. Differences from simulation 6 therefore reflect both stochastic resampling and engine changes, not pure Monte Carlo noise on the February stack.

Replication JSON: `data/run_01.json` … `data/run_10.json`.  
Combined transcript: `data/replications_transcripts.csv` (130 rows).  
Aggregate codes: `data/replications_analysis.json`.

### 2.3 Analytic procedures

**HPI coding.** Messages were split at the facilitator utterance. Pre/post segments were coded for theme presence (affordability/cost; rural charging/infrastructure; battery/range/maintenance; retiree/senior; inclusion/equity; explicit subsidy language) and for whether post-intervention text added **policy design detail** (eligibility, means-testing, price caps, euro amounts, percentages, tiers, vouchers, tax credits).

**Policy-action coding.** Original `action_items` and each replication’s generated `action_items` were coded for beneficiary, instrument, eligibility/priority, and relation (complementary vs conflicting). Replication `key_insights` (system field storing *unresolved disagreements*) were used to identify conflicts the summary model judged unresolved.

**Traceability.** For each persona, keyword markers drawn from profile fields (goals, frustrations, demographics, tagline) were counted in that persona’s messages across replications. No `sources_used` / RAG chunk IDs exist on simulation messages; traceability is therefore attribute-level only.

---

## 3. Results

### 3.1 Human intervention analysis

#### 3.1.1 Original simulation 6

**Pre-intervention (messages 1–6).**  
Liisa opened with retiree affordability, rural charging, and battery longevity/maintenance. Juho, Aino, and Mikko affirmed and extended those themes. The discussion rapidly became a consensus echo rather than a negotiation of trade-offs.

**Intervention.**  
Facilitator: “What about the subsidy” (underspecified: no amount, cap, targeting rule, or alternative instrument).

**Post-intervention (messages 7–10).**  
Almost no new information. Aino’s adjacent turn largely continued the prior consensus; Mikko mentioned “comprehensive subsidy policies” once; Liisa and Juho restated rural/older-population inclusion. No eligibility rules, payment levels, or conflicting subsidy designs appeared.

**HPI conclusion (original).** The intervention is best treated as a **failed probe**: it neither redirected the agenda nor elicited actionable subsidy design.

#### 3.1.2 Ten replications

| Metric | Result (10/10 runs) |
|---|---|
| Structure | 12 persona messages + 1 human message each |
| Pre-intervention themes | Affordability, rural charging, battery/range, subsidy language: **10/10** |
| Post-intervention mentions “subsidy” | **10/10** |
| Post-intervention adds design detail (eligibility/€/%/cap/tier/…) | **1/10** |
| Agree-first opening rate (pre / post) | **0.00 / 0.00** (current engine) |

Unlike the original, replications showed **priority conflict in openings** (e.g., purchase-price subsidies vs infrastructure-first subsidies vs rural-range constraints). Final-round phrasing often included “My position remains unchanged…”, consistent with stance-accountability prompting.

**HPI conclusion (replications).** The thin probe still does not produce policy design detail. What *does* change relative to simulation 6 is the surrounding discourse: conflict is present before the probe, so “confirming” the original HPI finding means confirming the **weakness of the probe**, not confirming the original consensus atmosphere.

### 3.2 Policy-action comparison

#### 3.2.1 Original five actions (simulation 6)

| # | Action (verbatim) | Beneficiaries | Instrument | Eligibility / priority | Relation |
|---|---|---|---|---|---|
| 1 | Develop a subsidy policy that prioritizes affordability and accessibility for retirees and rural communities. | Retirees; rural communities | Purchase/affordability subsidy (implied) | Priority to cost-sensitive / rural | Core |
| 2 | Invest in expanding charging infrastructure, particularly in rural areas… | Rural drivers | Public infrastructure investment | Geographic (rural first) | Complementary to 1 |
| 3 | Include provisions… to address battery longevity and maintenance concerns… | Cautious adopters (esp. seniors) | Warranty/maintenance support tied to subsidy | Concern-based | Complementary |
| 4 | Design inclusive policies… diverse demographics… | Broad / equity frame | Design principle | Soft equity criterion | Meta-requirement |
| 5 | Engage in advocacy efforts to promote comprehensive subsidy policies and robust infrastructure… | Public / coalition | Advocacy (non-fiscal) | N/A | Process support |

**Different vs conflicting (original):** all five are **aligned**. They form one package (money + chargers + maintenance reassurance + inclusion + advocacy). No rival design (e.g., luxury-first caps vs means-tested grants) is present.

#### 3.2.2 Replication action patterns

Across 10 runs, 40 action items were generated (3–5 per run). Dominant coded themes in action text:

| Theme in action items | Count (of 40) |
|---|---|
| Rural charging / infrastructure | 27 |
| Explicit subsidy language | 17 |
| Affordability / cost | 8 |
| Battery / range / maintenance | 5 |
| Retiree / senior | 2 |
| Inclusion / equity | 1 |

Recurring action *types* (not verbatim):

1. **Dual subsidy** — pair vehicle-purchase support with infrastructure expansion (most common).  
2. **Rural-first infrastructure** — pilots, needs assessments, rural chargers.  
3. **Education / simplification** — workshops for older or less tech-savvy users.  
4. **Studies / task forces** — gap analyses, feasibility, manufacturer partnerships.  
5. **Occasional alternatives** — hybrid interim subsidies; reallocation from other renewables; luxury-EV subsidy evaluation (run 1–2).

**Conflicts (from unresolved-disagreement summaries).** In **10/10** runs the summary model listed unresolved tension, most often:

- vehicle-price subsidies **versus** charging-infrastructure investment;  
- rural versus urban priority;  
- technology/education supports versus hard infrastructure;  
- universal versus geographically targeted subsidies.

So, relative to simulation 6, replications **do** surface genuine conflicts—primarily as competing *priorities within one subsidy agenda*, not as mutually exclusive policy regimes.

### 3.3 Profile-to-response traceability

#### 3.3.1 Original simulation 6

| Persona | Profile anchors | Observed contribution | Trace |
|---|---|---|---|
| Liisa | Retiree; cost; rural charging; battery longevity | Set the opening agenda in nearly those terms | Strong |
| Juho | Rural farm; practicality; infrastructure | Echoed rural/practical constraints | Strong |
| Aino | Urban sustainability; EV adoption; policy | Inclusive / green framing; endorsed others’ rural/retiree needs | Strong on goals; borrowed others’ barriers |
| Mikko | Tech early adopter; infrastructure/price frustrations | Battery tech, remote services, green transition | Strong |

No per-message retrieval evidence is stored for simulations; reverse-RAG scores from persona *generation* are out of scope here.

#### 3.3.2 Replication marker rates (30 messages per persona)

| Persona | Strongest markers (hit rate) | Weak / absent |
|---|---|---|
| Liisa | charging 53%; rural 53%; cost 33%; afford 30%; retire 17% | battery 0%; maintenance 0%; senior 0% |
| Juho | rural 100%; infrastructure 93%; range 93%; charging 80%; farm 40% | cost only 3% |
| Aino | policy 70%; sustain 40%; urban 27% | inclusive 3%; community 0% |
| Mikko | infrastructure 97%; adop\* 77%; sustain 23% | technology 0%; green 0%; battery 0% |

**Interpretation.** Profiles still shape talk—especially Juho’s rural/range/infrastructure package—but the current engine’s conflict and infrastructure emphasis **downweights** some original Liisa-specific cues (battery longevity, maintenance anxiety) that dominated simulation 6. Traceability supports “profiles contributed” claims; it does not support claims of independent empirical discovery or evidence-grounded citation in-sim.

---

## 4. Discussion

### 4.1 What replicates

1. **Thin HPI probes fail.** “What about the subsidy” still does not yield amounts, caps, or eligibility rules (1/10 design-detail hits).  
2. **Subsidy + rural infrastructure** remain the agenda core.  
3. **Attribute-level traceability** remains feasible from logs + persona JSON.

### 4.2 What does not replicate (engine-qualified)

1. **Immediate consensus** from simulation 6 does **not** replicate; openings now conflict.  
2. **Five neatly complementary actions** become **dual-track actions plus unresolved priority conflicts**.  
3. **Retiree/battery** framing is less dominant than in the original Liisa-led agenda.

### 4.3 Smaller confirmatory checks

| Check | Finding |
|---|---|
| Message structure stability | 10/10 runs: 12 persona + 1 human |
| Facilitator text fidelity | Identical string in all runs |
| Agree-echo rate | 0% under current prompts (vs high in original) |
| Summary always returns actions | Yes (3–5 items each) |
| Summary always flags unresolved conflict | Yes (10/10) |
| RAG evidence availability | Still absent on simulation messages |

### 4.4 Limitations

- Single original case; replications use a newer engine.  
- Theme coding is keyword-based (transparent, but not a substitute for full qualitative coding).  
- `shared_understanding` from the summary model is not persisted on the simulation row (only unresolved disagreements map into `key_insights`).  
- No claim is made that personas represent statistically sampled Finnish publics.

---

## 5. Conclusion

Simulation 6 is usable for HPI, policy-action, and profile-trace analyses, with the HPI section documenting a **weak intervention** rather than a rich probe sequence. Ten replications **confirm** that this facilitator wording fails to elicit subsidy design detail, while showing that the current PEP engine replaces the original consensus package with **priority conflicts**—especially vehicle affordability versus charging infrastructure. Analysts should treat simulation 6 as a historical consensus case and the 53–62 series as the robustness check for intervention barrenness and agenda themes under present system behaviour.

---

## References

American Psychological Association. (2020). *Publication manual of the American Psychological Association* (7th ed.).

Amin, D., et al. (in preparation / book chapter materials). Persona Ecosystem Playground (PEP) and Finland EV transition personas. [Chapter manuscript on file.]

OpenAI API / PEP backend simulation service documentation (internal), pep-be production deployment (Railway), accessed November 17, 2026.

---

## Appendix A. Original simulation 6 — full transcript

| Turn | Speaker | Text |
|---|---|---|
| 1 | Liisa Nieminen | From my perspective, a subsidy policy for electric vehicles should prioritize affordability and accessibility, especially for retirees like myself who are cautious about costs. It's crucial to ensure widespread charging infrastructure, particularly in rural areas. Additionally, it would be helpful if subsidies could address concerns about battery longevity and vehicle maintenance, making the transition less daunting for those of us unfamiliar with the technology. |
| 2 | Juho Laakso | I agree, Liisa. Making electric vehicles affordable and ensuring a robust charging infrastructure in rural areas is essential, especially for folks like us who rely on practicality. Battery longevity and maintenance are also critical concerns, as these factors directly impact operational costs and long-term sustainability for our lifestyles. |
| 3 | Aino Virtanen | Absolutely, Liisa and Juho, affordability and infrastructure are vital for widespread EV adoption. As someone focused on urban sustainability, I see the importance of inclusive policies that consider retirees and rural communities. Support in battery technology and maintenance will ease the transition and demonstrate the long-term benefits electric vehicles offer for a sustainable future. |
| 4 | Mikko Salminen | I completely agree with Liisa, Juho, and Aino. As someone who keenly follows technological advancements, I believe inclusive policies will accelerate EV adoption. Supporting battery tech and service networks, especially in remote areas, is crucial to breaking down barriers. These steps not only promote sustainability but also foster community-wide acceptance and participation in the green transition. |
| 5 | Liisa Nieminen | I appreciate everyone's insights. It's reassuring to see a shared commitment to making electric vehicles accessible to all, regardless of where we live. If policies can address our concerns about affordability and maintenance, it could make transitioning to EVs feel less daunting and more practical for seniors like myself. |
| 6 | Juho Laakso | Exactly, Liisa. Practical solutions are what make any new technology viable for people like us. If the policies address our specific needs, especially in rural areas, transitioning to electric vehicles can become a smooth process that benefits everyone while promoting sustainability. |
| 7 | **Facilitator** | **What about the subsidy** |
| 7 | Aino Virtanen | I'm glad to see this shared commitment, Liisa and Juho. By aligning policies with practical needs and expanding EV infrastructure, we can make this green transition inclusive and beneficial. Let's continue advocating for these changes to ensure everyone, regardless of location or age, can participate in creating a sustainable future. |
| 8 | Mikko Salminen | Absolutely, Aino. Our collective efforts to advocate for comprehensive subsidy policies and robust infrastructure are key. By addressing practical needs and promoting inclusive access, we encourage broader EV adoption, contributing to a sustainable future for everyone while easing the transition across various demographics. |
| 9 | Liisa Nieminen | I agree with all of you. It's encouraging to see a focus on inclusive policies and practical solutions. By considering the specific needs of rural and older populations, we can make the transition to electric vehicles not only feasible but also appealing, helping more of us contribute to a sustainable future. |
| 10 | Juho Laakso | Absolutely, Liisa. It's essential that policies cater to diverse needs, making sustainability both achievable and attractive. By ensuring rural infrastructure and affordability, we make EVs a practical choice for everyone, allowing us all to contribute effectively to a greener future. |

### Original stored summary fields

**Summary.**  
The group discussion focused on the implementation of a subsidy policy for electric vehicles (EVs), emphasizing the need for affordability and accessibility, particularly for retirees and rural communities. Participants highlighted the importance of developing a widespread charging infrastructure and addressing concerns related to battery longevity and vehicle maintenance. These measures are seen as essential for easing the transition to electric vehicles and making them a practical choice for a diverse population. The discussion underscored the necessity of inclusive policies that cater to the specific needs of different demographics, ensuring that everyone can participate in the shift towards a sustainable future.

**Key insights.**

1. Affordability and accessibility are critical for the widespread adoption of electric vehicles, particularly for retirees and rural residents.  
2. Developing a robust charging infrastructure in rural areas is essential to support the transition to electric vehicles.  
3. Addressing concerns about battery longevity and vehicle maintenance can significantly ease the transition to electric vehicles.  
4. Inclusive policies that consider the needs of diverse demographics are crucial for promoting sustainability and broader EV adoption.  
5. Community-wide acceptance and participation in the green transition can be fostered by aligning subsidy policies with practical needs.

**Action items.**

1. Develop a subsidy policy that prioritizes affordability and accessibility for retirees and rural communities.  
2. Invest in expanding charging infrastructure, particularly in rural areas, to support the practical use of electric vehicles.  
3. Include provisions in the subsidy policy to address battery longevity and maintenance concerns, making EVs a more attractive option.  
4. Design inclusive policies that cater to the specific needs of diverse demographics, ensuring equitable access to sustainable transportation.  
5. Engage in advocacy efforts to promote comprehensive subsidy policies and robust infrastructure development for broader EV adoption.

---

## Appendix B. Persona profile excerpts (set 11)

### Liisa Nieminen — “Skeptical Retiree”
- Demographics: 65, female, Rovaniemi, retired teacher, lower-middle income.  
- Frustrations: tech complexity; high EV upfront cost; limited rural charging; battery longevity/maintenance uncertainty.  
- Quote: “I need something reliable and straightforward. I'm not sure electric cars fit that bill yet…”

### Juho Laakso — “Rural Business Owner with Pragmatic Views”
- Demographics: 50, male, Jyväskylä area farm owner, middle income.  
- Frustrations: limited EV range; rural infrastructure unreadiness; high initial costs of sustainable tech.  
- Quote: “I'm open to new technology, but it needs to make sense for rural living and farming.”

### Aino Virtanen — “Eco-conscious City Dweller”
- Demographics: 35, non-binary, Turku, environmental consultant, upper-middle income.  
- Goals: sustainable living; increase EV adoption; influence renewable policy.  
- Frustrations: slow policy change; limited EV infrastructure; low public awareness.

### Mikko Salminen — “Young Professional Embracing Change”
- Demographics: 28, male, Helsinki, software developer, middle income.  
- Goals: reduce carbon footprint; transition to electric lifestyle; support green policy.  
- Frustrations: limited charging; high purchase price; lack of incentives; inconsistent information.

Full nested JSON: `data/original_participants.json`.

---

## Appendix C. Replication catalogue

| Run | Sim ID | Status | Persona msgs | Human | # Actions | Tokens |
|---|---|---|---|---|---|---|
| 1 | 53 | stopped | 12 | 1 | 5 | 731 |
| 2 | 54 | stopped | 12 | 1 | 4 | 686 |
| 3 | 55 | stopped | 12 | 1 | 3 | 734 |
| 4 | 56 | stopped | 12 | 1 | 4 | 675 |
| 5 | 57 | stopped | 12 | 1 | 3 | 729 |
| 6 | 58 | stopped | 12 | 1 | 3 | 720 |
| 7 | 59 | stopped | 12 | 1 | 4 | 649 |
| 8 | 60 | stopped | 12 | 1 | 4 | 687 |
| 9 | 61 | stopped | 12 | 1 | 5 | 697 |
| 10 | 62 | stopped | 12 | 1 | 5 | 722 |

Machine-readable transcripts and per-run action/disagreement lists: `data/run_XX.json`, `data/replications_transcripts.csv`, `data/replications_analysis.json`.

---

## Appendix D. All replication action items (verbatim)

### Run 1 (sim 53)
1. Conduct a comprehensive study to identify key infrastructure gaps in both urban and rural areas.  
2. Develop a subsidy policy that balances incentives for both vehicle affordability and infrastructure expansion.  
3. Initiate a pilot program focusing on rural areas to test longer-range EVs and expanded charging networks.  
4. Engage with EV manufacturers to explore the development of simpler, user-friendly models to address concerns about technology complexity.  
5. Set up a task force to evaluate the impact of luxury EV subsidies on overall adoption and sustainability goals.

### Run 2 (sim 54)
1. Develop a subsidy policy that equally prioritizes EV purchase incentives and charging infrastructure expansion.  
2. Focus initial infrastructure development efforts on rural areas to ensure broader accessibility.  
3. Consider interim solutions like hybrid vehicle subsidies while infrastructure and EV technology improve.  
4. Conduct a feasibility study on the impact of reallocating funds from other renewable energy projects to EV subsidies.

### Run 3 (sim 55)
1. Develop a policy package that includes both electric vehicle subsidies and investments in charging infrastructure.  
2. Conduct a feasibility study on integrating solar-powered charging stations in rural areas.  
3. Initiate a research project to advance battery technology, focusing on increasing range for rural applications.

### Run 4 (sim 56)
1. Develop a dual subsidy policy that addresses both EV purchases and infrastructure development simultaneously.  
2. Prioritize substantial investment in rural charging stations to address range limitations.  
3. Include educational programs in the subsidy policy to assist less tech-savvy individuals in understanding EV technology.  
4. Accelerate governmental support to ensure timely implementation of subsidy policies.

### Run 5 (sim 57)
1. Conduct a comprehensive analysis to identify strategic locations for new charging stations, focusing on rural and underserved areas.  
2. Develop a dual subsidy policy that addresses both EV purchase cost reduction and infrastructure expansion.  
3. Implement educational workshops and consultations tailored for older adults to facilitate the transition to electric vehicles.

### Run 6 (sim 58)
1. Conduct a study to evaluate the impact of electric vehicle range and infrastructure on rural adoption rates.  
2. Develop educational programs that simplify electric vehicle technology for potential users.  
3. Design a subsidy policy that integrates both vehicle affordability and infrastructure expansion.

### Run 7 (sim 59)
1. Develop a strategic plan for expanding charging infrastructure, with a focus on both urban and rural areas.  
2. Create a simplified subsidy application process to minimize bureaucratic barriers for potential EV users.  
3. Initiate a pilot program to test the impact of combined vehicle and infrastructure subsidies in select regions.  
4. Conduct a stakeholder analysis to better understand the specific needs of different user groups, including rural communities and older adults.

### Run 8 (sim 60)
1. Develop a comprehensive plan to expand charging infrastructure, with a focus on rural areas.  
2. Conduct an assessment of current EV technology to identify improvements needed for rural applicability.  
3. Design subsidy programs that include components for both reducing vehicle costs and infrastructure expansion.  
4. Create educational programs to support the adoption of new EV technology and reduce the learning curve for new users.

### Run 9 (sim 61)
1. Develop a comprehensive subsidy policy that balances vehicle affordability with infrastructure development.  
2. Initiate pilot programs focusing on expanding rural charging infrastructure as a priority.  
3. Create educational programs to simplify the transition to EVs for everyday users.  
4. Conduct a needs assessment to identify specific rural areas where infrastructure is most lacking.  
5. Establish a timeline for policy implementation that addresses both immediate and long-term goals.

### Run 10 (sim 62)
1. Develop a detailed subsidy policy proposal that includes both vehicle affordability and infrastructure expansion components.  
2. Conduct a needs assessment to identify specific rural areas that require infrastructure development.  
3. Propose a phased implementation plan that prioritizes infrastructure in underserved areas.  
4. Evaluate potential partnerships with EV manufacturers to address vehicle range limitations.  
5. Organize a follow-up meeting to refine the subsidy policy based on identified priorities and regional needs.

---

## Appendix E. File inventory

```
reports/sim6_subsidy_hpi/
├── APA_Report_Sim6_Subsidy_HPI.md          ← this report
└── data/
    ├── original_simulation.json
    ├── original_messages.json
    ├── original_participants.json
    ├── original_transcript.csv
    ├── replications_meta.json
    ├── replications_analysis.json
    ├── replications_transcripts.csv        ← 130 message rows
    └── run_01.json … run_10.json           ← full per-run payloads
```

---

*End of report.*
