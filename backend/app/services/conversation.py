"""Conversation state machine: implements the WhatsApp menu flow from the BRD.
Deterministic for menus / forms; delegates free-text questions to the AI counsellor.

handle() returns the list of outbound messages (also sent via WhatsApp if configured),
so a simulator endpoint can drive the same logic without a live WhatsApp connection.
"""
import re
from sqlalchemy.orm import Session
from ..models import Message
from ..data import catalog
from ..engines import eligibility, fees, scholarships
from . import whatsapp, crm, openai_service

# ---- button / row ids ----
MENU_AI, MENU_PROGRAMS, MENU_HUMAN, MENU_LANG = "menu_ai", "menu_programs", "menu_human", "menu_lang"
P_ELIG, P_SCH, P_TRANS, P_ADP, P_APPLY, P_FEE, P_HUMAN, P_MAIN = (
    "p_elig", "p_sch", "p_trans", "p_adp", "p_apply", "p_fee", "p_human", "p_main")
LANG_EN, LANG_UR = "lang_en", "lang_ur"
ACT_CHECK, ACT_APPLY, ACT_BACK = "act_check", "act_apply", "act_back"
PV_VOUCHER, PV_APPT, PV_MAIN = "pv_voucher", "pv_appt", "pv_main"
GREETING_WORDS = {"hi", "hello", "hey", "salam", "asalam", "assalam", "start", "menu", "hy", "aoa"}


# ============================ outbound dispatch ============================
def _dispatch(db: Session, contact, kind: str, **kw) -> dict:
    """Send an outbound message via WhatsApp (if configured) and log it."""
    text = kw.get("text", "")
    res = {"ok": False}
    if kind == "text":
        res = whatsapp.send_text(db, contact.wa_id, text)
    elif kind == "buttons":
        res = whatsapp.send_buttons(db, contact.wa_id, kw["body"], kw["buttons"],
                                    header=kw.get("header"), footer=kw.get("footer"))
        text = kw["body"]
    elif kind == "list":
        res = whatsapp.send_list(db, contact.wa_id, kw["body"], kw["button"], kw["sections"],
                                 header=kw.get("header"), footer=kw.get("footer"))
        text = kw["body"]
    crm.log_message(db, contact, "out", text, mtype=("interactive" if kind != "text" else "text"),
                    payload={k: v for k, v in kw.items() if k != "text"} if kind != "text" else None,
                    wa_message_id=res.get("message_id", ""), handled_by="ai",
                    status="sent" if res.get("ok") else "failed")
    return {"kind": kind, "text": text, **{k: v for k, v in kw.items()}, "delivery": res}


# ============================ menu builders ============================
def _greeting(contact) -> str:
    name = (contact.name or "").split(" ")[0]
    hi = f"Assalam-o-Alaikum {name}!" if name else "Assalam-o-Alaikum!"
    return (f"{hi} Welcome to {catalog.CAMPUS_NAME.split(',')[0]} admissions (Fall 2026). "
            "How can I help you today?")


def show_main_menu(db: Session, contact, greeting: bool = True):
    crm.set_state(db, contact, "MAIN_MENU")
    body = _greeting(contact) if greeting else "Main Menu - what would you like to do?"
    sections = [{"title": "Main Menu", "rows": [
        {"id": MENU_AI, "title": "AI Counsellor", "description": "Check eligibility & ask questions"},
        {"id": MENU_PROGRAMS, "title": "Programs Information", "description": "Programs, scholarships, transport"},
        {"id": MENU_HUMAN, "title": "Human Counsellor", "description": "Talk to our admissions team"},
        {"id": MENU_LANG, "title": "Change Language", "description": "English / Urdu"},
    ]}]
    return [_dispatch(db, contact, "list", body=body, button="Choose", sections=sections,
                      header="Superior University Okara")]


