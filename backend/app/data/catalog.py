"""
Static reference data for Superior University Okara Campus (Fall 2026).
Single source of truth for the eligibility, fee and scholarship engines.
All monetary values are in PKR.
"""

# ---------------------------------------------------------------------------
# PROGRAMS
# key fields: name, code, faculty, level, min_pct (None = "Intermediate, no fixed bar"),
#             qualification, council, semesters
# ---------------------------------------------------------------------------
PROGRAMS = [
    # Computing (BS)
    {"name": "BS Computer Science", "code": "BS-CS", "faculty": "Computing", "level": "BS",
     "min_pct": 50, "qualification": "Intermediate with FSc / ICS / I.Com / FA-IT (or equivalent)", "council": "NCEAC", "semesters": 8},
    {"name": "BS Software Engineering", "code": "BS-SE", "faculty": "Computing", "level": "BS",
     "min_pct": 50, "qualification": "Intermediate with FSc / ICS / I.Com / FA-IT (or equivalent)", "council": "NCEAC", "semesters": 8},
    {"name": "BS Data Science", "code": "BS-DS", "faculty": "Computing", "level": "BS",
     "min_pct": 50, "qualification": "Intermediate with FSc / ICS / I.Com / FA-IT (or equivalent)", "council": "NCEAC", "semesters": 8},
    {"name": "BS Artificial Intelligence", "code": "BS-AI", "faculty": "Computing", "level": "BS",
     "min_pct": 50, "qualification": "Intermediate with FSc / ICS / I.Com / FA-IT (or equivalent)", "council": "NCEAC", "semesters": 8},
    {"name": "BS Cyber Security", "code": "BS-CYS", "faculty": "Computing", "level": "BS",
     "min_pct": 50, "qualification": "Intermediate with FSc / ICS / I.Com / FA-IT (or equivalent)", "council": "NCEAC", "semesters": 8},
    {"name": "BS Robotics", "code": "BS-ROB", "faculty": "Computing", "level": "BS",
     "min_pct": 50, "qualification": "Intermediate with FSc / ICS / I.Com / FA-IT (or equivalent)", "council": "NCEAC", "semesters": 8},
    # Business & Management
    {"name": "BBA (Hons.)", "code": "BBA", "faculty": "Business & Management", "level": "BS",
     "min_pct": None, "qualification": "Intermediate or Equivalent", "council": "NBEAC", "semesters": 8},
    {"name": "BS Business Intelligence", "code": "BS-BI", "faculty": "Business & Management", "level": "BS",
     "min_pct": None, "qualification": "Intermediate or Equivalent", "council": "NBEAC", "semesters": 8},
    {"name": "BS Ecommerce", "code": "BS-ECOM", "faculty": "Business & Management", "level": "BS",
     "min_pct": None, "qualification": "Intermediate or Equivalent", "council": "HEC", "semesters": 8},
    {"name": "BS Accounting & Finance", "code": "BS-AF", "faculty": "Business & Management", "level": "BS",
     "min_pct": None, "qualification": "Intermediate or Equivalent", "council": "HEC", "semesters": 8},
    # Arts & Humanities
    {"name": "BS English Language & Literature", "code": "BS-ENG", "faculty": "Arts & Humanities", "level": "BS",
     "min_pct": 45, "qualification": "Intermediate or Equivalent", "council": "HEC", "semesters": 8},
    {"name": "BS Clinical Psychology", "code": "BS-CP", "faculty": "Arts & Humanities", "level": "BS",
     "min_pct": 45, "qualification": "Intermediate or Equivalent", "council": "HEC", "semesters": 8},
    # Allied Health
    {"name": "BS Medical Lab Sciences", "code": "BS-MLS", "faculty": "Allied Health Sciences", "level": "BS",
     "min_pct": 45, "qualification": "FSc Pre-Medical or Equivalent", "council": "AHPC / HEC", "semesters": 8},
    {"name": "BS Medical Imaging Technology", "code": "BS-MIT", "faculty": "Allied Health Sciences", "level": "BS",
     "min_pct": 45, "qualification": "FSc Pre-Medical or Equivalent", "council": "AHPC / HEC", "semesters": 8},
    {"name": "BS Human Nutrition & Dietetics", "code": "BS-HND", "faculty": "Allied Health Sciences", "level": "BS",
     "min_pct": 45, "qualification": "FSc Pre-Medical", "council": "AHPC / HEC", "semesters": 8},
    {"name": "BS Optometry & Vision Sciences", "code": "BS-OPT", "faculty": "Allied Health Sciences", "level": "BS",
     "min_pct": 45, "qualification": "FSc Pre-Medical", "council": "AHPC", "semesters": 8},
    {"name": "BS Aesthetics & Cosmetology", "code": "BS-AC", "faculty": "Allied Health Sciences", "level": "BS",
     "min_pct": 45, "qualification": "FSc Pre-Medical", "council": "AHPC", "semesters": 8},
    {"name": "Doctor of Physical Therapy (DPT)", "code": "DPT", "faculty": "Allied Health Sciences", "level": "DPT",
     "min_pct": 60, "qualification": "FSc Pre-Medical or Equivalent", "council": "AHPC / HEC", "semesters": 10},
    # ADP
    {"name": "ADP Business Administration", "code": "ADP-BA", "faculty": "Associate Degree", "level": "ADP",
     "min_pct": None, "qualification": "Intermediate or Equivalent", "council": "NBEAC / HEC", "semesters": 4},
    {"name": "ADP Computer Science", "code": "ADP-CS", "faculty": "Associate Degree", "level": "ADP",
     "min_pct": None, "qualification": "Intermediate or Equivalent", "council": "NCEAC", "semesters": 4},
    {"name": "ADP Cyber Security", "code": "ADP-CYS", "faculty": "Associate Degree", "level": "ADP",
     "min_pct": None, "qualification": "Intermediate or Equivalent", "council": "NCEAC", "semesters": 4},
    # Postgraduate
    {"name": "MBA 2 Year (Weekend)", "code": "MBA-WK", "faculty": "Postgraduate", "level": "MBA",
     "min_pct": None, "qualification": "16 years non-business education; merit on prior CGPA", "council": "NBEAC", "semesters": 4},
]

