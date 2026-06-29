"""Fee engine: net fee computation using the official formula.

Net first-semester payable = Admission Fee (one-time)
                           + Misc Fee (full, per semester)
                           + Tuition x (1 - scholarship%)
Scholarship waiver applies to tuition only (unless a total-fee-waiver category).
"""
from .. data.catalog import FEES, program_by_code, program_by_name


def get_fee(program_ref: str) -> dict:
    program = program_by_code(program_ref) or program_by_name(program_ref)
    code = program["code"] if program else program_ref
    fee = FEES.get(code)
    if not fee:
        return {"found": False, "message": f"No fee on record for '{program_ref}'."}
    name = program["name"] if program else code
    confirmed = fee["tuition"] is not None
    return {
        "found": True, "program": name, "code": code,
        "tuition_first_sem": fee["tuition"], "total": fee["total"],
        "admission": fee["admission"], "misc": fee["misc"],
        "confirmed": confirmed,
        "message": (f"{name}: first-semester tuition PKR {fee['tuition']:,}, "
                    f"plus one-time admission fee PKR {fee['admission']:,} and "
                    f"miscellaneous fee PKR {fee['misc']:,} per semester."
                    if confirmed else
                    f"{name}: fee is being finalised. The admissions office will confirm the exact amount."),
    }


def net_first_semester(program_ref: str, scholarship_pct: float = 0,
                       total_waiver: bool = False) -> dict:
    fee = get_fee(program_ref)
    if not fee.get("found"):
        return fee
    if fee["tuition_first_sem"] is None:
        return {**fee, "computed": False,
                "message": f"{fee['program']} fee is being finalised; net amount cannot be computed yet."}

    admission = fee["admission"]
    misc = fee["misc"]
    tuition = fee["tuition_first_sem"]

    if total_waiver:
        net = 0
        waived = admission + misc + tuition
    else:
        tuition_after = round(tuition * (1 - (scholarship_pct or 0) / 100))
        net = admission + misc + tuition_after
        waived = tuition - tuition_after

    return {
        **fee, "computed": True, "scholarship_pct": 0 if total_waiver else scholarship_pct,
        "total_waiver": total_waiver, "tuition_after_waiver": 0 if total_waiver else tuition_after,
        "amount_waived": waived, "net_first_semester": net,
        "message": (f"{fee['program']} net first-semester payable is PKR {net:,} "
                    f"(admission {admission:,} + misc {misc:,} + tuition after "
                    f"{scholarship_pct or 0}% waiver)." if not total_waiver else
                    f"{fee['program']} qualifies for a total fee waiver - net first-semester payable is PKR 0."),
    }