def show_programs_menu(db: Session, contact, intro: str = None):
    crm.set_state(db, contact, "PROGRAMS_MENU")
    body = intro or "Programs Information - please choose:"
    sections = [{"title": "Programs", "rows": [
        {"id": P_ELIG, "title": "Programs & Eligibility", "description": "Browse by faculty"},
        {"id": P_SCH, "title": "Scholarships", "description": "Merit & category waivers"},
        {"id": P_TRANS, "title": "Transport Information", "description": "Routes & charges"},
        {"id": P_ADP, "title": "ADP to BS (5th Sem)", "description": "Continue your associate degree"},
        {"id": P_APPLY, "title": "Apply / Form", "description": "Start your application"},
        {"id": P_FEE, "title": "Ask about Fee", "description": "Fee for a program"},
        {"id": P_HUMAN, "title": "Talk to Counsellor", "description": "Human help"},
        {"id": P_MAIN, "title": "Main Menu", "description": "Go back"},
    ]}]
    return [_dispatch(db, contact, "list", body=body, button="Choose", sections=sections,
                      header="Programs Menu")]


def show_faculties(db: Session, contact):
    crm.set_state(db, contact, "FACULTY_PICK")
    rows = [{"id": f"fac_{i}", "title": fac[:24], "description": ""} for i, fac in enumerate(catalog.FACULTIES)]
    sections = [{"title": "Faculties", "rows": rows}]
    return [_dispatch(db, contact, "list", body="Select a faculty to see its programs:",
                      button="Faculties", sections=sections, header="Programs & Eligibility")]


def show_programs_in_faculty(db: Session, contact, faculty: str):
    crm.set_state(db, contact, "PROGRAM_PICK", {"faculty": faculty})
    progs = catalog.programs_by_faculty(faculty)
    rows = []
    for p in progs:
        req = f"Min {p['min_pct']}%" if p["min_pct"] else "Intermediate"
        rows.append({"id": f"prog_{p['code']}", "title": p["name"][:24], "description": req})
    sections = [{"title": faculty[:24], "rows": rows[:10]}]
    return [_dispatch(db, contact, "list", body=f"{faculty} programs - tap one for details:",
                      button="Programs", sections=sections, header=faculty[:60])]


def show_program_detail(db: Session, contact, code: str):
    p = catalog.program_by_code(code)
    if not p:
        return show_programs_menu(db, contact, "I couldn't find that program. Choose again:")
    contact.program_interest = p["name"]
    contact.program_code = p["code"]
    contact.program_tag = p["code"]
    crm.set_state(db, contact, "PROGRAM_DETAIL", {"program_code": code})
    req = f"at least {p['min_pct']}%" if p["min_pct"] else "a valid Intermediate (or equivalent)"
    body = (f"*{p['name']}*\n"
            f"Eligibility: {req} - {p['qualification']}.\n"
            f"Duration: {p['semesters']} semesters. Accreditation: {p['council']}.")
    buttons = [{"id": ACT_CHECK, "title": "Check eligibility"},
               {"id": ACT_APPLY, "title": "Apply now"},
               {"id": P_MAIN, "title": "Main Menu"}]
    return [_dispatch(db, contact, "buttons", body=body, buttons=buttons)]


def show_transport(db: Session, contact):
    crm.set_state(db, contact, "PROGRAMS_MENU")
    lines = ["*Transport Routes* (all end at Superior University Okara):"]
    for r in catalog.TRANSPORT_ROUTES:
        lines.append(f"{r['no']}. {r['route']}  (~{r['distance_km']} km)")
    lines.append("\n" + catalog.TRANSPORT_CHARGES_STATUS)
    out = [_dispatch(db, contact, "text", text="\n".join(lines))]
    out += [_dispatch(db, contact, "buttons", body="Anything else?",
                      buttons=[{"id": P_MAIN, "title": "Main Menu"},
                               {"id": MENU_HUMAN, "title": "Human Counsellor"}])]
    return out


