# ASTER — Comprehensive Medical & Nine-Specialty MDS Source Inventory

**Research date:** 13 October 2026  
**Purpose:** Build a source-grounded, broad-coverage medical education assistant for all nine MDS specialties, general patient education, medicine explanation, dental and other radiographic research, and scientific literature assistance.  
**Important scope:** No finite list of sources can make a model know every medical fact or guarantee clinical accuracy. This is a **curated acquisition and reference registry**, not a representation that these data have already been downloaded, their licenses cleared, or their medical quality independently evaluated.

## How to read this inventory

**Access/ingestion codes:**

- **API / metadata** — an official machine interface is provided; comply with API terms and content-level rights. An API does **not** automatically authorize bulk training, commercial use, or redistribution.
- **Read / link** — refer users to the source and verify current facts; do not bulk ingest or redistribute until rights are established.
- **OA-filter** — identify qualifying papers and check **each article's** license. CC BY, CC BY-SA, CC BY-NC, etc. impose different conditions.
- **Restricted / permission** — proprietary, paid, credentialed or specifically limited material; acquire appropriate rights first.
- **Dataset / check** — research data; check consent, intended use, DUA, commercial eligibility, patient-level splits and whether derivative models can be distributed.

**Separate rights for**: (1) reading/linking, (2) API-based extraction, (3) indexing for private retrieval, (4) fine-tuning/training, (5) shipping raw contents, (6) shipping learned weights, and (7) commercial deployment. Do not collapse these into a single `open_source=true` flag.

---

## 1. Official Indian MDS scope and cross-specialty educational foundations

| Source | URL | Role and use | Rights/notes |
|---|---|---|---|
| National Dental Commission / DCI MDS Regulations (2017) | https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf | Canonical baseline for nine specialties, curriculum, training and examination expectations | Government publication; assess reuse rights, not an accuracy reference for every clinical topic |
| Official Gazette / regulatory amendments | https://dciindia.gov.in/GazetteList.aspx | Track 2018/2019 and future amendments; version curricula | Read / link; check current updates |
| University MDS subject-syllabus example | https://ssahe.edu.in/ssdc/pdf/curriculum/MDS%20Syllabus.pdf | Supplementary mapping of specialty topics | Third-party university PDF; check currency and rights; **not** a replacement for national requirements |
| ADA evidence-based clinical dentistry | https://www.ada.org/resources/research/science/evidence-based-dental-research | Dental clinical guidelines across fields | Read / link; individual pages may be copyrighted |
| Cochrane Oral Health | https://oralhealth.cochrane.org/ | Research syntheses relevant to many MDS specialties | Abstracts sometimes available; full review reuse generally restricted or separately licensed |
| PubMed | https://pubmed.ncbi.nlm.nih.gov/ | Locate published biomedical evidence and identifiers | API / metadata; abstracts may carry publisher copyright |
| NCBI Bookshelf | https://www.ncbi.nlm.nih.gov/books/ | Books, reports, guideline collections, foundational coverage | Per-book/per-chapter rights vary; **not** a free bulk textbook corpus |
| NIH/NLM MeSH | https://www.nlm.nih.gov/databases/download/mesh.html | Topic graph, synonyms, hierarchy and precise literature search | Download available; follow NLM conditions; 2026 XML rather than discontinued ASCII |
| UMLS terminology and licenses | https://www.nlm.nih.gov/databases/umls.html | Clinical synonyms and terminology mapping | Free registration/license but component vocabularies can impose restrictions |
| SNOMED CT licensing | https://www.nlm.nih.gov/healthit/snomedct/snomed_licensing.html | Optional clinical coding, concepts and synonyms | Explicit license; distribution/territory terms apply |
| WHO ICD-11 | https://icd.who.int/ | Diagnostic classification and codes | Use official browser/API under WHO terms; **not** evidence for care recommendations |

**Foundational modules required across ALL nine specialties:** oral and dental anatomy, oral histology, embryology and tooth development; head/neck anatomy; physiology; biochemistry; microbiology; immunology; inflammation and wound healing; pathology; dental materials; pharmacology and toxicology; radiology physics; infection prevention; research methodology, biostatistics, epidemiology, consent and ethics. Create complete educational *facet maps* rather than only term lists.

## 2. Specialty-by-specialty authoritative source map

The following are recommended **reference catalogs and specific guideline portals**. They are not automatically eligible for training or redistribution. For each specialty, maintain topic IDs, source versions, curricular facets, associated evidence, and limitations.

### S1 — Conservative Dentistry & Endodontics

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| American Association of Endodontists (AAE) clinical resources | https://www.aae.org/specialty/clinical-resources/ | Pulpal/periapical diagnosis, RCT, CBCT, vital pulp therapy, endodontic safety | Read / link; individual policies |
| AAE guidelines and position statements | https://www.aae.org/specialty/clinical-resources/guidelines-position-statements/ | Vital pulp therapy, irrigation-related guidance, root canal standards | Read / link |
| AAE endodontic glossary | https://www.aae.org/specialty/clinical-resources/glossary-endodontic-terms/ | Terminology/synonym mapping | Read / link; do not assume rights to embed whole glossary |
| ADA restorative treatments of caries lesions (2023) | https://www.ada.org/resources/research/science/evidence-based-dental-research/caries-management-clinical-practice-guidelines/evidence-based-clinical-practice-guideline-on-restorative-treatments-for-caries-lesions/ | Restorative materials, caries management, primary/permanent teeth | Read / link |
| Indian Endodontic Society deep-caries/VPT statement | https://journals.lww.com/eddt/fulltext/2023/35030/indian_endodontic_society__position_statement_for.1.aspx | India-relevant vital pulp therapy | Read / link; publisher terms |
| Cochrane Oral Health | https://oralhealth.cochrane.org/ | Comparative effectiveness of restorative/endodontic interventions | DOI/abstract plus permitted full text |

