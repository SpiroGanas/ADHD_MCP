# ADHD and Autism (ASD) in Adults and US Veterans/Service Members: Self-Harm and Suicide Risk, Mechanisms, and EHR Signals That Should Trigger a Formal Screening Referral

Research notes compiled 2026-11-26.

**How these notes were sourced (read first).** This session could not reach `pubmed.ncbi.nlm.nih.gov`, the NCBI E-utilities API or `www.ebi.ac.uk` (Europe PMC). The session's network policy blocked them, and those hosts must be allowed before the abstracts can be checked directly. Every number below came from web-search retrieval of journal pages, PMC pages, publisher abstracts, press releases or secondary citations. Each finding is tagged:
- **[primary]**: the figure appeared in a snippet or summary of the paper's own page (journal, PMC or publisher).
- **[secondary]**: the figure came from a citing article, a press release, news coverage or a vendor or recruiting blog.

Verify every [secondary] figure against the original abstract before it is used to set model weights. Anything that was recalled but could not be confirmed is listed under Gaps rather than reported as a finding.

---

## Q1. How common are adult ADHD and autism (often undiagnosed) in veterans, service members and VA patients, and how do military accession standards affect this?

### Takeaway
ADHD is common in the military population. Army STARRS found it among the most prevalent disorders in soldiers (about 6–7%), at higher rates than in civilians, even though DoD accession standards screen it out. VA ADHD diagnoses rose about 60% from FY2018 to FY2022 (to about 111,000 patients). No credible estimate exists for autism prevalence in veterans or service members. Accession standards make both conditions disqualifying in most cases, which gives applicants a strong reason not to disclose them. The likely result is a pool of undocumented ADHD and autism in service members and veterans, which an EHR flagging tool would have to infer from indirect signals.