def show_adp_pathways(db: Session, contact):
    crm.set_state(db, contact, "PROGRAMS_MENU")
    body = ("*ADP to BS (5th Semester)*\n"
            "After ADP Computer Science: continue into BS Computer Science, BS Artificial Intelligence or BS Robotics.\n"
            "After ADP Accounting & Finance: continue into BS Accounting & Finance.\n"
            "You enter directly in the 5th semester.")
    return [_dispatch(db, contact, "buttons", body=body,
                      buttons=[{"id": P_APPLY, "title": "Apply now"},
                               {"id": P_MAIN, "title": "Main Menu"}])]


def show_scholarship_overview(db: Session, contact):
    crm.set_state(db, contact, "PROGRAMS_MENU")
    body = ("*Scholarships* are mainly merit-based tuition waivers: 50% for 75-85%, 75% for 85-90%, "
            "and 100% for 90%+ or board position holders. Categories such as alumni, kinship, women "
            "empowerment, sports and children of martyrs also apply. You receive the single highest "
            "waiver you qualify for (they do not stack).")
    out = [_dispatch(db, contact, "text", text=body)]
    out += [_dispatch(db, contact, "buttons", body="Want me to check your maximum scholarship?",
                      buttons=[{"id": ACT_CHECK, "title": "Check for me"},
                               {"id": P_APPLY, "title": "Apply now"},
                               {"id": P_MAIN, "title": "Main Menu"}])]
    return out


def start_human(db: Session, contact):
    crm.assign_to_human(db, contact)
    crm.set_state(db, contact, "HUMAN")
    return [_dispatch(db, contact, "text",
                      text=("I'm connecting you with a human admissions counsellor. They'll reply here "
                            "shortly. Could you share your name and contact number so they can assist you?"))]


def ask_language(db: Session, contact):
    crm.set_state(db, contact, "LANG_PICK")
    return [_dispatch(db, contact, "buttons", body="Please choose your language / زبان منتخب کریں:",
                      buttons=[{"id": LANG_EN, "title": "English"}, {"id": LANG_UR, "title": "Urdu"}])]


def start_ai_chat(db: Session, contact):
    crm.set_state(db, contact, "AI_CHAT")
    return [_dispatch(db, contact, "text",
                      text=("Sure - ask me anything about programs, eligibility, fees or scholarships, "
                            "or tell me your marks (e.g. 850/1100) and the program you're interested in. "
                            "Type 'menu' anytime to go back."))]


# ---- application form ----
def start_form(db: Session, contact):
    crm.set_state(db, contact, "FORM_NAME", dict(contact.state_data or {}))
    return [_dispatch(db, contact, "text", text="Let's start your application. What is your *full name*?")]


def _advance_form(db: Session, contact, text: str):
    state = contact.state
    data = dict(contact.state_data or {})
    if state == "FORM_NAME":
        data["name"] = text.strip()
        contact.name = text.strip()
        crm.set_state(db, contact, "FORM_CNIC", data)
        return [_dispatch(db, contact, "text", text="Thanks! Your *CNIC* (xxxxx-xxxxxxx-x)?")]
    if state == "FORM_CNIC":
        data["cnic"] = text.strip()
        crm.set_state(db, contact, "FORM_FATHER", data)
        return [_dispatch(db, contact, "text", text="Your *father's name*?")]
    if state == "FORM_FATHER":
        data["father_name"] = text.strip()
        # program may already be known
        if contact.program_code:
            data["program"] = contact.program_interest
            crm.set_state(db, contact, "FORM_CONTACT", data)
            return [_dispatch(db, contact, "text", text="Your *contact number*?")]
        crm.set_state(db, contact, "FORM_PROGRAM", data)
        return [_dispatch(db, contact, "text", text="Which *program* are you applying for?")]
    if state == "FORM_PROGRAM":
        prog = catalog.program_by_name(text.strip())
        if not prog:
            return [_dispatch(db, contact, "text",
                              text=("I couldn't match that program. Please type the program name "
                                    "(e.g. BS Computer Science), or type 'menu' to browse programs."))]
        data["program"] = prog["name"]
        crm.set_state(db, contact, "FORM_CONTACT", data)
        return [_dispatch(db, contact, "text", text="Your *contact number*?")]
    if state == "FORM_CONTACT":
        data["contact_number"] = text.strip()
        crm.apply_lead_details(db, contact, data)
        return _after_form(db, contact)
    return show_main_menu(db, contact)