**Required facets:** pulpal biology, caries classification, diagnostic terminology, sensitivity tests, reversible/irreversible pulpitis, apical disease, instrumentation, irrigants, obturation, retreatment, endodontic surgery, trauma, regenerative endodontics, restorative material properties and restoration longevity.

### S2 — Orthodontics & Dentofacial Orthopedics

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| American Association of Orthodontists (AAO) | https://aaoinfo.org/ | Orthodontic terminology, patient explanations, scope of procedures | Read / link |
| AAO position paper on clinical AI | https://www2.aaoinfo.org/the-aao-position-paper/ | Clinical oversight and limitations of orthodontic AI | Read / link |
| American Board of Orthodontics | https://www.americanboardortho.com/ | Professional exam/quality framework; not a syllabus textbook | Read / link |
| AAOMR imaging-position literature | https://aaomr.org/ | CBCT selection and radiology guidance relevant to orthodontics | Read / link; verify currency of older papers |
| Cochrane Oral Health | https://oralhealth.cochrane.org/ | Trials/reviews comparing orthodontic interventions | Index eligible OA only |
| PubMed orthodontics research | https://pubmed.ncbi.nlm.nih.gov/?term=orthodontics+systematic+review | Mechanotherapy, growth, cephalometrics, aligners and clinical evidence | API / metadata; OA-filter |

**Required facets:** growth, cephalometrics, classification of malocclusions, etiology, biomechanics, PDL and bone biology, appliances, aligners, extractions, anchorage/TADs, expansion, retainers, temporomandibular considerations, interdisciplinary care and pediatric growth timing.

### S3 — Oral & Maxillofacial Surgery

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| AAOMS clinical care | https://aaoms.org/practice/clinical-care/ | Surgery professional guidance | Read / link |
| AAOMS clinical papers | https://aaoms.org/publications/position-papers/clinical-papers/ | Third molars, orthognathic surgery, reconstruction, TMJ | Read / link |
| AAOMS white papers | https://aaoms.org/publications/position-papers/white-papers/ | MRONJ, biopsy/referral, mucosal dysplasia, anesthesia, cancer | Read / link |
| AAOMS parameters of care | https://aaoms.org/practice/clinical-care/parameters-of-care/ | Procedural and quality framework | Read / link |
| American College of Surgeons trauma resources | https://www.facs.org/quality-programs/trauma/ | Trauma educational guidance | Varying access, check rights |
| National Cancer Institute PDQ | https://www.cancer.gov/publications/pdq | Evidence summaries on oral/head-neck cancers | Read / link; PDQ content restrictions and updates |

**Required facets:** exodontia, infections, impacted teeth, maxillofacial fracture patterns, trauma priorities, orthognathic planning, deformities, tumors, cyst surgery, implants, flap/graft reconstruction, anesthesia principles, bleeding/airway risks and postoperative complications. **Do not provide individualized operative plans** to patients.

### S4 — Prosthodontics and Crown & Bridge

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| American College of Prosthodontists (ACP) parameters | https://www.prosthodontics.org/acp-publications/parameters-of-care/ | Prosthodontic quality, diagnostic indices and care parameters | Read / link |
| ACP position statements | https://www.prosthodontics.org/about-acp/acp-position-statements/ | Implants, dentures, materials, maintenance and rehabilitation | Read / link |
| PubMed evidence-based complete denture maintenance | https://pubmed.ncbi.nlm.nih.gov/21324026/ | Denture maintenance guideline publication | Citation metadata; full text check |
| International Team for Implantology | https://www.iti.org/ | Implant prosthodontic education and research | Many resources licensed/paid; link only unless authorized |
| Cochrane Oral Health | https://oralhealth.cochrane.org/ | Implant/denture/bridge comparisons | OA-filter |
| ADA restorative evidence | https://www.ada.org/resources/research/science/evidence-based-dental-research | Materials and restorative best practices | Read / link |

**Required facets:** impression science, jaw relations, occlusion, partial/complete dentures, RPD surveying, fixed restorations, preparation geometry, ceramics, esthetics, digital prosthodontics, maxillofacial prosthesis, implant biology, complications and maintenance.

### S5 — Periodontology

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| European Federation of Periodontology (EFP) S3 guidelines | https://www.efp.org/education/continuing-education/clinical-guidelines/ | Stage I–III, stage IV and peri-implant disease care | Read / link; verify versions |
| American Academy of Periodontology (AAP) | https://www.perio.org/ | Classification, periodontal and implant resources | Read / link |
| ADA periodontal guideline index | https://www.ada.org/resources/research/science/evidence-based-dental-research | Nonsurgical interventions and related evidence | Read / link |
| Cochrane Oral Health | https://oralhealth.cochrane.org/ | Periodontal intervention reviews | OA-filter |
| PubMed 2017 World Workshop search | https://pubmed.ncbi.nlm.nih.gov/?term=2017+world+workshop+periodontal+classification | Staging/grading and diagnostic definitions | API / metadata; papers may be copyrighted |

**Required facets:** periodontal tissues, biofilms, inflammation, microbiology, 2017 classification and updates, probing and attachment, radiographic bone loss, risk assessment, scaling/root planing, surgical access, regenerative procedures, mucogingival surgery, implant disease and systemic interactions.