# ---------------------------------------------------------------------------
# FEES  (PKR)  keyed by program code
# tuition = first-semester tuition, total = full program, admission = one-time,
# misc = per-semester miscellaneous.  None = "to confirm".
# ---------------------------------------------------------------------------
FEES = {
    "BBA":     {"tuition": 195000, "total": 1640000, "admission": 20000, "misc": 7500},
    "BS-BI":   {"tuition": 150000, "total": 1280000, "admission": 20000, "misc": 7500},
    "BS-ECOM": {"tuition": 110000, "total": 960000,  "admission": 20000, "misc": 7500},
    "BS-AF":   {"tuition": 123000, "total": 1064000, "admission": 20000, "misc": 7500},
    "BS-CS":   {"tuition": 180000, "total": 1520000, "admission": 20000, "misc": 7500},
    "BS-SE":   {"tuition": 175000, "total": 1480000, "admission": 20000, "misc": 7500},
    "BS-DS":   {"tuition": 175000, "total": 1480000, "admission": 20000, "misc": 7500},
    "BS-AI":   {"tuition": 180000, "total": 1520000, "admission": 20000, "misc": 7500},
    "BS-CYS":  {"tuition": 175000, "total": 1480000, "admission": 20000, "misc": 7500},
    "BS-ROB":  {"tuition": 160000, "total": 1360000, "admission": 20000, "misc": 7500},
    "BS-ENG":  {"tuition": 115000, "total": 1000000, "admission": 20000, "misc": 7500},
    "BS-CP":   {"tuition": 110000, "total": 960000,  "admission": 15000, "misc": 7500},
    "BS-MLS":  {"tuition": 125000, "total": 1080000, "admission": 20000, "misc": 7500},
    "BS-MIT":  {"tuition": 175000, "total": 1480000, "admission": 20000, "misc": 7500},
    "BS-HND":  {"tuition": 143000, "total": 1224000, "admission": 20000, "misc": 7500},
    "BS-OPT":  {"tuition": 160000, "total": 1360000, "admission": 20000, "misc": 7500},
    "BS-AC":   {"tuition": 130000, "total": 1120000, "admission": 20000, "misc": 7500},
    "DPT":     {"tuition": 210000, "total": 2195000, "admission": 20000, "misc": 7500},
    "ADP-BA":  {"tuition": 95000,  "total": 425000,  "admission": 15000, "misc": 7500},
    "ADP-CS":  {"tuition": 95000,  "total": 425000,  "admission": 15000, "misc": 7500},
    "ADP-CYS": {"tuition": 95000,  "total": 425000,  "admission": 15000, "misc": 7500},
    "MBA-WK":  {"tuition": 155000, "total": 670000,  "admission": 20000, "misc": 7500},
    # Post-ADP (5th semester entry)
    "POST-BS-AF":  {"tuition": 123000, "total": 542000, "admission": 20000, "misc": 7500},
    "POST-BS-ROB": {"tuition": 160000, "total": 690000, "admission": 20000, "misc": 7500},
    "POST-BS-CS":  {"tuition": None,   "total": None,   "admission": 20000, "misc": 7500},
    "POST-BS-AI":  {"tuition": None,   "total": None,   "admission": 20000, "misc": 7500},
}