def _after_form(db: Session, contact):
    out = [_dispatch(db, contact, "text",
                     text=(f"Thank you, {contact.name.split(' ')[0]}! Your application details are saved "
                           f"for {contact.program_interest}."))]
    # scholarship if we know percentage
    if contact.percentage and contact.program_code:
        sch = scholarships.best_scholarship(contact.program_code, percentage=contact.percentage)
        if sch.get("found"):
            contact.scholarship_note = sch["best"]["name"]
            out += [_dispatch(db, contact, "text", text=sch["message"])]
    else:
        out += [_dispatch(db, contact, "text",
                          text=("Tip: share your percentage and I'll tell you the maximum scholarship "
                                "you qualify for."))]
    crm.set_state(db, contact, "PROSPECTUS")
    out += [_dispatch(db, contact, "buttons", body="How would you like to proceed?",
                      buttons=[{"id": PV_VOUCHER, "title": "Prospectus voucher"},
                               {"id": PV_APPT, "title": "Book appointment"},
                               {"id": PV_MAIN, "title": "Main Menu"}])]
    return out


def issue_prospectus(db: Session, contact):
    crm.set_stage(db, contact, "Prospectus Stage")
    crm.set_state(db, contact, "MAIN_MENU")
    link = f"https://{catalog.APPLY_PORTAL}/prospectus?campus=okara"
    return [_dispatch(db, contact, "text",
                      text=(f"Here is your prospectus voucher link: {link}\n"
                            "Once the prospectus is paid, your fee voucher will be issued and your "
                            "status updated. Reply 'menu' anytime."))]


def start_appointment(db: Session, contact):
    crm.set_state(db, contact, "APPOINTMENT_TIME")
    return [_dispatch(db, contact, "text",
                      text=(f"Our admissions office is open {catalog.OFFICE_HOURS}. "
                            "Please share your preferred day and time (e.g. 'Tue 11:00 AM')."))]


def book_appointment(db: Session, contact, text: str):
    from ..models import Appointment
    appt = Appointment(contact_id=contact.id, name=contact.name, contact_number=contact.contact_number,
                       program=contact.program_interest, slot=text.strip(), status="requested")
    db.add(appt)
    crm.set_stage(db, contact, "Prospectus Stage")
    db.commit()
    crm.set_state(db, contact, "MAIN_MENU")
    return [_dispatch(db, contact, "text",
                      text=(f"Your appointment request for '{text.strip()}' is noted. Our admissions "
                            "office will confirm shortly. Is there anything else I can help with?"))]


# ---- eligibility quick path ----
def ask_marks(db: Session, contact, program_code: str = None):
    data = dict(contact.state_data or {})
    if program_code:
        data["program_code"] = program_code
    crm.set_state(db, contact, "AWAITING_MARKS", data)
    prog = catalog.program_by_code(data.get("program_code") or contact.program_code or "")
    pname = prog["name"] if prog else "your program"
    return [_dispatch(db, contact, "text",
                      text=(f"Please share your marks for {pname} as obtained/total (e.g. 850/1100), "
                            "or your percentage (e.g. 82%). Add 'awaited' if your result isn't declared yet."))]