### S6 — Pediatric & Preventive Dentistry

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| AAPD policies and recommendation index | https://www.aapd.org/research/oral-health-policies--recommendations/table-of-contents/ | Pediatric dental guidelines, risk assessment, behavior, sedation, radiographs | Read / link; some materials sold commercially |
| AAPD vital pulp therapies | https://www.aapd.org/research/oral-health-policies--recommendations/vital_pulp_therapies_in_primary_teeth_with_deep_caries_lesions/ | Pediatric pulp therapy | Read / link |
| AAPD official website | https://www.aapd.org/ | Trauma, preventive and growth-related patient/student resources | Read / link |
| ADA sealant/caries guidance | https://www.ada.org/resources/research/science/evidence-based-dental-research | Caries prevention, sealants and restorations | Read / link |
| WHO essential medicines for children | https://www.who.int/groups/expert-committee-on-selection-and-use-of-essential-medicines/essential-medicines-lists/ | Essential medicines and pediatric formulations | Read / link; not pediatric dosing engine |
| International Association of Dental Traumatology | https://www.iadt-dentaltrauma.org/ | Guidelines and dental-trauma references | Full documents / copyright status varies |

**Required facets:** eruption, developmental anomalies, ECC, fluoride and sealants, pulp therapy, mixed-dentition development, molar-incisor hypomineralization, behavior guidance, age-specific safety, dental trauma and child protection.

### S7 — Oral Medicine & Radiology

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| American Academy of Oral Medicine (AAOM) | https://www.aaom.com/ | Oral mucosal disease and oral medicine professional resources | Read / link |
| American Academy of Oral & Maxillofacial Radiology (AAOMR) | https://aaomr.org/ | Imaging positions and appropriate modality selection | Read / link |
| ADA radiography and radiation-safety guidelines | https://www.ada.org/resources/research/science/evidence-based-dental-research | Dental imaging justification, 2026 selection recommendations, 2024 safety | Read / link |
| NIH National Institute of Dental and Craniofacial Research | https://www.nidcr.nih.gov/health-info | Dry mouth, oral cancer, Sjögren's disease and patient information | Read / link, rights vary |
| NCI PDQ | https://www.cancer.gov/publications/pdq | Oral cancer evidence and patient explanations | Read / link |
| MedlinePlus | https://medlineplus.gov/ | Patient-focused symptom and condition explanations | Official API / attribution; third-party links distinct |

**Required facets:** mucosal diseases, ulcers, oral potentially malignant disorders, burning-mouth issues, salivary disorders, TMJ issues, radiological interpretation principles, periapical/panoramic/CBCT, differential reasoning, red flags, diagnostic testing, radiation dose justification. **Educational image review is distinct from patient-image diagnostic interpretation.**

### S8 — Oral Pathology & Microbiology

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| WHO/IARC Head and Neck Tumours (5th ed., vol. 9, 2024) | https://publications.iarc.who.int/Book-And-Report-Series/Who-Classification-Of-Tumours/Head-And-Neck-Tumours-2024 | Primary authoritative tumour classification | **Paid/web access**; use bibliographic reference and licensed access, not unauthorized corpus copying |
| WHO/IARC classification catalog | https://publications.iarc.who.int/Book-And-ReportSeries/Who-Classification-Of-Tumours | Find current versions and relevant classifications | Read / link |
| IARC Monographs | https://monographs.iarc.who.int/ | Carcinogen evidence: tobacco, areca-nut and related exposures | Check report-specific rights |
| National Cancer Institute PDQ | https://www.cancer.gov/publications/pdq | Cancer biology, oral cancer and diagnostic context | Read / link |
| PubMed / PMC OA-filtered pathology studies | https://pubmed.ncbi.nlm.nih.gov/?term=oral+pathology | OED, OPMDs, cysts, tumours, OSCC, immunohistochemistry | Article-level license, study-specific claims |
| American Academy of Oral & Maxillofacial Pathology (AAOMP) | https://www.aaomp.org/ | Professional clinical/pathology education | Read / link; inspect individual material rights |

**Required facets:** histology, cellular pathology, apoptosis/necrosis, dysplasia criteria, cysts, odontogenic tumours, oral cancer, salivary gland disease, bone lesions, inflammatory and infectious pathology, biopsy, processing/staining, immunohistochemistry, molecular pathology, forensic dentistry, oral microbiology and immunology.

### S9 — Public Health Dentistry

| Source | URL | Coverage | Acquisition |
|---|---|---|---|
| WHO Global Oral Health Strategy and Action Plan 2023–2030 | https://www.who.int/publications/i/item/9789240090538 | Policy, public health interventions, implementation | **CC BY-NC-SA 3.0 IGO** on the cited publication; noncommercial conditions |
| WHO 2025 oral health monitoring baseline | https://www.who.int/southeastasia/publications/i/item/9789240106031 | Global indicators, oral disease burden and progress | Noncommercial IGO licensing; verify edition |
| WHO Oral Health Programme | https://www.who.int/teams/noncommunicable-diseases/ncds-management/oral-health-programme | Global oral health monitoring and policy | Read / link |
| CDC National Oral Health Surveillance System | https://www.cdc.gov/oral-health-data-systems/about_oral_health_data/national-oral-health-surveillance-system-nohss.html | Epidemiology and surveillance indicators | CDC government materials often reusable, but page-specific rights |
| CDC fluoride-related indicators | https://www.cdc.gov/oral-health-data-systems/about_oral_health_data/water-fluoridation-indicators.html | Fluoridation monitoring | Verify method, year, country context |
| India MoHFW | https://mohfw.gov.in/ | India's public health policy and programmes | Read / link; confirm current official publications |
| Indian Council of Medical Research (ICMR) | https://www.icmr.gov.in/ | Research, public health, ethics and national surveys | Read / link; rights vary |
| WHO Global Health Observatory | https://www.who.int/data/gho | Cross-country public health indicators | Data license/attribution checks |

**Required facets:** DMFT/deft indices, CPI, diagnostic and survey measurements, sampling and confidence intervals, epidemiology, biostatistics, oral health policy, disease surveillance, water fluoridation, inequalities, oral cancer/tobacco prevention, school-based programmes, economic evaluation and implementation science.

---

## 3. Patient/general-medical information sources