# ---------------------------------------------------------------------------
# SCHOLARSHIPS
# ---------------------------------------------------------------------------
# Merit bands for BS / Bachelor / ADP. (low, high, waiver_pct, total_waiver?)
MERIT_BANDS = [
    {"min": 90, "max": 1000, "waiver": 100, "total": False, "label": "90% and above"},
    {"min": 85, "max": 90,   "waiver": 75,  "total": False, "label": "85% to below 90%"},
    {"min": 75, "max": 85,   "waiver": 50,  "total": False, "label": "75% to below 85%"},
    {"min": 70, "max": 75,   "waiver": 40,  "total": False, "label": "70% to below 75%"},
    {"min": 60, "max": 70,   "waiver": 30,  "total": False, "label": "60% to below 70%"},
    {"min": 50, "max": 60,   "waiver": 20,  "total": False, "label": "50% to below 60%"},
]
POSITION_HOLDER = {"waiver": 100, "total": True, "label": "Board Position Holder (Total Fee Waiver)"}

MERIT_BANDS_DPT = [
    {"min": 80, "max": 1000, "waiver": 50, "total": False, "label": "Above 80%"},
    {"min": 70, "max": 80,   "waiver": 25, "total": False, "label": "70% to 80%"},
]
MERIT_BANDS_MBA = [
    {"min": 3.50, "waiver": 50, "label": "Qualifying CGPA 3.50"},
    {"min": 3.25, "waiver": 35, "label": "Qualifying CGPA 3.25"},
    {"min": 3.00, "waiver": 25, "label": "Qualifying CGPA 3.00"},
]
HIGH_ACHIEVERS = [
    {"label": "All Intermediate position holders", "benefit": "100% Total Fee Waiver"},
    {"label": "FA / FSc, I.Com / ICS: 90%+", "benefit": "100% Tuition Fee Waiver"},
    {"label": "A Levels: 3A / A*", "benefit": "100% Tuition Fee Waiver"},
    {"label": "A Levels: 2A / A*", "benefit": "90% Tuition Fee Waiver"},
    {"label": "A Levels: 1A + 2B", "benefit": "75% Tuition Fee Waiver"},
]
OTHER_CATEGORIES = [
    {"name": "Alumni Based", "benefit": "SGC regular HSSC: 50% (UG/ADP), 25% (PG). SU ADP graduate: 50%. SU 16/17-yr graduate: 25%.", "evidence": "HSSC result card / SU ADP or UG transcript"},
    {"name": "Kinship", "benefit": "35% (UG/ADP), 25% (PG) where parent, sibling or spouse is a current SU student / alumnus.", "evidence": "Kin transcript + Family Registration Certificate"},
    {"name": "Rector's Women Empowerment", "benefit": "30% for first female in family in higher education; 25% (PG) for widow, single mother, woman entrepreneur.", "evidence": "Affidavit / NADRA verification / business evidence"},
    {"name": "Outstanding Sportsmen", "benefit": "100% (UG/ADP) for excellence in sports.", "evidence": "Sports certificates + prescribed trials"},
    {"name": "Extracurricular Talent", "benefit": "100% (UG/ADP) for music, dramatics, debate / declamation, Naat or Qirat.", "evidence": "Certificates + prescribed assessment"},
    {"name": "Corporate Linkages", "benefit": "30% (UG/ADP) for MOU-partner employees / evening working professionals; 15% (PG).", "evidence": "Employment / employability letter"},
    {"name": "Differently Abled Students", "benefit": "50% for a permanent disability.", "evidence": "Government or NADRA disability certificate"},
    {"name": "Children of Martyrs / Shuhadaa", "benefit": "100% for spouse or child of a martyr / shaheed.", "evidence": "Death certificate + Shaheed / Martyr certificate"},
    {"name": "Remote Area Students", "benefit": "30% for designated remote areas.", "evidence": "Domicile certificate"},
    {"name": "Children of Govt. Employees, Armed Forces & Teachers", "benefit": "25% (UG/ADP).", "evidence": "Parent / guardian employability certificate"},
    {"name": "PWWF Scholarship", "benefit": "100% for eligible children of registered workers (UG & PG).", "evidence": "Labour card, CNICs, academic records, photos; PWWF verification"},
    {"name": "Honhaar Scholarship", "benefit": "100% for eligible UG applicants (Govt. of Punjab criteria).", "evidence": "Punjab domicile, income affidavit (E-stamp), application form"},
    {"name": "Qarz-e-Hasna", "benefit": "Interest-free loan; repayable 3-5 years after graduation.", "evidence": "Income / property / rent evidence, CNICs, FAO verification"},
]