def parse_marks(text: str):
    awaited = bool(re.search(r"await|not declared|result pending|part\s*1", text, re.I))
    mpct = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", text)
    if mpct:
        return None, None, float(mpct.group(1)), awaited
    mfrac = re.search(r"(\d{2,4}(?:\.\d+)?)\s*(?:/|out of|outof|of)\s*(\d{2,4}(?:\.\d+)?)", text, re.I)
    if mfrac:
        return float(mfrac.group(1)), float(mfrac.group(2)), None, awaited
    return None, None, None, awaited


def handle_marks(db: Session, contact, text: str):
    obtained, total, pct, awaited = parse_marks(text)
    data = dict(contact.state_data or {})
    code = data.get("program_code") or contact.program_code
    if obtained is None and pct is None:
        return [_dispatch(db, contact, "text",
                          text="Please send marks like 850/1100 or a percentage like 82%.")]
    result = eligibility.check_eligibility(code or "", obtained, total, pct, awaited)
    if result.get("percentage") is not None:
        contact.percentage = result["percentage"]
        db.commit()
    out = [_dispatch(db, contact, "text", text=result["message"])]
    if result.get("eligible"):
        if contact.stage == "Lead":
            crm.set_stage(db, contact, "Qualified Lead")
        out += [_dispatch(db, contact, "buttons", body="Would you like to apply now?",
                          buttons=[{"id": P_APPLY, "title": "Apply now"},
                                   {"id": P_FEE, "title": "Ask about fee"},
                                   {"id": P_MAIN, "title": "Main Menu"}])]
    elif result.get("eligible") is False and not result.get("refer_lahore"):
        alts = eligibility.eligible_alternatives(result.get("percentage"))[:5]
        if alts:
            names = ", ".join(a["name"] for a in alts)
            out += [_dispatch(db, contact, "text", text=f"You may qualify for: {names}.")]
        out += [_dispatch(db, contact, "buttons", body="What next?",
                          buttons=[{"id": P_APPLY, "title": "Apply anyway"},
                                   {"id": MENU_HUMAN, "title": "Human Counsellor"},
                                   {"id": P_MAIN, "title": "Main Menu"}])]
    crm.set_state(db, contact, "PROGRAMS_MENU")
    return out


# ---- fee prompt ----
def ask_fee_program(db: Session, contact):
    crm.set_state(db, contact, "FEE_PROMPT")
    return [_dispatch(db, contact, "text",
                      text="Which program's fee would you like? (e.g. BS Computer Science)")]


def handle_fee_prompt(db: Session, contact, text: str):
    prog = catalog.program_by_name(text.strip())
    if not prog:
        return [_dispatch(db, contact, "text",
                          text="I couldn't match that program. Try the full name, e.g. 'BS Cyber Security'.")]
    fee = fees.get_fee(prog["code"])
    crm.set_state(db, contact, "PROGRAMS_MENU")
    out = [_dispatch(db, contact, "text", text=fee["message"])]
    out += [_dispatch(db, contact, "buttons", body="Anything else?",
                      buttons=[{"id": P_APPLY, "title": "Apply now"},
                               {"id": P_MAIN, "title": "Main Menu"}])]
    return out