Use this group to answer **general symptoms, definitions, report terminology, disease basics and when-to-seek-care questions** in plain language. It is not a substitute for examination, prescriptions, professional imaging reports or clinical decision-making.

| Source | URL | Role | Rights / warning |
|---|---|---|---|
| MedlinePlus health topics | https://medlineplus.gov/ | Patient-appropriate information, symptoms and tests | Prefer documented service; distinguish third-party content |
| MedlinePlus web service | https://medlineplus.gov/about/developers/webservices/ | **First-choice programmatic patient topic summaries** | No registration or licensing for the service, attribution/no endorsement conditions; respect rate limits |
| NIH NIDCR oral health info | https://www.nidcr.nih.gov/health-info | Official oral/dental patient information | Page-specific reuse rights |
| NHS Health A–Z | https://www.nhs.uk/conditions/ | Accessible condition/symptom explanations | **Read / link**; NHS content has its own reuse and API terms |
| NHS Medicines A–Z | https://www.nhs.uk/medicines/ | Patient-oriented medicines explanations | Read / link, jurisdiction-specific |
| WHO fact sheets | https://www.who.int/news-room/fact-sheets | Global public health and medical information | Item-specific reuse rights |
| NIH National Cancer Institute | https://www.cancer.gov/ | Cancer patient/professional explanations | Page and PDQ-specific rights |
| CDC disease and health-topic pages | https://www.cdc.gov/ | Infection prevention, epidemiology and patient guidance | Check specific content and reuse rules |
| Mayo Clinic health information | https://www.mayoclinic.org/ | Supplementary patient reading | **Proprietary; link only** without permission |
| ADA MouthHealthy | https://www.mouthhealthy.org/ | Patient-friendly dental problems and care | Read / link; not assumed redistributable |

**Patient answer format:** plain-language definition; common possible causes; signs that deserve timely care; urgent red flags when relevant; what a clinician typically assesses; uncertainty and citations. No asserted diagnosis from one symptom.


### 3.1 Broad systemic medicine — India-specific and international expansion

For questions that go beyond dentistry (cardiology, neurology, dermatology, infectious disease, pulmonology, paediatrics and so on), Aster needs **condition-specific authoritative guidance** rather than treating nine dental specialties as the entire medical universe.

| Source | URL | Recommended role | Notes |
|---|---|---|---|
| ICMR Standard Treatment Workflows | https://www.icmr.gov.in/standard-treatment-workflows-stws | **India-first systemic disease workflows**, including cardiovascular, respiratory, endocrinology, ENT, neurology, oncology and oral/lip cancer | Official clinical materials; read/link, verify rights and update dates; not patient prescriptions |
| ICMR STW portal | https://stw.icmr.org.in/ | Search Indian standard treatment workflow volumes | Scope and authority per workflow |
| NICE guidance catalog | https://www.nice.org.uk/guidance | UK disease-specific evidence-based recommendations | Country and copyright restrictions; verify guideline updates |
| WHO clinical guidelines | https://www.who.int/publications/guidelines | Global guidelines, prevention and public health | Publication-level license varies |
| NCI PDQ | https://www.cancer.gov/publications/pdq | Cancer information, staging context and patient/professional explanations | Version/reuse restrictions vary |
| CDC dental infection prevention | https://www.cdc.gov/dental-infection-control/hcp/index.html | Infection control and precautions across dental specialties | Official guidance; do not replace institution-specific infection protocols |
| ACR Appropriateness Criteria | https://acsearch.acr.org/ | Which imaging tests are appropriate for a given presentation | Controlled copyrighted guideline; read/link |
| WHO ICD-11 API | https://icd.who.int/icdapi | Codes and classification (2026 release) | Register for API, consult version-specific license; classification ≠ diagnosis |

**Avoid automatically merging recommendations across countries** (e.g., a US prescription label, an Indian brand, and a UK NHS guidance page) without showing jurisdiction and update dates. The Aster patient route should use general information even when a professional-care guideline contains advanced treatment details.

## 4. Medicines, active ingredients, labels, brands and drug safety

| Source | URL | Content | Use constraints |
|---|---|---|---|
| NLM RxNorm API | https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html | Drug-normalized identities, ingredient and strength terminology | Official API under terms; **not** sufficient for interactions or dosing |
| RxNorm terminology overview | https://www.nlm.nih.gov/research/umls/rxnorm/overview.html | Terms and release files | RxNorm-only subset free, other vocabulary components can differ |
| DailyMed REST APIs | https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm | Structured FDA-approved labelling, warnings, indications, dosage form, revisions | Label is product- and **US-jurisdiction-specific**; API terms and updates |
| US openFDA | https://open.fda.gov/ | Drug label data, adverse events, enforcement and approvals | Signals aren't incidence or definitive causality; check endpoint and warnings |
| Drugs@FDA | https://www.accessdata.fda.gov/scripts/cder/daf/ | US drug approval and label history | Read / link; monitor changes |
| CDSCO approved new drugs | https://cdsco.gov.in/opencms/opencms/en/Approval_new/Approved-New-Drugs | India new-drug approvals | Government source; not complete verified retail brand mapping |
| CDSCO searchable approvals | https://www.cdscoonline.gov.in/CDSCO/cdscoDrugs | Indian approvals and indications | Current regulatory data, online access terms |
| CDSCO fixed-dose combinations | https://cdsco.gov.in/opencms/opencms/en/Approval_new/FDC-New-Drugs-Marketing/ | Indian combination formulation approvals | Interpret version and conditions carefully |
| National List of Essential Medicines 2022 (India) | https://nppa.gov.in/en/nlem2022 | National essential-drug priorities | Not a prescribing formulary or current stock catalog |
| WHO Model Lists of Essential Medicines (2025) | https://www.who.int/groups/expert-committee-on-selection-and-use-of-essential-medicines/essential-medicines-lists/ | Global medicine essentiality and pediatric list | **Essentiality is not dose, safety or patient suitability** |
| PMBI/Janaushadhi products | https://www.pmbi.co.in/ProductList.aspx | Indian product names, pack and prices | Changing inventory; verify composition/product identity independently |
| Indian Pharmacopoeia Commission (IPC) | https://ipc.gov.in/ | Pharmacopoeial standards and pharmacovigilance coordination | Full pharmacopoeia protected; check each program |
| MedlinePlus drug pages | https://medlineplus.gov/druginformation.html | Patient-level medicine explanations | Read / link and use authorized data service where available |
| WHO AWaRe antibiotics | https://www.who.int/groups/expert-committee-on-selection-and-use-of-essential-medicines/essential-medicines-lists/ | Antibiotic stewardship categories | Not permission to suggest antibiotics for a patient's symptoms |