### Cited Findings
**US civilian adult baselines (labelled civilian)**
- About 6.0% of US adults (about 15.5 million) reported a current ADHD diagnosis in October–November 2023 (NCHS Rapid Surveys System). More than half of them were diagnosed at age 18 or older. Source: Staley BS et al., MMWR 2024;73(40):890–895, doi:10.15585/mmwr.mm7340a1 [primary]. — [PMC11466376](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11466376/); [Healio summary](https://www.healio.com/news/psychiatry/20241023/one-in-16-us-adults-estimated-to-have-adhd-with-more-than-half-diagnosed-in-adulthood)
- **Landmark, older study:** the National Comorbidity Survey Replication estimated current adult ADHD at 4.4% in adults aged 18–44 (n = 3,199). Prevalence was 5.4% in men and 3.2% in women, and most cases were untreated for ADHD even though many had received treatment for comorbid mental or substance disorders. Source: Kessler RC et al., Am J Psychiatry 2006;163(4):716–723, doi:10.1176/ajp.2006.163.4.716 [primary]. — [Psychiatry Online](https://psychiatryonline.org/doi/10.1176/ajp.2006.163.4.716); [NIMH statistics](https://www.nimh.nih.gov/health/statistics/attention-deficit-hyperactivity-disorder-adhd)
- About 5.4 million US adults, or 2.21% of adults aged 18–84 in 2017, were modelled to be autistic, counting both diagnosed and undiagnosed people. State estimates ranged from 1.97% (Louisiana) to 2.42% (Massachusetts). Source: Dietz PM et al., J Autism Dev Disord 2020;50(12):4258–4266 [primary abstract; secondary for the figures]. — [PubMed 32390121](https://pubmed.ncbi.nlm.nih.gov/32390121/); [BibBase record](https://bibbase.org/network/publication/dietz-rose-mcarthur-maenner-nationalandstateestimatesofadultswithautismspectrumdisorder-2020)
- **Underdiagnosis evidence (UK primary care, civilian):** at the end of 2018, 1.22% of males and 0.35% of females in England had autism recorded in their GP record. A King's College London reanalysis of O'Nions et al. (Lancet Reg Health Eur 2023;29) concluded that more than 89% of autistic adults aged 40 or older are undiagnosed [secondary]. — [O'Nions 2023 (ResearchGate)](https://www.researchgate.net/publication/370222235_Autism_in_England_assessing_underdiagnosis_in_a_population-based_cohort_study_of_prospectively_collected_primary_care_data); [KCL news](https://www.kcl.ac.uk/news/up-to-90-of-middle-aged-and-older-autistic-adults-are-undiagnosed-in-the-uk-new-review-finds)

**Military: Army STARRS**
- Among non-deployed soldiers, 25.1% met criteria for at least one common DSM-IV disorder in the past 30 days, against 11.6% in an adjusted civilian comparison sample. 30-day disorders with onset before enlistment were also more common in soldiers (19.2% vs 10.6%). Source: Kessler RC et al., JAMA Psychiatry 2014;71(5):504–513 [secondary for the figures]. — [PMC4057988](https://pmc.ncbi.nlm.nih.gov/articles/PMC4057988/); [JAMA Psychiatry](https://jamanetwork.com/journals/jamapsychiatry/fullarticle/1835338)
- STARRS reported ADHD and intermittent explosive disorder (IED) among the most common disorders in soldiers, at higher rates than in civilians [secondary: NIMH/STARRS press coverage]. — [Social Work Today](https://www.socialworktoday.com/news/dn_032614.shtml); [Behavioral Health News](https://behavioralhealthnews.org/suicide-in-the-military-army-nih-funded-study-points-to-risk-and-protective-factors/). A later paper citing Kessler et al. gives 30-day ADHD prevalence in non-deployed soldiers as about 7.0% [secondary]. — [Howlett 2018 author manuscript](https://onlinelibrary.wiley.com/doi/am-pdf/10.1002/jts.22347)
- In Army brigade combat teams deploying to Afghanistan, weighted pre-deployment ADHD prevalence was 6.1%. Source: Howlett JR et al., J Trauma Stress 2018;31(6):909–918, doi:10.1002/jts.22347 [primary]. — [PMC6386189](https://pmc.ncbi.nlm.nih.gov/articles/PMC6386189); [Wiley](https://onlinelibrary.wiley.com/doi/10.1002/jts.22347)

**VA / VHA**
- The VA Office of Inspector General (report 22-03013-129, 4 April 2024) reviewed a rise in ADHD diagnoses and stimulant prescriptions in VHA from FY2018 through FY2022. It found that documentation supporting ADHD diagnoses and stimulant prescribing was often unstandardized and poorly supported, with growth in new prescriptions from primary care. It recommended that prescribers establish a diagnosis through a complete, documented assessment before starting a stimulant [primary]. — [VA OIG report page](https://www.vaoig.gov/reports/national-healthcare-review/deficiencies-attention-deficit-hyperactivity-disorder-diagnostic); [OIG PDF](https://www.vaoig.gov/sites/default/files/reports/2024-04/vaoig-22-03013-129.pdf)
- VHA patients with an ADHD diagnosis rose almost 60%, from about 70,000 (FY2018) to about 111,300 (FY2022). Stimulant prescriptions for ADHD patients rose 53%, from about 41,000 to about 62,500 [secondary: Military.com coverage of the OIG report]. — [Military.com, 5 April 2024](https://www.military.com/daily-news/2024/04/05/veteran-prescriptions-addictive-adhd-drugs-are-not-being-properly-vetted-and-tracked-watchdog-says.html)
- A VA Evidence Synthesis Program report (November 2024, "ADHD and Substance Use Disorders") notes a rise in ADHD diagnoses among veterans over the past decade [primary]. — [VA HSR&D ESP PDF](https://www.hsrd.research.va.gov/publications/esp/adult-adhd.pdf)
- In 2021–2022 VA data, homeless veterans were less likely than independently housed veterans to receive a stimulant (aOR 0.80). Risky or potentially inappropriate stimulant prescriptions were more common among homeless and HUD-VASH veterans [primary abstract]. — [PubMed 41534506](https://pubmed.ncbi.nlm.nih.gov/41534506/)
- Among veterans with TBI, ADHD diagnoses rose over time but stimulant use among those with ADHD did not [primary abstract, truncated]. — [Am J Med 2025 (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0002934325007028)

**Autism in veterans and service members**
- No published estimate of autism prevalence in US veterans or service members was found. A clinician's column (August 2026) states there are "no robust estimates of autism prevalence among U.S. veterans" and no longitudinal studies of suicide risk or utilization in autistic veterans. It reports anecdotally that veterans are often first diagnosed with PTSD, depression, GAD, ADHD or TBI before recognising lifelong autistic traits [secondary, opinion]. — [Psychology Today, "The Clockwork Men"](https://www.psychologytoday.com/us/blog/the-forgotten-women/202608/the-clockwork-men)
- Board of Veterans' Appeals decisions show veterans seeking service connection for ASD. In one 2023 decision the Board remanded because no VA examination had been done [primary, single case]. — [BVA A23032475](https://www.va.gov/vetapp23/Files11/A23032475.txt)
- Military-connected autism research concerns dependents rather than service members: a 2025 qualitative study of military and veteran families, and a National Academies review of the TRICARE Comprehensive Autism Care Demonstration. — [Mil Med 2025, PubMed 39423114](https://pubmed.ncbi.nlm.nih.gov/39423114/); [NAP 29139](https://www.nationalacademies.org/read/29139/chapter/4)

**DoD accession standards (DoDI 6130.03, Volume 1)**
- Under paragraph 6.28.a (as described by secondary sources), ADHD is disqualifying if any one of the following applies:
  - an IEP, 504 Plan or work accommodations after the 14th birthday;
  - a comorbid mental disorder;
  - ADHD medication prescribed in the previous 24 months;
  - documented adverse academic, occupational or work performance.

  One source says the current version is Change 6, effective 3 February 2026 [secondary; recruiting-guide sources]. — [Military.com join guide](https://www.military.com/join-the-military/eligibility-requirements/joining-the-military-with-anxiety-or-adhd); [MilitaryPrepHub ADHD](https://www.militaryprephub.com/blog/can-you-join-military-with-adhd.html); [FedLaws](https://fedlaws.org/dodi-6130-03-military-medical-standards-and-the-waiver-process/)
- **Conflicting reports:** secondary sources say the Medical Accession Records Pilot (MARP) lets applicants with ADHD enlist without a waiver after 12 or more consecutive months off medication, and that ADHD was among the original pilot conditions. This conflicts with the 24-month rule [secondary]. — [MilitaryPrepHub](https://www.militaryprephub.com/blog/can-you-join-military-with-adhd.html); [Garrison Ledger](https://www.garrisonledger.com/guides/adhd-military-diagnosis-career-guide)
- Autism spectrum disorder is disqualifying for accession. One source says it can be considered for a waiver [secondary]. — [MilitaryPrepHub autism](https://www.militaryprephub.com/blog/can-you-join-military-with-autism.html)
- ADHD reportedly does not appear in DoDI 6130.03 Volume 2, the retention standards [secondary]. — [Garrison Ledger](https://www.garrisonledger.com/guides/adhd-military-diagnosis-career-guide)

### Inferences
- Accession rules penalise any documented ADHD or autism history: medication, accommodations, academic problems or comorbidity. Applicants and families therefore have reason to stop medication, avoid evaluation or not disclose. Service members and veterans are probably enriched for undocumented, untreated ADHD and autism, especially masked autism and the inattentive presentation of ADHD. STARRS finding ADHD prevalence above civilian levels despite screening is consistent with this.
- Because ADHD is not a retention criterion, people may first be diagnosed during service or at the VA. The roughly 60% VHA growth suggests many veterans are now being diagnosed as adults. Absence of an F90 code in a VA chart is therefore weak evidence of absence.
- The VA OIG findings imply that existing VHA ADHD diagnoses vary in quality. A flagging tool should not treat a VHA F90.x code as a gold-standard label for model training without chart validation.

### Gaps
- The exact ADHD prevalence and pre-enlistment-onset row in Kessler 2014, Table 2 could not be read; the 7.0% figure is secondary. The STARRS new-soldier lifetime prevalence paper (Rosellini 2015, [PubMed 25338841](https://pubmed.ncbi.nlm.nih.gov/25338841/)) was not reviewed.
- The current official text of DoDI 6130.03 Vol 1 (esd.whs.mil) was not reached. The 24-month vs 12-month medication-free rule, MARP status, and how MHS GENESIS record-sharing affects ADHD/ASD disqualifications are unverified.
- No US data were found on ADHD or ASD prevalence among VHA users relative to all US veterans, or on the proportion who are undiagnosed. No veteran autism prevalence or suicide data exist in what was found.
- The global adult ADHD meta-analysis (Song P et al., J Glob Health 2021; [PMC7916320](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7916320/)) was listed in results, but its figures (recalled as about 2.6% persistent and about 6.8% symptomatic adult ADHD) were not confirmed.

---

## Q2. What are the best effect-size estimates linking ADHD to self-harm, suicidal ideation, suicide attempts and suicide death in adults, and does treatment reduce the risk?

### Takeaway
Across meta-analyses and Nordic registries, ADHD carries roughly 2–4x higher odds of suicide attempts and 3.5–4.5x higher odds of ideation and plans. Suicide death is about 5–7x higher, with wide confidence intervals. Most of the excess is mediated by comorbidity but not fully explained by it. Within-person and target-trial studies, including one VA cohort (OR 0.57 for suicide death in months on stimulants), suggest ADHD medication lowers suicidal behaviour, transport accidents, substance misuse and criminality by roughly 12–43%.

### Cited Findings
**Meta-analyses**
- Septier M et al., Neurosci Biobehav Rev 2019;103:109–118, doi:10.1016/j.neubiorev.2019.05.022: 57 studies across children, adolescents and adults. Pooled ORs:

  | Outcome | Pooled OR (95% CI) |
  |---|---|
  | Suicide attempts | 2.37 (1.64–3.43) |
  | Suicidal ideation | 3.53 (2.94–4.25) |
  | Suicide plans | 4.54 (2.46–8.37) |
  | Completed suicide | 6.69 (secondary sources give CI 3.24–17.37; the CI is asymmetric and may be mis-transcribed) |

  Other citing papers report adjusted values (aOR 4.50 for ideation, 2.10 for attempts) [secondary]. — [ScienceDirect abstract](https://www.sciencedirect.com/science/article/abs/pii/S0149763418309412); [ResearchGate](https://www.researchgate.net/publication/333353385_Association_between_suicidal_spectrum_behaviors_and_Attention-DeficitHyperactivity_Disorder_A_systematic_review_and_meta-analysis)
- Garas P, Balazs J et al., Brain Behav 2025 (longitudinal studies only, children and adolescents followed up; 9 studies): suicidal ideation OR 3.956 (1.996–7.841); suicide attempt OR 3.344 (1.682–6.650) [primary]. — [Wiley doi:10.1002/brb3.70618](https://onlinelibrary.wiley.com/doi/10.1002/brb3.70618); [PMC12177204](https://pmc.ncbi.nlm.nih.gov/articles/PMC12177204/)
- Garas P, Balazs J, Front Psychiatry 2020 (systematic review of long-term suicide risk in youth with ADHD), included for completeness; it is a youth review. — [PMC7779592](https://pmc.ncbi.nlm.nih.gov/articles/PMC7779592/)
- An adult-only pooled estimate for non-suicidal self-injury (NSSI) in ADHD was OR 1.85 (0.56–6.08), not significant. This reflects few adult studies [primary]. — [PMC13797376](https://pmc.ncbi.nlm.nih.gov/articles/PMC13797376)
- An adult single-study estimate cited in search results: ADHD independently associated with lifetime suicide attempt, OR 1.62 (1.08–2.44). It may come from the English Adult Psychiatric Morbidity Survey 2007 analysis [secondary; attribution uncertain]. — [J Affect Disord, APMS 2007 analysis](https://www.sciencedirect.com/science/article/abs/pii/S016503271530656X)

**Registry cohorts (civilian, Nordic)**
- Ljung T, Chen Q, Lichtenstein P, Larsson H, JAMA Psychiatry 2014;71(8):958–964 (Sweden; 51,707 people with ADHD, matched cohort plus family design): attempted suicide OR 3.62 (3.29–3.98) and completed suicide OR 5.91, both adjusted for comorbid psychiatric disorders. The familial co-aggregation design is reflected in the title, "Common etiological factors" [secondary]. — [ResearchGate](https://www.researchgate.net/publication/263431493_Common_Etiological_Factors_of_Attention-DeficitHyperactivity_Disorder_and_Suicidal_Behavior_A_Population-Based_Study_in_Sweden)
- Danish national cohort (Fitzgerald C, Dalsgaard S, Nordentoft M, Erlangsen A), Br J Psychiatry 2019 (about 2.9 million people aged 10 and over, 1995–2014):
  - suicidal behaviour (attempts plus suicides) IRR 4.7 (4.3–5.1), adjusted for sociodemographics and parental suicidal behaviour;
  - crude incidence 415.6 vs 75.5 per 100,000 person-years.

  This analysis was not adult-only. Note: the search did not independently confirm the first-author name [primary]. — [Cambridge Core](https://www.cambridge.org/core/journals/the-british-journal-of-psychiatry/article/suicidal-behaviour-among-persons-with-attentiondeficit-hyperactivity-disorder/6CECF48A64E415C871D233B2607114ED)
- **Mortality, landmark study (Dalsgaard S et al., Lancet 2015, Denmark):**
  - mortality 5.85 vs 2.21 per 10,000 person-years;
  - accidents caused 42 of 79 deaths with a known cause;
  - the mortality rate ratio was higher in women and in people diagnosed in adulthood.

  [secondary]. — [Medscape](https://www.medscape.com/viewarticle/840502); [ScienceDaily](https://www.sciencedaily.com/releases/2015/02/150225205834.htm)
- Sun S et al., JAMA Psychiatry 2019 (Sweden): unintentional injury and suicide were the leading causes of death in ADHD. Psychiatric comorbidity that developed later accounted for much of the excess unnatural-cause mortality [primary]. — [JAMA Psychiatry](https://jamanetwork.com/journals/jamapsychiatry/fullarticle/2739304)

**Treatment effects**
- Chen Q et al., BMJ 2014;348:g3769, doi:10.1136/bmj.g3769 (Swedish registers; within-patient design): no positive association between ADHD drug treatment and concurrent suicidal behaviour. Results pointed towards a protective effect, particularly for stimulants (exact HRs not retrieved) [primary]. — [ScienceDaily](https://www.sciencedaily.com/releases/2014/06/140618111728.htm); [Ovid/BMJ abstract](https://www.ovid.com/journals/bmjd/abstract/10.1136/bmj.g3769~drug-treatment-for-attention-deficithyperactivity-disorder?redirectionsource=fulltextview)
- Zhang L, … Chang Z, BMJ 2025;390:e083658, doi:10.1136/bmj-2024-083658 (target-trial emulation; 148,581 people aged 6–64 with newly diagnosed ADHD; Sweden 2007–2020; medication started within 3 months of diagnosis vs not; 2-year follow-up). First-event reductions:

  | Outcome | Reduction |
  |---|---|
  | Suicidal behaviour | about 17% (IRR about 0.83) |
  | Substance misuse | about 15% |
  | Transport accidents | about 12% |
  | Criminality | about 13% |
  | Accidental injuries | no reduction |

  Recurrent-event reductions were larger and covered all five outcomes. Effects were larger for stimulants and in people with a prior event [primary design; percentages from press coverage]. — [PMC12344785](https://pmc.ncbi.nlm.nih.gov/articles/PMC12344785/); [Semantic Scholar](https://www.semanticscholar.org/paper/ADHD-drug-treatment-and-risk-of-suicidal-substance-Zhang-Zhu/3db648f9de8786712f124931b41757e42f9bce2a); [Technology Networks](https://www.technologynetworks.com/drug-discovery/news/adhd-medications-cut-risk-of-self-harm-by-17-and-crime-by-13-403612); [HCPLive](https://www.hcplive.com/view/adhd-drugs-reduce-risk-of-suicidal-behavior-criminality-and-more)
- **VA-specific evidence.** VA patients with an active ADHD diagnosis who received stimulants, 2016–2019: months with an active stimulant prescription were associated with lower suicide mortality than months without, OR 0.57 (0.36–0.88). The authors suggest stimulants may mediate treatment of co-occurring depression and SUD [primary]. — [PMC10897683, "Stimulant medication and suicide mortality in ADHD"](https://pmc.ncbi.nlm.nih.gov/articles/PMC10897683/)
- Chang Z et al., JAMA Psychiatry 2017;74(6):597–603, doi:10.1001/jamapsychiatry.2017.0659 (US commercial claims; more than 2.3 million patients per the press release):
  - adults with ADHD vs matched controls: motor-vehicle-crash OR about 1.49 in men and about 1.44 in women;
  - within-person, months on medication: OR 0.62 in men and 0.58 in women;
  - up to 22.1% of crashes among people with ADHD were estimated to be avoidable with medication.

  [secondary for the ORs]. — [PMC10270426 commentary](https://pmc.ncbi.nlm.nih.gov/articles/PMC10270426/); [ScienceDaily](https://www.sciencedaily.com/releases/2017/05/170510132007.htm); [Ovid abstract](https://www.ovid.com/journals/japs/fulltext/10.1001/jamapsychiatry.2017.0659~association-between-medication-use-for)

**Military / veteran ADHD and suicidal behaviour**
- Army STARRS (Nock MK et al., JAMA Psychiatry 2014;71(5):514–522, doi:10.1001/jamapsychiatry.2014.30):
  - 47.0–58.2% of soldiers' lifetime suicidal behaviours began before enlistment;
  - about one-third of post-enlistment first attempts were associated with mental disorders that began before enlistment;
  - IED, whether it began before or after enlistment, predicted post-enlistment first attempts (OR about 3.7–3.8).

  The ADHD-specific OR was not visible in retrieved text [primary]. — [JAMA Psychiatry](https://jamanetwork.com/journals/jamapsychiatry/fullarticle/1835339); [PMC4100464](https://pmc.ncbi.nlm.nih.gov/articles/PMC4100464); [ScienceDaily](https://www.sciencedaily.com/releases/2014/03/140303163153.htm)

### Inferences
- **Proposed planning priors for a veteran flagging model.** ADHD vs no ADHD:
  - suicide attempt OR about 2.4–3.6;
  - suicidal ideation OR about 3.5;
  - suicidal behaviour (any) IRR about 4.7;
  - suicide death OR about 5.9–6.7 (wide CI);
  - motor-vehicle crash OR about 1.45.

  These are civilian estimates. No veteran-specific ADHD-to-suicide-attempt effect size was found.
- Medication lowers risk in within-person and target-trial designs, including one VA cohort. Identifying untreated ADHD is therefore an actionable suicide-prevention lever, not only a diagnostic exercise.
- Excess mortality is mostly unnatural (accidents, then suicide) and is higher for adult-diagnosed people and women (Dalsgaard 2015). Injury, crash and poisoning encounters belong in the flag set.

### Gaps
- Exact HRs from Chen 2014 BMJ and exact IRRs with 95% CIs from Zhang 2025 BMJ were not retrieved; only percentages from press coverage. Verify against the BMJ full text before use.
- The ADHD-specific OR for suicide attempt in Nock 2014 STARRS was not retrieved.
- No adult-only meta-analytic pooled OR for suicide attempts was found. A recent adult-specific meta-analysis may exist, but none surfaced.
- The first author of the 2019 Danish BJPsych paper was not confirmed by the search; recalled as Fitzgerald et al.
- No VA/DoD study quantifying the association between ADHD diagnosis and suicide attempt or death against veterans without ADHD was found. Only the within-ADHD stimulant study was found.

---

## Q3. What are the best effect-size estimates linking autism to suicide and self-harm, what do the camouflaging and sex-difference findings show, and is there veteran-specific data?

### Takeaway
Autistic adults have roughly 3–4x higher odds of self-harm and suicidality in meta-analysis. Danish registry rates of suicide attempts and suicide are more than 3 times higher. Swedish registry odds of suicide death are about 7.5x higher: about 9.4x without intellectual disability and about 13x in autistic women. Risk rises with later age at diagnosis. Camouflaging (masking) consistently predicts suicidality. About half of autistic adults who attempted suicide in one US health-system study had no depression diagnosis, so depression-anchored screening will miss them. No veteran-specific autism suicide data exist.

### Cited Findings
**Registries and health-system cohorts**
- Hirvikoski T, Mittendorfer-Rutz E, Boman M, Larsson H, Lichtenstein P, Bölte S, Br J Psychiatry 2016;208(3):232–238, doi:10.1192/bjp.bp.114.160192 (Sweden, matched population cohort) [primary]:
  - all-cause mortality OR 2.56 (2.38–2.76): 706 deaths (2.60%) in ASD vs 24,358 (0.91%) in the general population;
  - suicide OR 7.55 (6.04–9.44), the largest OR of any cause of death;
  - ASD without intellectual disability: suicide OR 9.40 (7.43–11.9);
  - females with ASD: suicide OR 13.05 (8.73–19.5).

  A 2025 citation analysis found 9.3% of citing papers misreported the suicide OR. — [PMC11833514](https://pmc.ncbi.nlm.nih.gov/articles/PMC11833514/); [Cambridge PDF](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/4C9260DB64DFC29AF945D32D1C15E8F2/S0007125000279385a.pdf/div-class-title-premature-mortality-in-autism-spectrum-disorder-div.pdf)
- Kõlves K, Fitzgerald C, Nordentoft M, Wood SJ, Erlangsen A, JAMA Netw Open 2021 (Denmark, about 6.56 million people aged 10 and over, 1995–2016):
  - people with diagnosed ASD had more than 3-fold higher rates of suicide attempt and suicide after adjustment for sex, age and period;
  - the suicide-attempt rate ratio increased with age at first ASD diagnosis.

  A scoping review summarises the suicide-death increase as 3.83-fold (Denmark) vs 2.56-fold (an all-cause-type figure attributed to Sweden; note the Swedish suicide OR itself is 7.55) [primary]. — [JAMA Netw Open](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2774853); [PMC12578491](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12578491/); [scoping review PMC12923620](https://pmc.ncbi.nlm.nih.gov/articles/PMC12923620/)
- Croen LA et al., Autism 2015, doi:10.1177/1362361315577517 (Kaiser Permanente Northern California adults, 2008–2012):
  - suicide attempts in 1.79% (27) of autistic adults vs 0.32% (48) of controls, about 5x;
  - only 14 of 27 autistic attempters had a depression diagnosis;
  - significantly higher rates of all major psychiatric disorders: depression, anxiety, bipolar, OCD, schizophrenia;
  - higher rates of nearly all medical conditions, including seizures, obesity, diabetes and hypertension.

  [primary]. — [SAGE](https://journals.sagepub.com/doi/abs/10.1177/1362361315577517); [eScholarship full text](https://escholarship.org/content/qt3v42r5rs/qt3v42r5rs_noSplash_fc1b05311a4f9e7cac3fd90c500372d7.pdf)
- Baker M, Lam W, Virtosu M, de Lacy N, Front Psychiatry 2026, doi:10.3389/fpsyt.2026.1940193 (Epic Cosmos US EHR data; 2,311,171 people with ICD-10-CM ASD codes; 2016–2025):
  - suicide-attempt prevalence 1.7% (38,160 people);
  - females carry a disproportionate share of attempts and peak earlier; males peak later and stay elevated into midlife;
  - effect sizes are adjusted prevalence ratios from modified Poisson regression (values not retrieved).

  [primary]. — [Frontiers](https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2026.1940193/full)
- Utah 20-year statewide study of suicide death in autism: Kirby AV et al., Autism Res 2019, doi:10.1002/aur.2076 (figures not retrieved). A 2024 commentary by Kirby et al. says evidence on whether autistic females carry higher suicide risk is mixed: two large recent studies found higher attempt risk in autistic females, while absolute suicide rates look broadly similar [primary]. — [Kirby 2019](https://onlinelibrary.wiley.com/doi/10.1002/aur.2076); [Kirby 2024, PMC11102323](https://pmc.ncbi.nlm.nih.gov/articles/PMC11102323/)

**Meta-analyses**
- Blanchard A et al., JAMA Netw Open 2021, doi:10.1001/jamanetworkopen.2021.30272 (31 studies) [primary]:
  - self-injurious behaviour OR 3.18 (2.45–4.12);
  - suicidality OR 3.32 (2.60–4.24);
  - adults: self-harm OR 3.97 (3.11–5.01) and suicidality OR 3.84 (2.78–5.30).

  One version of the paper gives overall self-harm OR 3.26 (2.74–3.89); check which version is cited. — [JAMA Netw Open](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2785235); [PMC8527356](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8527356/)
- Newell V, Phillips L, Jones C, Townsend E, Richards C, Cassidy S, Mol Autism 2023;14:12, doi:10.1186/s13229-023-00544-7 (36 studies; 48,186 autistic and possibly autistic people without intellectual disability). Pooled prevalence [primary]:
  - suicidal ideation 34.2% (27.9–40.5);
  - suicide plans 21.9% (13.4–30.4);
  - suicide attempts or behaviours 24.3% (18.9–29.6).

  — [Springer](https://link.springer.com/article/10.1186/s13229-023-00544-7); [PMC10018918](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10018918/)
- A Crisis 2024 meta-analysis (52 studies) found pooled lifetime suicidal ideation of 37.2% and suicide attempts of 15.3% [primary]. — [Hogrefe](https://econtent.hogrefe.com/doi/10.1027/0227-5910/a000922)

**Late-diagnosed adults and camouflaging**
- Cassidy S et al., Lancet Psychiatry 2014 (adults newly diagnosed with Asperger syndrome at a UK specialist clinic): 66% had lifetime suicidal ideation and 35% had planned or attempted suicide [secondary]. — [JADD 2020 editorial review](https://link.springer.com/article/10.1007/s10803-020-04643-9)
- Cassidy S, Bradley L, Shaw R, Baron-Cohen S, Mol Autism 2018;9:42 ("Risk markers for suicidality in autistic adults"): camouflaging significantly predicted lifetime suicidality [primary]. — [Cambridge repository](https://www.repository.cam.ac.uk/items/356ff321-0f9b-4204-a8c4-9f105a0cca65); [ResearchGate](https://www.researchgate.net/publication/326552278_Risk_markers_for_suicidality_in_autistic_adults)
- Cassidy et al., Suicide Life Threat Behav 2023: the association between autistic traits and lifetime suicidal thoughts was significantly mediated by camouflaging, defeat and entrapment (Integrated Motivational-Volitional model) [primary]. — [PDF via suicideinfo.ca](https://www.suicideinfo.ca/wp-content/uploads/2023/08/Suicide-Life-Threat-Behav-2023-Cassidy-Is-camouflaging-autistic-traits-associated-with-defeat-entrapment-and.pdf)
- A 2025 mixed-methods systematic review describes camouflaging as an increasingly identified, unique risk factor for suicidality in autistic adults; the mechanisms are unclear [primary]. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S3050656525000124)

**Veterans**
- No study of autism and suicide in veterans or service members was found (see Q1). — [Psychology Today](https://www.psychologytoday.com/us/blog/the-forgotten-women/202608/the-clockwork-men)

### Inferences
- **Proposed planning priors (civilian):**
  - self-harm OR about 3.2–4.0;
  - suicide attempt rate ratio about 3–5;
  - suicide death OR about 3.8 (Denmark) to 7.5 (Sweden);
  - about 9–13x in subgroups without intellectual disability and in women.
- **Why late diagnosis is the target group.** Kõlves found the attempt rate ratio rises with age at diagnosis, and Cassidy's late-diagnosed clinic sample had very high suicidality. Adults whose autism was first recognised late are the group a veteran flag would target. It is also the group most likely to be camouflaging.
- **Depression-anchored screening will miss many.** About half of autistic attempters in Kaiser had no depression code. A flag that relies only on depression or PHQ-9 positives would miss many high-risk autistic adults.

### Gaps
- Exact Kõlves 2021 aIRRs (recalled as about 3.2 for attempts and about 3.75 for suicide, with higher female IRRs) and the share with psychiatric comorbidity were not verified.
- Hirvikoski et al. 2020 (Psychol Med; individual and familial risk of suicide attempt and suicide in autism) was not retrieved.
- Effect sizes in the Utah statewide study (Kirby 2019) and the Epic Cosmos prevalence ratios (Baker 2026) were not retrieved.
- The Cassidy 2014 sample size and the "9x general population" comparison were not verified.
- No veteran or military autism suicide data exist in what was found.

---

## Q4. What mechanisms link ADHD and autism to self-harm and suicide (impulsivity, emotional dysregulation, camouflaging, late diagnosis, comorbidity)?

### Takeaway
For ADHD, three pathways are proposed:
- comorbidity (depression, SUD, conduct and personality disorders), which mediates much but not all of the risk;
- emotional dysregulation, the leading candidate mediator, with mixed direct evidence;
- shared familial or genetic liability.

Impulsivity findings are inconsistent. For autism, three pathways have support:
- camouflaging, defeat and entrapment;
- thwarted belongingness and perceived burdensomeness;
- later diagnosis.

Both conditions also raise the risk of accidents and injuries, which overlap with self-harm in EHR coding.

### Cited Findings
- **Emotional dysregulation (ADHD).** A 2023 systematic review in BMC Psychiatry identifies emotional dysregulation as a significant potential mediator of suicidal spectrum behaviours in adolescents and adults with ADHD. In adults, attentional impulsiveness and severity of inattentive symptoms predicted severe suicidal ideation [primary]. — [BMC Psychiatry 2023](https://link.springer.com/article/10.1186/s12888-023-05099-8)
- **Moderation vs mediation.** A 2025 review of adolescents found emotion dysregulation moderated the link between hyperactive-impulsive symptoms and suicidal behaviour. An older all-female study found impulsivity did not mediate the ADHD–attempt association [primary]. — [PMC12634774](https://pmc.ncbi.nlm.nih.gov/articles/PMC12634774/); [PMC12436829](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12436829/)
- **Interpersonal theory.** In non-clinical young adults, thwarted belongingness and perceived burdensomeness mediated the association between ADHD traits and suicidal ideation; parallel mechanisms were tested in autistic people with ADHD [primary]. — [Humanit Soc Sci Commun 2024](https://www.nature.com/articles/s41599-024-03578-1); [PMC10902282](https://pmc.ncbi.nlm.nih.gov/articles/PMC10902282/)
- **Shared familial liability.** Ljung 2014 used a family design ("Common etiological factors"). ADHD-related risk remained after adjustment for comorbidity (attempt OR 3.62) [secondary]. — [ResearchGate](https://www.researchgate.net/publication/263431493_Common_Etiological_Factors_of_Attention-DeficitHyperactivity_Disorder_and_Suicidal_Behavior_A_Population-Based_Study_in_Sweden)
- **Comorbidity onset.** Later-onset psychiatric comorbidity explained much of the excess unnatural-cause mortality in ADHD [primary]. — [Sun 2019, JAMA Psychiatry](https://jamanetwork.com/journals/jamapsychiatry/fullarticle/2739304)
- **Late diagnosis (ADHD).** Mortality rate ratios were higher in people diagnosed with ADHD in adulthood [secondary]. — [ScienceDaily on Dalsgaard 2015](https://www.sciencedaily.com/releases/2015/02/150225205834.htm)
- **Late diagnosis (autism).** Attempt rate ratios rose with age at ASD diagnosis [primary]. — [Kõlves 2021](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2774853)
- **Camouflaging (autism).** Camouflaging predicted suicidality (Cassidy 2018). Camouflaging, defeat and entrapment mediated the link between autistic traits and suicidality (Cassidy 2023). Pelton and Cassidy (2017) reported perceived burdensomeness and thwarted belonging as indirect pathways [primary/secondary]. — [Cambridge repository](https://www.repository.cam.ac.uk/items/356ff321-0f9b-4204-a8c4-9f105a0cca65); [SLTB 2023 PDF](https://www.suicideinfo.ca/wp-content/uploads/2023/08/Suicide-Life-Threat-Behav-2023-Cassidy-Is-camouflaging-autistic-traits-associated-with-defeat-entrapment-and.pdf)
- **Other autism risk factors.** A systematic review lists later diagnosis, social-communication difficulties, marginalisation and psychiatric comorbidity, including personality disorders [secondary]. — [ResearchGate systematic review](https://www.researchgate.net/publication/322576962_Systematic_Review_of_Suicide_in_Autism_Spectrum_Disorder_Current_Trends_and_Implications)
- **Accidents as a parallel pathway.** Unintentional injuries are the leading cause of excess death in ADHD, and medication reduces transport accidents [primary]. — [Sun 2019](https://jamanetwork.com/journals/jamapsychiatry/fullarticle/2739304); [Zhang 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12344785/)
- **ADHD and trauma exposure in soldiers.**
  - Pre-deployment ADHD predicted post-deployment PTSD, AOR 2.13 (1.51–3.00).
  - Among soldiers with no prior PTSD, AOR 2.50 (1.69–3.69); n = 4,612 Army soldiers without stimulant treatment.

  [primary]. — [Howlett 2018, PMC6386189](https://pmc.ncbi.nlm.nih.gov/articles/PMC6386189)

### Inferences
- **Military-specific pathway (hypothesis).** ADHD raises vulnerability to PTSD after deployment, and PTSD is a major suicide risk factor in veterans. That makes the chain ADHD → PTSD → suicide plausible; it is an inference, not tested.
- **Mechanisms map to EHR signals:**
  - emotional dysregulation → IED codes, anger-management referrals, BPD-type diagnoses;
  - impulsivity → injuries, crashes, SUD, legal and disciplinary problems;
  - camouflaging and social disconnection → isolation, unemployment and relationship Z-codes;
  - late diagnosis → age at first ADHD or ASD code.

### Gaps
- No study tested mediation of ADHD→suicide or ASD→suicide pathways in veterans.
- Evidence on unemployment and social isolation as mechanisms for autism suicide risk was not retrieved, beyond the interpersonal-theory constructs.

---

## Q5. Which comorbid conditions and behaviours most often precede or co-occur with undiagnosed adult ADHD or autism?

### Takeaway
Undiagnosed adult ADHD typically shows up in the record as depression and anxiety (especially in women), SUD (alcohol, stimulant, cannabis, nicotine), insomnia and delayed sleep phase, injuries and crashes, TBI, PTSD after trauma exposure, and IED or anger problems. Undiagnosed autism shows up as depression, anxiety, OCD, bipolar disorder, personality-disorder labels (especially BPD in women), seizures, obesity and diabetes, plus repeated psychiatric diagnoses that never fully fit. Treatment is commonly sought for comorbidities rather than for the core condition.

### Cited Findings
- **Adult ADHD comorbidity is very high.** The NCS-R found adult ADHD highly comorbid with many DSM-IV disorders. Most cases had been treated for comorbid mental or substance disorders but not for ADHD [primary]. — [Kessler 2006](https://psychiatryonline.org/doi/10.1176/ajp.2006.163.4.716). A secondary summary puts comorbid mood, anxiety, substance and personality disorders at 60–80% of adults with ADHD [secondary]. — [CHADD](https://chadd.org/about-adhd/general-prevalence-adults/)
- **Substance-use signals before adult ADHD diagnosis.** In Swedish EHR data, the strongest SHAP features predicting adult ADHD diagnosis 6–18 months ahead included:
  - ICD-10 F15.8 (other stimulant-related disorders);
  - Y90.3 (blood alcohol level, evidence of alcohol involvement).

  [primary]. — [Hamed 2026, Eur Psychiatry](https://www.cambridge.org/core/journals/european-psychiatry/article/early-detection-of-adults-adhd-using-electronic-health-records-a-machine-learning-study/C84C0CA747621B55238E6ED384120176); [PsyPost](https://www.psypost.org/a-new-ai-tool-spots-hidden-signs-of-adult-adhd-months-before-a-formal-diagnosis/)
- **SUD populations have high ADHD screen-positive rates.** The ASRS was validated specifically in 1,138 treatment-seeking SUD patients [primary]. — [van de Glind et al., PMC4083506](https://pmc.ncbi.nlm.nih.gov/articles/PMC4083506/). VA ESP (2024) reviewed ADHD with SUD in veterans [primary]. — [VA ESP](https://www.hsrd.research.va.gov/publications/esp/adult-adhd.pdf)
- **PTSD.** Pre-deployment ADHD predicted post-deployment PTSD in soldiers (AOR 2.13) [primary]. — [Howlett 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6386189). In Korean conscripts, current and past ADHD symptoms predicted PTSD symptoms in the first week of basic training [primary]. — [PMC3372563](https://pmc.ncbi.nlm.nih.gov/articles/PMC3372563/)
- **TBI.**
  - Umbrella review, relative risk of ADHD after TBI by severity: mild 1.2 (0.3–3.1), moderate 3.7 (0.9–9.3), severe 6.3 (2.0–14.3) [primary]. — [Nature Mental Health 2024](https://www.nature.com/articles/s44220-024-00356-5)
  - Pediatric meta-analysis (24 studies): pre-injury ADHD 16% vs 10.8% population incidence, so ADHD precedes TBI. Severe TBI raised ADHD odds (OR 4.81 at 1 year, 6.70 later) [secondary]. — [ResearchGate](https://www.researchgate.net/publication/353202539_Association_of_Attention-DeficitHyperactivity_Disorder_Diagnoses_With_Pediatric_Traumatic_Brain_Injury_A_Meta-analysis)
  - Adeyemo et al. (2014) meta-analysed ADHD as a risk factor for mild TBI (OR not retrieved). — [ResearchGate](https://www.researchgate.net/publication/264127060_Mild_Traumatic_Brain_Injury_and_ADHD_A_Systematic_Review_of_the_Literature_and_Meta-Analysis)
- **Injuries and crashes.**
  - An ADHD and injuries systematic review and meta-analysis exists [primary; pooled estimates not retrieved]. — [PMC5556632](https://pmc.ncbi.nlm.nih.gov/articles/PMC5556632/)
  - Motor-vehicle-crash OR about 1.45–1.49 in adults with ADHD [secondary]. — [PMC10270426](https://pmc.ncbi.nlm.nih.gov/articles/PMC10270426/)
  - Accidents caused 42 of 79 deaths with a known cause in the Danish ADHD cohort [secondary]. — [ScienceDaily](https://www.sciencedaily.com/releases/2015/02/150225205834.htm)
- **IED.** IED predicted first suicide attempts in soldiers (OR about 3.7–3.8), and IED and ADHD were the most common disorders in STARRS [primary]. — [Nock 2014, PMC4100464](https://pmc.ncbi.nlm.nih.gov/articles/PMC4100464)
- **Women with ADHD.**
  - Women are under-recognised and often misdiagnosed with depression [primary].
  - In a qualitative study of late-diagnosed women, 50% reported symptoms misattributed to anxiety, depression or hormones, and some considered a prior BPD diagnosis a misdiagnosis [primary].
  - Women with comorbid anxiety had the longest diagnostic delays, a mean of more than 7 years [secondary].
  - In a Spanish clinical cohort, females were diagnosed later and had more depression and anxiety [secondary].

  — [Int J Womens Health review](https://www.tandfonline.com/doi/abs/10.2147/IJWH.S511297); [Sci Rep 2025, PMC12218314](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12218314/); [Asia Pac J Soc Work qualitative study](https://www.tandfonline.com/doi/full/10.1080/18387357.2023.2268756); [PMC12840745 (late ASD/ADHD in UK women)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12840745/)
- **Sleep.** Insomnia in about 67% of people with ADHD vs 29% of controls; delayed sleep phase is more common in adults with ADHD symptoms (shorter sleep, longer sleep latency, more night-time activity). One source cites 78% insomnia in combined presentation [secondary, single narrative review]. — [Int J Womens Health review](https://www.tandfonline.com/doi/abs/10.2147/IJWH.S511297)
- **Autism comorbidity (Kaiser adults).** Higher rates of depression, anxiety, bipolar disorder, OCD, schizophrenia and suicide attempts, and of nearly all medical conditions, including seizures, obesity, diabetes and hypertension [primary]. — [Croen 2015](https://journals.sagepub.com/doi/abs/10.1177/1362361315577517)
- **Prior labels in autistic veterans.** Veterans with unrecognised autism are anecdotally first labelled with PTSD, depression, GAD, ADHD or TBI [secondary, opinion]. — [Psychology Today 2026](https://www.psychologytoday.com/us/blog/the-forgotten-women/202608/the-clockwork-men)
- **Suicide attempts in autism by comorbidity.** In Epic Cosmos, suicide attempts in autism are concentrated in people with psychiatric comorbidity (adjusted prevalence ratios by comorbidity were modelled); a 2026 preprint models attempt prediction in autism with comorbid mood or psychotic disorders [primary]. — [Baker 2026](https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2026.1940193/full); [medRxiv preprint](https://www.medrxiv.org/content/10.64898/2026.09.25.26364048v1.full)
- **Medicaid data (2026).** Co-occurring mental, neurodevelopmental and neurological conditions in autistic Medicaid beneficiaries were quantified (figures not retrieved). — [JADD 2026](https://link.springer.com/article/10.1007/s10803-026-07324-1)

### Inferences
- Comorbidities have low specificity on their own: depression, anxiety and SUD are common in all veterans. Flag value will come from combinations, for example:
  - early-onset or treatment-resistant depression plus SUD plus injury or crash history;
  - multiple psychiatric diagnoses that change over time;
  - BPD or IED labels in a woman with ADHD- or autism-like functional history.
- Pre-deployment ADHD predicts PTSD, and pre-injury ADHD predicts TBI. In veterans with PTSD or TBI, attention and executive complaints may be wrongly attributed wholly to PTSD or TBI. A flag should prompt clinicians to ask about childhood onset, before service, which the DIVA-5 and WURS are designed to capture.

### Gaps
- No quantitative estimates were retrieved for these associations in adults:
  - ADHD with eating disorders (binge eating, bulimia);
  - ADHD with BPD;
  - autism with GI disorders or IBS, Ehlers-Danlos/hypermobility, epilepsy (beyond the Kaiser "seizure" finding), gender dysphoria, or sensory over-responsivity;
  - autism misdiagnosed as BPD in women.
- No veteran-specific comorbidity profiles for ADHD or ASD were found.
- No quantitative study of "multiple failed antidepressant trials" as a marker of undiagnosed ADHD or ASD was found.

---

## Q6. Which validated adult screening instruments exist, how accurate are they, and are any already captured in VA EHRs?

### Takeaway
For ADHD, the 6-item ASRS-5 (DSM-5) performs best in general-population validation (sensitivity 91%, specificity 96%, AUC 0.94). Specificity falls in clinical samples (74%) and in SUD populations (about 0.66–0.70). The older ASRS v1.1 Part A has high specificity but modest sensitivity. For autism, the AQ-10 (recommended by NICE for deciding referral) and the RAADS-14 are reasonable, but their positive predictive value in referral clinics is low. CAT-Q measures camouflaging and is not a diagnostic screen. No evidence was found that the ASRS, AQ or RAADS is a standard structured field in VA EHRs.

### Cited Findings
- **ASRS v1.1, 6-item Part A (Kessler 2005; 154 NCS-R clinical reappraisal respondents).** Sensitivity 68.7% and specificity 99.5%, against 56.3% and 98.3% for the full 18 items [secondary]. — [ASRS summary](https://www.adhdtestonline.net/blog/adhd-asrs-scale); [Penn State record](https://pure.psu.edu/en/publications/the-adult-adhd-self-report-scale-for-screening-for-adult-attentio/)
- **ASRS in SUD patients (van de Glind et al. 2013; 1,138 treatment-seeking SUD patients).** Sensitivity 0.84 and specificity 0.66 at admission; best balance at a cut-off of 14 or more (0.81/0.70) [primary]. — [PMC4083506](https://pmc.ncbi.nlm.nih.gov/articles/PMC4083506/)
- **ASRS-5, 6-item DSM-5 version (Üstün B, Adler LA, … Kessler RC, JAMA Psychiatry 2017).** Cut-off 14 or more [secondary]:

  | Sample | Sensitivity | Specificity | AUC |
  |---|---|---|---|
  | General population | 91.4% | 96.0% | 0.94 |
  | Adult ADHD clinic | 91.9% | 74.0% | 0.83 |

  — [ASRS summaries](https://lifebylogic.com/glossary/asrs-screener/); [hiboop ASRS page](https://hiboop.com/assessments/asrs/)
- **AQ-10 adult (Allison, Auyeung, Baron-Cohen 2012).** At cut-off 6: sensitivity 0.88, specificity 0.91, PPV 0.85. NICE recommends the AQ-10 for deciding whether a full autism assessment is needed [secondary]. — [Sizoo et al. 2015 comparison (ResearchGate)](https://www.researchgate.net/publication/279251183_Predictability_of_Self-report_Questionnaires_RAADS-R-NL_AQ-28_and_AQ-10_in_the_Assessment_of_Autism_Spectrum_Disorders_in_Adults); [AIDE Canada](https://aidecanada.ca/resources/learn/asd-id-core-knowledge/screening-tests-and-tools-for-autism-in-adulthood-examples-and-cautions)
- **Real-world performance in a Dutch referral clinic (Sizoo et al. 2015).** RAADS-R had the highest sensitivity (73%); the AQ short forms had the highest specificity (70–72%) [secondary]. — [ResearchGate](https://www.researchgate.net/publication/279251183_Predictability_of_Self-report_Questionnaires_RAADS-R-NL_AQ-28_and_AQ-10_in_the_Assessment_of_Autism_Spectrum_Disorders_in_Adults)
- **Conflicting RAADS-R figures.** Vendor sites claim sensitivity above 97% (from Ritvo 2011's development sample). This conflicts with the referral-clinic data above. In one clinic, a score above cut-off carried only a 34.7% chance of an autism diagnosis. A 2024 psychometric study concluded the RAADS-R lacks sufficient accuracy as a stand-alone screen [secondary/primary]. — [PubMed 38305196](https://pubmed.ncbi.nlm.nih.gov/38305196/); [AIDE Canada](https://aidecanada.ca/resources/learn/asd-id-core-knowledge/screening-tests-and-tools-for-autism-in-adulthood-examples-and-cautions)
- **RAADS-14 Screen (Eriksson JM et al., BMC Psychiatry 2013; adult psychiatric outpatients).** Cut-off 14 or more: sensitivity 97%, specificity 46–64% [primary]. — [PMC3907126](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3907126/)
- **CAT-Q (Camouflaging Autistic Traits Questionnaire).** Measures camouflaging; it is not designed for diagnostic screening [secondary]. — [ScienceWorks comparison](https://www.scienceworkshealth.com/post/adult-autism-screening-scores-what-aq-10-raads-14-and-cat-q-can-and-cannot-tell-you)
- **VA documentation.** The VA OIG found VHA ADHD diagnostic documentation was often unstandardised and lacked appropriate support, which implies validated instruments are not consistently recorded [primary]. — [VA OIG 2024](https://www.vaoig.gov/reports/national-healthcare-review/deficiencies-attention-deficit-hyperactivity-disorder-diagnostic)

### Inferences
- **Suggested two-stage workflow.** Use the EHR flag first, then the ASRS-5 for ADHD and the AQ-10 or RAADS-14 for autism, then structured diagnostic assessment (DIVA-5 or ACE+ for ADHD; ADOS-2 Module 4 or ADI-R plus clinical interview for autism).
- **Expect low PPV in VA.** High comorbidity in VA mental health populations (PTSD, SUD, TBI) will lower screener specificity, as the SUD and clinic validations show. The EHR flag should therefore set the pre-test probability and the screener should confirm, not the other way round.
- **Masking blunts self-report.** Self-report autism screeners may under-detect camouflaging women and veterans. A negative AQ-10 should not override a strong EHR pattern.

### Gaps
- Primary accuracy figures were not retrieved for:
  - WURS (recalled: 25-item, cut-off 46, sensitivity about 86%, specificity about 99%, Ward 1993 — unverified);
  - DIVA-5 (a structured diagnostic interview rather than a screen);
  - the CAT-Q;
  - the Ashwood 2016 AQ referral-clinic study (Psychol Med).
- Whether any VA CPRS/Cerner (Oracle Health) clinical reminder, Mental Health Assistant instrument or Primary Care Mental Health Integration template captures ASRS, AQ-10 or RAADS scores as structured data was not found. VA's mandated screens (PHQ-2/9, C-SSRS/VA Risk ID, AUDIT-C, PC-PTSD-5, TBI screen) were not verified in this pass but are likely structured inputs.
- No veteran-specific validation of the ASRS, AQ-10 or RAADS was found.

---

## Q7. Are there published EHR- or registry-based prediction models or computable phenotypes for adult ADHD or autism, and how well do they perform?

### Takeaway
Few adult models exist. The best directly relevant one is a 2026 Swedish primary and secondary care EHR model that predicts adult ADHD diagnosis 6 months in advance with AUC 0.79 (sensitivity 0.80, specificity 0.77), using only clinical codes and demographics; substance-related codes were top predictors. Reviews of neurodevelopmental-disorder EHR models report AUCs above 0.75 but sensitivity usually below 75%. No adult autism EHR detection model was found. US EHR data (Epic Cosmos) now support large ICD-based autism cohorts.

### Cited Findings
- **Hamed O, Etminani F, Jacobsson P, Davidsson T, Eur Psychiatry 2026;69 ("Early detection of adults ADHD using electronic health records: A machine learning study").** Region Halland, Sweden, Regional Health Care Information Platform; 2,973 adults with ADHD; controls were adults referred to psychologists without ADHD [primary]:

  | Prediction horizon | AUROC | Notes |
  |---|---|---|
  | 6 months before diagnosis | 0.79 (0.76–0.81) | sensitivity 0.80, specificity 0.77 |
  | 12 months | 0.76 | |
  | 18 months | 0.75 | |

  Key SHAP features included F15.8 (stimulant-related disorder) and Y90.3 (blood alcohol evidence). The authors conclude that clinical codes and demographics alone support early, low-cost detection. — [Cambridge Core](https://www.cambridge.org/core/journals/european-psychiatry/article/early-detection-of-adults-adhd-using-electronic-health-records-a-machine-learning-study/C84C0CA747621B55238E6ED384120176); [PMC13122517](https://pmc.ncbi.nlm.nih.gov/articles/PMC13122517)
- **Review of ML on registers and EHRs for neurodevelopmental disorders (J Neurodev Disord 2024).** Sensitivity was below 75% in most studies, while AUC was above 0.75. The best performers (AUC above 0.8) used deep neural networks or tree-based models with subject-level past medical history [primary]. — [PMC11566279](https://pmc.ncbi.nlm.nih.gov/articles/PMC11566279/)
- **Stacked ML on administrative register data in a universal healthcare system (paediatric/non-adult population).** Reported very high AUC in cross-validation; not adult and not directly comparable [primary]. — [PMC10933630](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10933630/)
- **Paediatric autism prediction from Israeli well-baby electronic data.** 780,610 children, 1,163 with ASD; not adult [primary]. — [PMC11049145](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11049145/)
- **Epic Cosmos autism cohort.** ICD-10-CM-defined cohort of 2.3 million US patients with ASD for suicide-attempt epidemiology; descriptive, not a detection model [primary]. — [Baker 2026](https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2026.1940193/full)
- **Suicide-attempt prediction within autism and comorbid mood or psychotic disorders.** 2026 preprint, not peer reviewed; metrics not retrieved. — [medRxiv](https://www.medrxiv.org/content/10.64898/2026.09.25.26364048v1.full)
- **Military suicide ML literature.** A 2025 scoping review of ML for suicide in military and veteran populations exists (arXiv) [primary]. — [arXiv 2505.12220](https://arxiv.org/pdf/2505.12220)

### Inferences
- **Realistic performance target.** An AUC of about 0.75–0.80 is realistic for a codes-plus-demographics adult ADHD flag. Adding VA-specific structured data could plausibly improve it, but this is untested. Candidate additions:
  - pharmacy fills (stimulants obtained outside VA, bupropion, multiple antidepressant switches);
  - utilisation (no-shows, ED injury visits);
  - military history (separation type, MOS, discipline);
  - NLP of notes ("trouble focusing", "since childhood", "IEP", "special ed").
- **Label noise.** Given the VA OIG findings, training labels (VHA F90.x) are noisy. Chart-validated labels or positive-predictive-value checks are needed. Combining F90.x with an ADHD medication fill plus a specialist encounter is a common computable-phenotype pattern; it is not verified here for adults.
- **No adult autism template.** No adult autism detection model was found to copy. A VA autism flag would be novel and should be framed as a referral prompt, not a diagnosis.

### Gaps
- No published US VA/DoD computable phenotype or prediction model for adult ADHD or ASD was found.
- No adult autism EHR detection model with a reported AUC was found.
- Feature lists beyond the top SHAP codes in Hamed 2026 were not retrieved.
- REACH VET (the VA suicide-risk predictive model) variables relevant to ADHD or ASD were not reviewed.

---

## Q8. Synthesis: which EHR-recordable signals should prompt referral for formal ADHD or autism evaluation in a never-diagnosed adult veteran?

### Takeaway
No validated adult veteran flag exists. The evidence above supports a rule- or ML-based flag built from combinations of the signals in the tables below, giving extra weight to suicide-relevant signals because untreated ADHD is modifiable and late-diagnosed autism carries high risk.

The signals that reach the flag (a code or a pattern in the record):
- substance-related codes, especially stimulant and alcohol;
- injuries, crashes and TBI;
- PTSD with lifelong attention complaints;
- IED, anger or BPD-type labels;
- chronic insomnia or delayed sleep phase;
- recurrent or treatment-resistant depression or anxiety, particularly in women;
- prior suicidal behaviour or self-harm without a clear depression diagnosis;
- functional, occupational, legal and social Z-codes.

### Cited Findings (evidence base for each signal class; ICD-10-CM codes from the official code set)
- ICD-10-CM codes should be validated against the current tabular list (FY2027, effective 1 October 2026). — [CDC ICD-10-CM browser](https://icd10cmtool.cdc.gov/); [CMS ICD-10](https://www.cms.gov/medicare/coding-billing/icd-10-codes)
- Self-harm codes added in FY2022 (effective 1 October 2021):
  - R45.88 (nonsuicidal self-harm);
  - Z91.51 (personal history of suicidal behavior);
  - Z91.52 (personal history of nonsuicidal self-harm).

  Sources conflict slightly on Z91.51's title. — [SMFM FY2022 codes](https://smfm.org/news/newupdated-icd-10-cm-diagnosis-codes-for-2022); [AAFP FY2022 update](https://www.aafp.org/pubs/fpm/blogs/gettingpaid/entry/icd10-update-2022.html); [CMS FY2022 guidelines](https://cms.gov/files/document/fy-2022-icd-10-cm-coding-guidelines-updated-02012022.pdf)
- The rows below are a **draft feature map**. The "Evidence" column cites the findings above; codes are standard ICD-10-CM categories and should be validated.

**Draft EHR feature map: signals pointing to possible undiagnosed ADHD (A) or autism (S)**

| # | Signal (EHR-observable) | Example codes / data elements | A/S | Evidence (see sections above) |
|---|---|---|---|---|
| 1 | Prior suicide attempt, self-harm, suicidal ideation | T14.91; X71–X83 (intentional self-harm external causes); R45.851; R45.88; Z91.51/Z91.52; T36–T50 poisonings with intent "intentional self-harm" | A, S | ADHD attempt OR 2.4–3.6 ([Septier](https://www.sciencedirect.com/science/article/abs/pii/S0149763418309412); [Ljung](https://www.researchgate.net/publication/263431493_Common_Etiological_Factors_of_Attention-DeficitHyperactivity_Disorder_and_Suicidal_Behavior_A_Population-Based_Study_in_Sweden)); ASD self-harm OR about 4 in adults ([Blanchard](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2785235)) |
| 2 | Suicide attempt **without** a depression diagnosis | Row 1 codes with no F32/F33 | S (A) | 14/27 autistic attempters had depression ([Croen 2015](https://journals.sagepub.com/doi/abs/10.1177/1362361315577517)) |
| 3 | Stimulant-related disorder or misuse; non-VA stimulant fills; urine drug screen positive for amphetamine | F15.x (esp. F15.8, F15.1x, F15.2x); pharmacy and UDS data | A | Top predictor in [Hamed 2026](https://www.cambridge.org/core/journals/european-psychiatry/article/early-detection-of-adults-adhd-using-electronic-health-records-a-machine-learning-study/C84C0CA747621B55238E6ED384120176) |
| 4 | Alcohol involvement / alcohol use disorder; positive AUDIT-C | F10.x; Y90.x; AUDIT-C | A | Y90.3 a top predictor ([Hamed 2026](https://www.cambridge.org/core/journals/european-psychiatry/article/early-detection-of-adults-adhd-using-electronic-health-records-a-machine-learning-study/C84C0CA747621B55238E6ED384120176)); SUD comorbidity ([Kessler 2006](https://psychiatryonline.org/doi/10.1176/ajp.2006.163.4.716); [VA ESP 2024](https://www.hsrd.research.va.gov/publications/esp/adult-adhd.pdf)) |
| 5 | Other SUD (cannabis, cocaine, opioids, nicotine, polysubstance) | F12.x, F14.x, F11.x, F17.2x, F19.x | A | SUD validation population for the ASRS ([PMC4083506](https://pmc.ncbi.nlm.nih.gov/articles/PMC4083506/)); medication lowers substance misuse about 15% ([Zhang 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12344785/)) |
| 6 | Motor-vehicle crashes (driver), traffic citations noted | V40–V49 (car occupant), V20–V29 (motorcycle), with S/T injury codes | A | MVC OR about 1.45–1.49; medication OR 0.58–0.62 ([Chang 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC10270426/)) |
| 7 | Repeated ED or urgent visits for accidental injuries, fractures, burns, falls | S00–T34 injury codes, W00–X58 external causes; ED encounter counts | A | Accidents were the leading cause of ADHD excess deaths ([Dalsgaard via ScienceDaily](https://www.sciencedaily.com/releases/2015/02/150225205834.htm); [Sun 2019](https://jamanetwork.com/journals/jamapsychiatry/fullarticle/2739304)); injuries meta-analysis ([PMC5556632](https://pmc.ncbi.nlm.nih.gov/articles/PMC5556632/)) |
| 8 | TBI / concussion history (especially if attention complaints said to predate injury) | S06.x; Z87.820; VA TBI screen positive | A | Pre-injury ADHD over-represented; ADHD RR rises with TBI severity ([umbrella review](https://www.nature.com/articles/s44220-024-00356-5)) |
| 9 | PTSD (esp. with lifelong inattention) | F43.10–F43.12; PC-PTSD-5 | A, S | Pre-deployment ADHD → PTSD AOR 2.13 ([Howlett 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6386189)); autistic veterans anecdotally labelled PTSD first ([Psychology Today](https://www.psychologytoday.com/us/blog/the-forgotten-women/202608/the-clockwork-men)) |
| 10 | Intermittent explosive disorder / anger-management referral | F63.81; anger-management consults | A | IED common in STARRS and predicts attempts (OR about 3.7) ([Nock 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4100464)) |
| 11 | Recurrent or early-onset depression, dysthymia, GAD; many antidepressant switches or treatment-resistant course | F32–F33, F34.1, F41.1; count of distinct antidepressants | A, S | ADHD in women often mistaken for depression ([IJWH review](https://www.tandfonline.com/doi/abs/10.2147/IJWH.S511297)); autism raises all major psychiatric diagnoses ([Croen](https://journals.sagepub.com/doi/abs/10.1177/1362361315577517)); treatment usually sought for comorbidities ([Kessler 2006](https://psychiatryonline.org/doi/10.1176/ajp.2006.163.4.716)). *Antidepressant-switch count is an inference, not directly validated.* |
| 12 | Borderline personality disorder or "emotionally unstable" label, especially in women | F60.3 | A, S | Late-diagnosed women report BPD misdiagnosis ([Asia Pac J Soc Work](https://www.tandfonline.com/doi/full/10.1080/18387357.2023.2268756)); personality disorders among autism suicide risk factors ([systematic review](https://www.researchgate.net/publication/322576962_Systematic_Review_of_Suicide_in_Autism_Spectrum_Disorder_Current_Trends_and_Implications)) |
| 13 | Bipolar disorder, OCD, schizophrenia-spectrum codes (repeatedly changing diagnoses) | F31, F42, F20–F29 | S | Raised in autistic adults ([Croen 2015](https://journals.sagepub.com/doi/abs/10.1177/1362361315577517)) |
| 14 | Social anxiety, isolation, living alone, social exclusion | F40.10/F40.11; Z60.2, Z60.4 | S (A) | Thwarted belongingness and burdensomeness pathway ([PMC10902282](https://pmc.ncbi.nlm.nih.gov/articles/PMC10902282/); [Nature HSSC](https://www.nature.com/articles/s41599-024-03578-1)). *Code mapping is an inference.* |
| 15 | Chronic insomnia; circadian rhythm disorder, delayed sleep phase; sedative-hypnotic prescriptions | G47.00, G47.01, G47.21, F51.0x | A | Insomnia about 67% vs 29%; delayed sleep phase more common ([IJWH review](https://www.tandfonline.com/doi/abs/10.2147/IJWH.S511297)) |
| 16 | Epilepsy / seizures | G40.x, R56.9 | S | Raised in autistic adults ([Croen 2015](https://journals.sagepub.com/doi/abs/10.1177/1362361315577517)) |
| 17 | Obesity, diabetes, hypertension at young age | E66, E11, I10 | S | Raised in autistic adults ([Croen 2015](https://journals.sagepub.com/doi/abs/10.1177/1362361315577517)). *Low specificity.* |
| 18 | Female sex combined with rows 11–12 or anxiety | Sex field | A, S | Women diagnosed later; longest delays with comorbid anxiety ([Sci Rep 2025](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12218314/); [IJWH](https://www.tandfonline.com/doi/abs/10.2147/IJWH.S511297)); autistic women suicide OR 13.05 ([Hirvikoski 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC11833514/)) |
| 19 | Homelessness / housing instability | Z59.0x; HUD-VASH enrollment | A | Different stimulant-prescribing patterns in homeless veterans ([PubMed 41534506](https://pubmed.ncbi.nlm.nih.gov/41534506/)). *Link to undiagnosed ADHD is an inference.* |
| 20 | Legal involvement / incarceration; criminal-justice outreach | Z65.1, Z65.3; VJO/HCRV program contacts | A | Medication lowers criminality about 13% ([Zhang 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12344785/)) |
| 21 | Academic or occupational problems; unemployment; job loss; documented "adverse performance" | Z55.x, Z56.x; VR&E enrollment | A, S | The DoD ADHD standard explicitly cites adverse academic and occupational performance ([Military.com](https://www.military.com/join-the-military/eligibility-requirements/joining-the-military-with-anxiety-or-adhd)). *Use as a flag is an inference.* |
| 22 | Attention or executive-function symptom codes without a diagnosis | R41.840, R41.844; neuropsych testing orders | A | Direct symptom capture. *Inference; no validation found.* |
| 23 | Notes and NLP mentions: "IEP", "504 plan", "special education", "childhood ADHD", "stopped meds to enlist", "Ritalin/Adderall as a kid", "sensory", "meltdown", "routine", "literal" | Clinical notes | A, S | Accession rule on IEP/504 and medication history ([MilitaryPrepHub](https://www.militaryprephub.com/blog/can-you-join-military-with-adhd.html)); masking ([Cassidy 2018](https://www.repository.cam.ac.uk/items/356ff321-0f9b-4204-a8c4-9f105a0cca65)). *NLP list is an inference.* |
| 24 | First-degree relative with ADHD or ASD (family history field) | Z81.8 / Z82.x (family history), notes | A, S | Familial co-aggregation ([Ljung 2014](https://www.researchgate.net/publication/263431493_Common_Etiological_Factors_of_Attention-DeficitHyperactivity_Disorder_and_Suicidal_Behavior_A_Population-Based_Study_in_Sweden)). *Mapping is an inference.* |

### Inferences
- **Weighting.**
  - Rows 1–8 have the strongest quantitative support for ADHD.
  - Rows 1, 2, 12, 13 and 18 have the strongest support for autism.
  - Rows 14, 17, 19, 21 and 22 are low-specificity modifiers.
  - A starting heuristic: refer when one high-weight signal co-occurs with two or more modifiers, or when two or more high-weight classes appear within roughly 3 years. Calibrate against chart-reviewed cases. The Hamed 2026 6-month horizon (AUC 0.79) suggests signals cluster in the months before diagnosis.
- **Suicide-safety gating.** Any flagged veteran with row-1 history should route through VA suicide-risk procedures first. The neurodevelopmental referral is an adjunct, justified by medication's protective associations (VA OR 0.57 for suicide death; Swedish IRR about 0.83 for suicidal behaviour).
- **Exclusions.** Suppress the flag for veterans who already have F90.x or F84.x codes. Still review F90.x quality, given the OIG findings. Consider separate logic for veterans already on stimulants for other indications (narcolepsy G47.4x, TBI-related fatigue).
- **Fairness.** Women are probably under-flagged by injury, crash and legal features, which skew male. A sex-stratified model or sex-specific thresholds is advisable, consistent with the female underdiagnosis and higher female autism suicide ORs.

### Gaps
- Not quantified in adults or veterans as predictors of undiagnosed ADHD or ASD:
  - missed-appointment and no-show rates;
  - number of failed antidepressant trials;
  - military disciplinary actions, Article 15 or non-judicial punishment, other-than-honorable discharge, and separations for "personality disorder" or "adjustment disorder";
  - gambling;
  - eating disorders;
  - sensory or GI symptoms;
  - hypermobility.

  These remain plausible but unvalidated features.
- MHS GENESIS–to–VA data-sharing elements (for example, the DD-214 separation code, service treatment records) that could supply pre-service or in-service history were not researched.
- No published, validated threshold or weighting scheme for an adult veteran ADHD/ASD referral flag exists in the material found.