# ============================ main router ============================
def handle(db: Session, contact, inbound: dict) -> list:
    """inbound: {type, text, interactive_id, interactive_title}"""
    itype = inbound.get("type", "text")
    text = (inbound.get("text") or "").strip()
    iid = inbound.get("interactive_id")

    # log inbound (carry audio + transcription if this was a voice note)
    media_b64 = inbound.get("media_b64")
    payload_clean = {k: v for k, v in inbound.items() if k != "media_b64"}
    crm.log_message(db, contact, "in",
                    text or inbound.get("transcription") or (inbound.get("interactive_title") or ""),
                    mtype=itype, payload=payload_clean, handled_by="ai",
                    media_b64=media_b64, media_mime=inbound.get("media_mime", ""),
                    transcription=inbound.get("transcription", "") or "",
                    media_id=inbound.get("media_id", ""))

    # interactive replies route by id regardless of state
    if iid:
        return _route_id(db, contact, iid)

    low = text.lower()
    if low in GREETING_WORDS or low in {"main menu", "go back", "back"}:
        return show_main_menu(db, contact)
    if low in {"human", "agent", "counsellor", "talk to human"}:
        return start_human(db, contact)

    state = contact.state
    # stateful text handlers
    if state in ("FORM_NAME", "FORM_CNIC", "FORM_FATHER", "FORM_PROGRAM", "FORM_CONTACT"):
        return _advance_form(db, contact, text)
    if state == "AWAITING_MARKS":
        return handle_marks(db, contact, text)
    if state == "FEE_PROMPT":
        return handle_fee_prompt(db, contact, text)
    if state == "APPOINTMENT_TIME":
        return book_appointment(db, contact, text)
    if state == "HUMAN":
        # human is handling; just acknowledge and keep logging
        return []
    if state == "NEW":
        return show_main_menu(db, contact)

    # default: AI counsellor (grounded). Works in AI_CHAT and as a helpful fallback.
    history = _recent_history(db, contact)
    reply = openai_service.answer(db, contact, text, history)
    out = [_dispatch(db, contact, "text", text=reply)]
    if state != "AI_CHAT":
        crm.set_state(db, contact, "AI_CHAT")
    return out


def _route_id(db: Session, contact, iid: str) -> list:
    if iid == MENU_AI:
        return start_ai_chat(db, contact)
    if iid in (MENU_PROGRAMS,):
        return show_programs_menu(db, contact)
    if iid in (MENU_HUMAN, P_HUMAN):
        return start_human(db, contact)
    if iid == MENU_LANG:
        return ask_language(db, contact)
    if iid == LANG_EN:
        contact.language = "en"; db.commit()
        return show_main_menu(db, contact, greeting=False)
    if iid == LANG_UR:
        contact.language = "ur"; db.commit()
        out = [_dispatch(db, contact, "text", text="ٹھیک ہے، میں اردو میں مدد کروں گا۔")]
        return out + show_main_menu(db, contact, greeting=False)
    if iid in (P_MAIN, PV_MAIN):
        return show_main_menu(db, contact, greeting=False)
    if iid == P_ELIG:
        return show_faculties(db, contact)
    if iid == P_SCH:
        return show_scholarship_overview(db, contact)
    if iid == P_TRANS:
        return show_transport(db, contact)
    if iid == P_ADP:
        return show_adp_pathways(db, contact)
    if iid == P_APPLY:
        return start_form(db, contact)
    if iid == P_FEE:
        return ask_fee_program(db, contact)
    if iid == ACT_CHECK:
        return ask_marks(db, contact)
    if iid == ACT_APPLY:
        return start_form(db, contact)
    if iid == PV_VOUCHER:
        return issue_prospectus(db, contact)
    if iid == PV_APPT:
        return start_appointment(db, contact)
    if iid.startswith("fac_"):
        try:
            fac = catalog.FACULTIES[int(iid.split("_")[1])]
            return show_programs_in_faculty(db, contact, fac)
        except (IndexError, ValueError):
            return show_faculties(db, contact)
    if iid.startswith("prog_"):
        return show_program_detail(db, contact, iid[len("prog_"):])
    # unknown id -> main menu
    return show_main_menu(db, contact, greeting=False)


def _recent_history(db: Session, contact, limit: int = 8) -> list:
    msgs = (db.query(Message).filter(Message.contact_id == contact.id)
            .order_by(Message.created_at.desc()).limit(limit).all())
    msgs = list(reversed(msgs))
    out = []
    for m in msgs[:-1]:  # exclude the just-logged inbound (added last)
        role = "user" if m.direction == "in" else "assistant"
        if m.body:
            out.append({"role": role, "content": m.body})
    return out