**Drug resolver minimum record:** jurisdiction, brand, company, generic ingredient(s), formulation, strength, route, regulatory identifier, intended population, label version, source URL, last verified, ambiguity and withdrawal status.

**Do not** auto-map a product solely by a brand-like name, infer dosage from similar brands, confuse paediatric and adult formulations, or call RxNorm an interaction database. A high-quality interaction checker requires a properly licensed validated interaction knowledgebase and pharmacist/clinician-led evaluation.

## 5. Medical imaging: reference sources and research datasets

**Crucial distinction:** Image datasets train or test *one particular visual task*. Textbooks/guidelines teach image acquisition and interpretive principles. Neither alone authorizes Aster to diagnose an arbitrary uploaded patient image. Separate `report-explanation`, `educational-known-image`, and `unvalidated-user-image` routes.

### 5.1 Dental imaging data

| Dataset / reference | URL | Reported size / task | Access and restrictions |
|---|---|---|---|
| **DENTEX** | https://github.com/ibrahimethemhamamci/DENTEX | 693 quadrant-only, 634 tooth-enumeration, **1,005 diagnosis-labelled** panoramic X-rays; four abnormality labels; **1,571 unlabeled** pretraining X-rays; specific labelled subset 705/50/250 split | Research dataset; inspect dataset and component image licenses and competition conditions before reuse |
| **InReDD PAN924** | https://physionet.org/content/inredd-dataset-pan924/1.0.0/ | **924 panoramic X-rays**, 200 with tooth segmentation, 14 tooth-condition categories and 4 mouth-condition categories | **Credentialed + contributor-approved**, research DUA, no redistribution |
| **ToothFairy** | https://toothfairy.grand-challenge.org/dataset/ | CBCT inferior alveolar canal segmentation | Training set sign-up, CC BY-SA; test set private; verify terms |
| **ToothFairy2** | https://toothfairy2.grand-challenge.org/dataset/ | CBCT multi-structure segmentation | Training set CC BY-SA with registration; test set private |
| **TL-pano** | https://zenodo.org/records/15038971 | 197 annotated, 114 unannotated panoramic radiographs; segmentation of dental structures | **Restricted**, noncommercial research terms and version checks |
| **AAOMR professional statements** | https://aaomr.org/ | Appropriate dental imaging, CBCT justification and interpretation principles | Read / link; older position statements may be superseded |
| **ADA radiography recommendations** | https://www.ada.org/resources/research/science/evidence-based-dental-research | 2026 imaging selection and 2024 radiation-safety guidance | Read / link |

**Do not add sample numbers across DENTEX annotation tiers and call the result unique patients without auditing duplicates.** Avoid leakage across subjects, image variants, teeth from the same person and derived report text. Track scanner/site, patient ID if legitimately available, age, tooth, split and annotation ontology.

### 5.2 Chest/general radiography research data (a separately validated project)

| Dataset | URL | Scale / task | Restriction |
|---|---|---|---|
| **CheXpert** | https://stanfordmlgroup.github.io/competitions/chexpert/ | **224,316 chest radiographs**, 65,240 patients, 14 observations with uncertain labels | Review Stanford access/license and evaluation rules; research-grade labels |
| **MIMIC-CXR v2.1.0** | https://physionet.org/content/mimic-cxr/2.1.0/ | **377,110 images**, 227,835 studies and text reports | **Credentialed only**, training and DUA, no redistribution |
| **NIH ChestX-ray14** | https://nihcc.app.box.com/v/ChestXray-NIHCC | Large weakly labelled chest radiography research corpus | Check official NIH terms and validation/label-noise limits |
| **RSNA datasets/challenges** | https://www.rsna.org/education/ai-resources-and-training/ai-image-challenge | Task-specific radiology benchmarks | Per-challenge licenses and external test sets vary |
| **The Cancer Imaging Archive (TCIA)** | https://www.cancerimagingarchive.net/ | Cancer CT/MRI/PET and linked imaging collections | Per-collection license/consent and patient-level splits |
| **NIH MedPix** | https://medpix.nlm.nih.gov/ | Medical image teaching cases | Image-case reuse terms vary; not unrestricted AI training corpus |
| **ACR Appropriateness Criteria** | https://acsearch.acr.org/ | Imaging selection based on clinical presentation | Guideline use; copyrighted material and versioning |

**Evaluation:** modality/task recognition, image quality/OOD, tooth finding detection, sensitivity, specificity, F1, AUROC/AUPRC, segmentation Dice/IoU, localization accuracy, false-negative rate, calibration and external-site robustness. All positive findings are **research outputs, not clinical diagnoses**, until task-specific real-world validation and authorization.

## 6. Biomedical literature and evidence feeds

