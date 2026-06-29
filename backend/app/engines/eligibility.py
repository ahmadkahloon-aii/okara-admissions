"""Eligibility engine: percentage calculation and program eligibility decision."""
from .. data.catalog import program_by_code, program_by_name


def calc_percentage(obtained: float, total: float) -> float:
    if not total or total <= 0:
        raise ValueError("Total marks must be greater than zero.")
    return round((float(obtained) / float(total)) * 100, 2)


def check_eligibility(program_ref: str, obtained: float = None, total: float = None,
                      percentage: float = None, result_awaited: bool = False) -> dict:
    """
    program_ref: program code or name.
    Provide either (obtained & total) or percentage.
    Returns a structured decision the assistant/dashboard can use directly.
    """
    program = program_by_code(program_ref) or program_by_name(program_ref)
    if not program:
        return {"found": False, "message": f"'{program_ref}' is not offered at the Okara campus.",
                "eligible": False, "refer_lahore": True}

    pct = percentage
    if pct is None and obtained is not None and total:
        pct = calc_percentage(obtained, total)

    min_pct = program["min_pct"]
    part = "Part 1 (result awaited / provisional)" if result_awaited else "Part 2 (final result)"

    # No fixed percentage bar -> eligible on valid Intermediate, confirm on qualification
    if min_pct is None:
        return {
            "found": True, "program": program["name"], "code": program["code"],
            "percentage": pct, "min_pct": None, "part": part,
            "eligible": True, "provisional": result_awaited, "refer_lahore": False,
            "message": (f"{program['name']} requires {program['qualification']}. "
                        f"You appear eligible on a valid Intermediate (or equivalent) qualification."),
        }

    if pct is None:
        return {
            "found": True, "program": program["name"], "code": program["code"],
            "percentage": None, "min_pct": min_pct, "part": part,
            "eligible": None, "provisional": result_awaited, "refer_lahore": False,
            "message": (f"{program['name']} requires at least {min_pct}% with "
                        f"{program['qualification']}. Please share your marks to confirm."),
        }

    eligible = pct >= min_pct
    if eligible:
        msg = (f"With {pct}% you meet the {min_pct}% requirement for {program['name']}"
               + (" (provisional, pending final result)." if result_awaited else "."))
    else:
        msg = (f"{program['name']} requires at least {min_pct}%. With {pct}% you are just below "
               f"the bar for this program, but you may qualify for other options.")
    return {
        "found": True, "program": program["name"], "code": program["code"],
        "percentage": pct, "min_pct": min_pct, "part": part,
        "eligible": eligible, "provisional": result_awaited and eligible,
        "refer_lahore": False, "message": msg,
    }


def eligible_alternatives(percentage: float, qualification_hint: str = "") -> list:
    """Programs the applicant would qualify for at this percentage (best-effort)."""
    from .. data.catalog import PROGRAMS
    out = []
    for p in PROGRAMS:
        mp = p["min_pct"]
        if mp is None or (percentage is not None and percentage >= mp):
            out.append({"name": p["name"], "code": p["code"], "min_pct": mp})
    return out