# ---------------------------------------------------------------------------
# ADP -> BS (5th semester) pathways
# ---------------------------------------------------------------------------
ADP_PATHWAYS = {
    "ADP-CS": ["BS Computer Science", "BS Artificial Intelligence", "BS Robotics"],
    "ADP-AF": ["BS Accounting & Finance"],
}

# ---------------------------------------------------------------------------
# TRANSPORT  (charges still being calculated)
# ---------------------------------------------------------------------------
TRANSPORT_ROUTES = [
    {"no": 1, "route": "Pattoki -> Okara", "distance_km": 52},
    {"no": 2, "route": "Hujra - Depalpur -> Okara", "distance_km": 55},
    {"no": 3, "route": "Chuchak / Bahma Bala (Express) -> Okara", "distance_km": 45},
    {"no": 4, "route": "Okara City Route", "distance_km": 20},
    {"no": 5, "route": "Jandaraka - Bangla Gogera -> Okara", "distance_km": 45},
    {"no": 6, "route": "Gamber -> Okara", "distance_km": 25},
]
TRANSPORT_CHARGES_STATUS = "Transport fare is being calculated and will be shared shortly."

# ---------------------------------------------------------------------------
# CONTACT / CRM
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    "Lead", "Qualified Lead", "Prospectus Stage", "Entry Test Stage",
    "Fee Voucher Issued", "Fee Voucher Paid", "Current Student",
]
STATUS_TAGS = ["AI-Handled", "Human-Required", "Human-Assigned", "Awaiting-Student-Response"]

FACULTIES = ["Computing", "Business & Management", "Allied Health Sciences",
             "Arts & Humanities", "Associate Degree", "Postgraduate"]

OFFICE_HOURS = "Monday to Saturday, 09:00 AM - 03:30 PM"
APPLY_PORTAL = "admissions.superior.edu.pk"
CAMPUS_NAME = "Superior University Okara Campus, Jawad Avenue, Okara"


# ---------- lookup helpers ----------
def program_by_code(code: str):
    for p in PROGRAMS:
        if p["code"] == code:
            return p
    return None


def program_by_name(name: str):
    name_l = name.strip().lower()
    for p in PROGRAMS:
        if p["name"].lower() == name_l:
            return p
    # fuzzy contains
    for p in PROGRAMS:
        if name_l in p["name"].lower() or p["name"].lower() in name_l:
            return p
    return None


def programs_by_faculty(faculty: str):
    return [p for p in PROGRAMS if p["faculty"] == faculty]