| Feed | URL | What to collect | Rights / update notes |
|---|---|---|---|
| PubMed E-utilities | https://www.ncbi.nlm.nih.gov/books/NBK25497/ | PMID, title, abstract when rights permit, MeSH, date, DOI and links | Default ≤3 requests/s, ≤10 requests/s with API key; rate-limit and attribute |
| PMC OA subset | https://pmc.ncbi.nlm.nih.gov/tools/openftlist/ | **Only licensed reusable article content** and exact terms | Inspect article rights, individual licenses and corrected/withdrawn versions |
| **PMC AWS article datasets (post-August-2026)** | https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/ | Official bulk/research full-text pipeline | **Legacy bulk FTP/cloud files removed Aug 2026**; use updated AWS distribution, article licenses |
| PMC copyright statement | https://pmc.ncbi.nlm.nih.gov/about/copyright/ | Legal interpretation of PMC access | Do not scrape the main PMC website in bulk |
| Europe PMC | https://europepmc.org/ | Biomedical literature discovery and permitted OA texts | API and article-level licenses |
| Crossref REST API | https://www.crossref.org/documentation/retrieve-metadata/rest-api/ | DOI metadata, relations and corrections | Metadata vs copyrighted full text |
| OpenAlex | https://docs.openalex.org/ | Research graph, works/authors/venues and OA pointers | Licensing/rate limits/metadata provenance |
| DOAJ | https://doaj.org/ | Curated OA journal discovery | Article-level licensing still matters |
| PubMed retractions/corrections | https://pubmed.ncbi.nlm.nih.gov/ | Validate publication status and linked updates | Keep retraction flags to suppress outdated claims |
| ClinicalTrials.gov API | https://clinicaltrials.gov/data-api/api | Clinical trial registry records | Registry entry is **not** proof of benefit |
| Cochrane Library | https://www.cochranelibrary.com/ | High-level clinical effectiveness evidence | Full content generally controlled; link/metadata unless permission |
| GRADE working group | https://www.gradeworkinggroup.org/ | Evidence certainty and recommendation framework | Methodology link; do not invent GRADE ratings |

**Evidence precedence by question:** directly relevant current authoritative guideline or classification (if current) > appropriate systematic review/meta-analysis > suitable primary research > foundational educational reference > weak opinion/preprint. This is a starting heuristic: guideline currency, local jurisdiction, study quality, population applicability, conflicts and individual source limits can change the ranking. Multiple papers quoting the same source do not equal independent validation.

## 7. Task-specific text datasets and benchmarks (NOT a complete MDS textbook)

| Dataset | URL | Sample structure / official or representative counts | Role and caution |
|---|---|---|---|
| **MedMCQA** | https://huggingface.co/datasets/awinml/medmcqa | **182,822 train / 4,183 dev / 6,150 test**, four-way medical MCQ; test labels not public | Auxiliary medical MCQ benchmark, **not** open-ended MDS assessment; check question/explanation rights and leakage |
| **PubMedQA** | https://pubmedqa.github.io/ | **1,000 expert-labelled** research QAs plus much larger unlabelled/artificial subsets | Biomedical yes/no/maybe interpretation, not patient diagnosis; verify subsets/licensing before use |
| **MedQuAD** | https://github.com/abachaa/MedQuAD | Commonly reported **47,457 Q–A pairs** assembled from NIH websites | Patient QA task; original answers/source-specific rights and coverage gaps |
| **MedQA (USMLE)** | https://github.com/jind11/MedQA | USMLE-style questions (often cited as ~12.7k English four-option questions; verify selected version) | Auxiliary exams only; split licensing and contamination checks |
| **MIMIC-CXR** | https://physionet.org/content/mimic-cxr/2.1.0/ | Image/report pairs | Restricted research; not permitted patient report-writing deployment by default |
| **Aster Nine-Specialty Facet Benchmark — create** | Local project dataset | Plan minimum **9 specialties × task types × topics**, independently authored; exact future count TBD | Original open-answer benchmark with qualified reviewer labels; keep test cases and answers out of RAG/training |
| **Aster Patient-Explanation Benchmark — create** | Local project dataset | Symptom definitions, medicine basics, safe report explanations, red flags, uncertainty | Assess communication and patient safety separately |
| **Aster Image Interpretation Benchmark — create** | Local project dataset | Modality-specific, licensed images and independently adjudicated labels | Separate dental panoramic, periapical, CBCT, chest imaging; distinct clinical validation |

**Data splits:** group by source family, topic, study, patient and institution where relevant. Prevent duplicates, translated questions, answer key leakage, near-matching clinical cases, variants of the same X-ray and cross-paper citation contamination from crossing train/validation/test. Keep a truly unseen institutional/external challenge where lawful. Deduplicate by identifier AND semantic/visual fingerprints. Record rights for training and model-output redistribution per dataset.

## 8. Advanced textbooks that are useful **as references**, not free training sources

Do not obtain pirated copies, bypass paywalls, or upload and distribute these as if they were open datasets. Aster can support **authorized user-provided excerpts** consistent with the user's rights and system design.

| Major | Common standard textbooks / series (verify edition) | Status |
|---|---|---|
| Conservative/endodontics | Cohen's Pathways of the Pulp; Ingle's Endodontics; Sturdevant's Art and Science of Operative Dentistry | Commercial / copyright-protected |
| Orthodontics | Proffit's Contemporary Orthodontics; Graber's Orthodontics; Nanda's Biomechanics | Commercial |
| Oral surgery | Peterson's Principles of Oral and Maxillofacial Surgery; Contemporary Oral and Maxillofacial Surgery | Commercial |
| Prosthodontics | Boucher's Prosthodontic Treatment for Edentulous Patients; Rosenstiel's Contemporary Fixed Prosthodontics; McCracken's Removable Partial Prosthodontics | Commercial |
| Periodontology | Carranza's Clinical Periodontology; Lindhe's Clinical Periodontology and Implant Dentistry | Commercial |
| Pediatric dentistry | McDonald and Avery's Dentistry for the Child and Adolescent; Pinkham's Pediatric Dentistry | Commercial |
| Oral medicine/radiology | Burket's Oral Medicine; White and Pharoah's Oral Radiology | Commercial |
| Oral pathology/microbiology | Neville's Oral and Maxillofacial Pathology; Shafer's Textbook of Oral Pathology; WHO Head and Neck Tumours 2024 | Commercial/controlled access |
| Public health dentistry | Soben Peter's Essentials of Public Health Dentistry; Park's Textbook of Preventive and Social Medicine | Commercial |

**Special warning:** Recent OpenStax *Anatomy & Physiology 2e* rights notices explicitly bar ingestion into generative-AI offerings without prior written permission, despite freely viewable textbook pages. See https://openstax.org/books/anatomy-and-physiology-2e/pages/1-introduction . The presence of a Creative Commons badge does not override specific usage statements: obtain clarification/permission before feeding this book into Aster.

## 9. Required source manifest and ingestion gating

Implement one durable record **per source and per licensed item**; examples:

```yaml
source_id: "guideline_aae_vpt_2021"
canonical_url: "https://www.aae.org/specialty/clinical-resources/guidelines-position-statements/"
authority: "AAE"
content_type: "professional_guideline"
specialties: ["conservative_endodontics"]
audiences: ["student", "general_education"]
retrieved_at_utc: null
published_at: null
updated_at: null
edition: "verify_exact_version"
checksum_sha256: null
license_spdx: null
license_url: null
rights_read: "verify"
rights_api: "verify"
rights_private_rag: "verify"
rights_training: "not_approved"
rights_redistribution: "not_approved"
rights_commercial: "not_approved"
access_requirement: "review_source_terms"
clinical_review_status: "pending"
reference_scope: ["vital_pulp_therapy"]
patient_clinical_use_approved: false
source_class: "guideline"
```

**Acquisition stages:** discover -> resolve canonical URL, DOI and version -> check redirects/robots/API policy -> determine content-level copyright and permissions -> preserve immutable copy when lawful -> extract structured text/tables/figures without corrupting captions -> verify page/section offsets and hashes -> split coherent sections with context -> map to curriculum topic and task facets -> evidence QA -> index -> run regression and corpus-leakage controls -> release numbered source pack -> monitor corrections, withdrawals and guideline updates.

Never convert a `read` permission into `training` permission automatically. Never embed raw documents in a distributable installer without redistribution rights. Use a lightweight starter pack plus downloadable licensed/authorized optional packs.

## 10. How Aster should answer 'anything it knows' without pretending to be a doctor

The aim is **maximum helpfulness with honest evidence**, not 'answer only if every sentence passed a human medical examination'. Aster should answer harmless questions about anatomy, diseases, mechanisms, symptoms, medicines, procedures, public health, pathology, research and findings it can substantiate; clearly state when the knowledge is limited.

### Claim and response statuses (no fake confidence %)

| UI status | Meaning | Permitted behavior |
|---|---|---|
| **Current guideline / verified source** | Relevant authoritative source with identity/version and claim-level support checked | Give full educational explanation with links and applicable limitations; not automatically human-reviewed |
| **Source supported — clinical review pending** | Source applies and claim support was checked automatically, but no clinician independently reviewed Aster's answer | Answer in full, clearly label review pending |
| **Research finding — preliminary/contested** | Correctly attributed single study, weak evidence, conflict or evolving hypothesis | Explain as tentative and contrast with established consensus |
| **General model knowledge — not source verified** | Low-risk educational statement for which live/retrieved source is unavailable | May give a succinct provisional explanation, conspicuously flag that it is unverified, provide relevant caveats and encourage checking a source; do not fabricate references |
| **Unable to assess / clinically unsafe** | Personalized diagnosis, unsafe medication decision, unsupported image finding, urgent symptoms or missing critical context | Explain why the conclusion cannot be established; offer safe general facts, recommended professional evaluation/urgent care as appropriate, and useful follow-up questions |

Statuses must apply at the **claim/section level** for mixed responses. Distinguish source existence, source applicability, claim support, independent clinical review and safety eligibility; don't reduce them to one composite `accuracy` score.

**Examples of desired behavior:**

1. **“What is pulpitis?”** — answer normally, define, explain mechanisms, symptoms, relevant types and that a dentist differentiates clinically; give sources or indicate missing verification.
2. **“What does toothache mean?”** — useful general causes, red flags and when to seek a dentist; never substitute tooth eruption passages.
3. **“What is Dolo?”** — first disambiguate brand, country, ingredient, dosage form/strength; general label-backed information; no unrequested pediatric dose or personalized recommendation.
4. **“What does this X-ray show?”** — distinguish known educational images and independently validated tasks from real user scans. If image interpretation has not been validated for that modality/use, do not assert findings; explain image type, visible anatomy only where reliably supported, and offer to explain an accompanying radiologist/dentist report. Saying “unverified” does not itself make a patient-specific diagnosis safe.
5. **“Define leukoplakia and compare with lichen planus in MDS detail.”** — preserve both subjects, retrieve separate definitional, clinical and histological facets, construct an actual comparison and cite applicable references; identify missing facets.
6. **“What is the appropriate antibiotic dose for my child?”** — no personalized dose calculation/prescription. Explain standard medicine information, clarify risks and direct to a prescribing clinician/pharmacist.
7. **“Summarize this open-access paper.”** — extract exact bibliographic details, study population, design, outcomes and limitations; distinguish the paper's conclusions from consensus and never invent an effect size.

**No automatic blanket refusal for benign educational questions.** Missing specialty-specific material can trigger a broad but clearly flagged explanation from established model knowledge when low risk. Patient-critical outcomes and high-risk decisions should trigger stricter verification and qualified oversight, not only visual warning labels.

## 11. Architecture: evidence-aware system, not a raw scrape dump

```
User question / image / paper / medicine name
  -> session authorization, uploaded-data privacy and file validation
  -> audience + intent + personal-risk + modality classifier
  -> task decomposition with inherited full medical entities and context
  -> curriculum/terminology graph and brand/formulation resolution
  -> modality-specific evidence retrieval:
       MDS: textbooks-with-rights + guideline/review/topic/facet stores
       General patient: MedlinePlus/NIDCR/NHS/WHO allowed resources
       Medicines: RxNorm + country regulator + exact product label
       Imaging: approved image model and professional imaging guidance
       Research: paper metadata + authorized full-text chunks
  -> rank for topic, required facet, applicable population, authority,
     source currency, license and evidence contradictions
  -> compose short / deeper / comparison / viva / case / image explanation
  -> verify each substantive claim and each requested part
  -> common medical safety and output scope guard (INCLUDING fallback)
  -> attach per-claim evidence status and human-review state
  -> produce complete / partial / clarify / cannot-safely-assess output
  -> save privacy-preserving failure metrics and update topic capability map
```

**Do not start by fine-tuning on a huge mixed corpus.** First make source acquisition, answerability, retrieval, relevance and task completion measurable. RAG brings versioned external information; training makes behaviors more consistent but can introduce stale or unsupported claims. Image models must be trained and externally validated separately per modality/task.

## 12. Measurable acceptance and clinical governance

| Workstream | Required metrics |
|---|---|
| 9-specialty open-answer benchmark | facet completion, relevance, correct task format, completeness, appropriate abstention; stratify by specialty, topic, operation and depth |
| Literature | citation identity, publication version, reference accuracy, paper claim faithfulness, study-design/numeric extraction |
| Patient explanations | plain-language quality, red-flag recall, dangerous omission, unnecessary alarm, false reassurance and clinical-review status |
| Drug identity | brand/ingredient/formulation/strength precision, ambiguity detection, false mappings, outdated product labels |
| Imaging classification/detection | AUROC/AUPRC, sensitivity/specificity, F1, Dice/IoU where appropriate, patient/site-independent test, false-negative rate and out-of-distribution detection |
| Reliability | risk–coverage curve, selective accuracy, ECE/Brier where calibrated labels exist, unsupported-complete rate |
| Deployment | p50/p95 latency, VRAM/RAM, startup, offline source freshness, provenance and license compliance |

**External reviewers:** keep F03 open. Automated validation does not create faculty/clinician scores. Use real qualified reviewers, independent cases and adjudication before clinical deployment, diagnosis, treatment or image-reading claims. For local student education, clearly label provisional review states and measure learning-task completion separately from clinical safety.

## 13. Suggested acquisition order and minimum viable packs

**Stage 1:** DCI curriculum and current amendments; MeSH; MedlinePlus topic service; source/license ledger; ADA general guidance; AAE/EFP/AAPD/AAOMS core; foundational topic packs for all nine specialties.  
**Stage 2:** Complete common MDS short/long answers, comparisons, case facets and viva in each specialty using authorized comprehensive educational chapters and targeted recent guidelines.  
**Stage 3:** Medicine resolution via RxNorm, DailyMed, CDSCO, Indian NLEM and PMBI; explicit formulation and jurisdiction checking.  
**Stage 4:** Literature discovery via PubMed, Crossref, Europe PMC/OpenAlex; curated PMC OA full-text ingestion using the **2026 AWS service** and per-article licenses.  
**Stage 5:** Research-only imaging: DENTEX first, then licensed dental segmentation/CBCT packs; chest X-ray as a separate, appropriately credentialed and independently evaluated workstream.  
**Stage 6:** Train/ablate reliability-aware reranker/FGRC on **genuinely annotated** relevance/support/answerability data; do not turn LLM judge scores into medical accuracy.  
**Stage 7:** Qualified human review, external validation, rights-cleared distribution and monitoring.

**Success definition:** Aster answers relevant questions in useful depth, marks unsupported claims accurately, handles the nine MDS subjects and broad medical education, and does not claim to diagnose, prescribe or interpret patient imaging beyond its actual independently validated scope.

---

## 14. Official links checked particularly carefully (October 2026)

- DCI regulation index and amendments: https://dciindia.gov.in/GazetteList.aspx
- ADA current guideline catalog including 2026 imaging/pain/antibiotic material: https://www.ada.org/resources/research/science/evidence-based-dental-research
- AAPD reference index: https://www.aapd.org/research/oral-health-policies--recommendations/table-of-contents/
- EFP S3 clinical guidelines: https://www.efp.org/education/continuing-education/clinical-guidelines/
- AAOMS professional position paper catalog: https://aaoms.org/publications/position-papers/white-papers/
- WHO/IARC 2024 classification catalog: https://publications.iarc.who.int/Book-And-Report-Series/Who-Classification-Of-Tumours/Head-And-Neck-Tumours-2024
- PMC official 2026 article datasets: https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/
- MedlinePlus API: https://medlineplus.gov/about/developers/webservices/
- Drug RxNorm API: https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html
- DailyMed API: https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm
- India CDSCO approvals: https://www.cdscoonline.gov.in/CDSCO/cdscoDrugs
- DENTEX dataset: https://github.com/ibrahimethemhamamci/DENTEX
- InReDD PAN924: https://physionet.org/content/inredd-dataset-pan924/1.0.0/
- CheXpert: https://stanfordmlgroup.github.io/competitions/chexpert/
- MIMIC-CXR: https://physionet.org/content/mimic-cxr/2.1.0/
- OpenStax generative-AI reuse restrictions: https://openstax.org/books/anatomy-and-physiology-2e/pages/1-introduction

**Final note:** Rights and clinical status are deployment decisions to verify at the individual source/item level; “freely accessible” is not equivalent to “open licensed for model training.” This registry is broad but necessarily non-exhaustive and should be maintained as a living, version-controlled source manifest rather than a once-only scrape.
