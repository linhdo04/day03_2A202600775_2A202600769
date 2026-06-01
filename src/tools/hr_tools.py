"""
HR Management Tools — Person B
================================
Chủ đề: Quản lý nhân sự công ty
Mock database + 5 tool functions cho ReAct Agent.
"""

from typing import Dict, Any

# ── Mock Database ─────────────────────────────────────────────────────────────

_EMPLOYEES: Dict[str, Dict[str, Any]] = {
    "EMP001": {
        "name": "Nguyễn Thị Mai",
        "department": "Nhân sự",
        "position": "HR Manager",
        "base_salary": 25_000_000,
        "allowance": 3_000_000,
        "leave_balance": 10,
        "performance_rating": "A",
        "years_of_service": 5,
    },
    "EMP002": {
        "name": "Trần Văn Hùng",
        "department": "IT",
        "position": "Software Engineer",
        "base_salary": 30_000_000,
        "allowance": 2_000_000,
        "leave_balance": 8,
        "performance_rating": "B+",
        "years_of_service": 3,
    },
    "EMP003": {
        "name": "Lê Thị Lan",
        "department": "Marketing",
        "position": "Marketing Specialist",
        "base_salary": 20_000_000,
        "allowance": 1_500_000,
        "leave_balance": 12,
        "performance_rating": "A-",
        "years_of_service": 2,
    },
    "EMP004": {
        "name": "Phạm Quốc Bảo",
        "department": "IT",
        "position": "Senior Developer",
        "base_salary": 40_000_000,
        "allowance": 4_000_000,
        "leave_balance": 5,
        "performance_rating": "A+",
        "years_of_service": 7,
    },
    "EMP005": {
        "name": "Đỗ Thị Hoa",
        "department": "Kế toán",
        "position": "Accountant",
        "base_salary": 22_000_000,
        "allowance": 1_000_000,
        "leave_balance": 7,
        "performance_rating": "B",
        "years_of_service": 4,
    },
}

_DEPARTMENTS: Dict[str, Dict[str, Any]] = {
    "IT":       {"manager": "EMP004", "headcount": 15, "budget_monthly": 450_000_000},
    "Marketing":{"manager": "EMP003", "headcount": 8,  "budget_monthly": 180_000_000},
    "Nhân sự":  {"manager": "EMP001", "headcount": 5,  "budget_monthly": 130_000_000},
    "Kế toán":  {"manager": "EMP005", "headcount": 6,  "budget_monthly": 145_000_000},
}

_WORKING_DAYS_PER_MONTH = 26


# ── Tool Functions ────────────────────────────────────────────────────────────

def get_employee_info(employee_id: str) -> str:
    """
    Lấy thông tin chi tiết của nhân viên theo mã nhân viên.
    Trả về: họ tên, phòng ban, chức vụ, lương cơ bản, phụ cấp, KPI, thâm niên.
    Args: employee_id (str) — ví dụ 'EMP001'
    """
    emp = _EMPLOYEES.get(employee_id.upper())
    if not emp:
        return (
            f"Không tìm thấy nhân viên '{employee_id}'. "
            f"Mã hợp lệ: {list(_EMPLOYEES.keys())}"
        )
    return (
        f"Thông tin nhân viên {employee_id.upper()}:\n"
        f"  Họ tên        : {emp['name']}\n"
        f"  Phòng ban     : {emp['department']}\n"
        f"  Chức vụ       : {emp['position']}\n"
        f"  Lương cơ bản  : {emp['base_salary']:,} VND\n"
        f"  Phụ cấp       : {emp['allowance']:,} VND\n"
        f"  Xếp loại KPI  : {emp['performance_rating']}\n"
        f"  Thâm niên     : {emp['years_of_service']} năm"
    )


def check_leave_balance(employee_id: str) -> str:
    """
    Kiểm tra số ngày phép còn lại trong năm của nhân viên.
    Args: employee_id (str) — ví dụ 'EMP002'
    """
    emp = _EMPLOYEES.get(employee_id.upper())
    if not emp:
        return f"Không tìm thấy nhân viên '{employee_id}'."
    balance = emp["leave_balance"]
    return (
        f"Nhân viên {emp['name']} ({employee_id.upper()}) "
        f"còn {balance} ngày phép trong năm."
    )


def submit_leave_request(employee_id: str, days_requested: int) -> str:
    """
    Xử lý đơn xin nghỉ phép cho nhân viên.
    Kiểm tra số ngày phép còn lại, duyệt hoặc từ chối, cập nhật số dư phép.
    Args:
        employee_id (str)    — ví dụ 'EMP003'
        days_requested (int) — số ngày muốn nghỉ (phải > 0)
    """
    emp = _EMPLOYEES.get(employee_id.upper())
    if not emp:
        return f"Không tìm thấy nhân viên '{employee_id}'."
    if days_requested <= 0:
        return "Số ngày nghỉ phải lớn hơn 0."

    balance = emp["leave_balance"]
    if days_requested > balance:
        return (
            f"TỪ CHỐI: {emp['name']} chỉ còn {balance} ngày phép, "
            f"không đủ để nghỉ {days_requested} ngày."
        )

    emp["leave_balance"] -= days_requested
    return (
        f"CHẤP THUẬN: Đã duyệt {days_requested} ngày nghỉ phép "
        f"cho {emp['name']} ({employee_id.upper()}).\n"
        f"  Số ngày phép trước  : {balance} ngày\n"
        f"  Số ngày phép còn lại: {emp['leave_balance']} ngày"
    )


def calculate_monthly_salary(employee_id: str) -> str:
    """
    Tính lương thực nhận tháng này của nhân viên.
    Công thức: (lương cơ bản + phụ cấp) - BHXH (10.5%) - thuế TNCN (10%).
    Args: employee_id (str) — ví dụ 'EMP004'
    """
    emp = _EMPLOYEES.get(employee_id.upper())
    if not emp:
        return f"Không tìm thấy nhân viên '{employee_id}'."

    base = emp["base_salary"]
    allowance = emp["allowance"]
    gross = base + allowance
    social_insurance = int(base * 0.105)
    taxable = gross - social_insurance
    income_tax = int(taxable * 0.10) if taxable > 11_000_000 else 0
    net = gross - social_insurance - income_tax

    return (
        f"Bảng lương tháng này — {emp['name']} ({employee_id.upper()}):\n"
        f"  Lương cơ bản      : {base:,} VND\n"
        f"  Phụ cấp           : {allowance:,} VND\n"
        f"  Tổng thu nhập gộp : {gross:,} VND\n"
        f"  BHXH (10.5%)      : -{social_insurance:,} VND\n"
        f"  Thuế TNCN (10%)   : -{income_tax:,} VND\n"
        f"  ─────────────────────────────\n"
        f"  Lương thực nhận   : {net:,} VND"
    )


def get_department_info(department_name: str) -> str:
    """
    Lấy thông tin phòng ban: trưởng phòng, số nhân viên, ngân sách tháng.
    Args: department_name (str) — ví dụ 'IT', 'Marketing', 'Nhân sự', 'Kế toán'
    """
    dept = _DEPARTMENTS.get(department_name)
    if not dept:
        return (
            f"Không tìm thấy phòng ban '{department_name}'. "
            f"Các phòng ban: {list(_DEPARTMENTS.keys())}"
        )
    manager = _EMPLOYEES.get(dept["manager"], {})
    return (
        f"Thông tin phòng {department_name}:\n"
        f"  Trưởng phòng    : {manager.get('name', 'Không rõ')} ({dept['manager']})\n"
        f"  Số nhân viên    : {dept['headcount']} người\n"
        f"  Ngân sách tháng : {dept['budget_monthly']:,} VND"
    )


# ── Tools Registry ────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_employee_info",
        "description": (
            "Lấy thông tin chi tiết của nhân viên theo mã nhân viên. "
            "Trả về: họ tên, phòng ban, chức vụ, lương cơ bản, phụ cấp, xếp loại KPI, thâm niên. "
            "Args: employee_id (str) — ví dụ 'EMP001', 'EMP003'."
        ),
        "function": get_employee_info,
    },
    {
        "name": "check_leave_balance",
        "description": (
            "Kiểm tra số ngày phép còn lại trong năm của một nhân viên. "
            "Args: employee_id (str) — ví dụ 'EMP002'."
        ),
        "function": check_leave_balance,
    },
    {
        "name": "submit_leave_request",
        "description": (
            "Nộp và xử lý đơn xin nghỉ phép cho nhân viên. "
            "Kiểm tra số ngày phép còn lại rồi duyệt hoặc từ chối, cập nhật số dư phép. "
            "Args: employee_id (str), days_requested (int — số ngày muốn nghỉ, phải > 0)."
        ),
        "function": submit_leave_request,
    },
    {
        "name": "calculate_monthly_salary",
        "description": (
            "Tính lương thực nhận tháng này: lương cơ bản + phụ cấp, "
            "trừ BHXH (10.5%) và thuế TNCN (10%). "
            "Args: employee_id (str) — ví dụ 'EMP003'."
        ),
        "function": calculate_monthly_salary,
    },
    {
        "name": "get_department_info",
        "description": (
            "Lấy thông tin phòng ban: trưởng phòng, số nhân viên, ngân sách tháng. "
            "Args: department_name (str) — ví dụ 'IT', 'Marketing', 'Nhân sự', 'Kế toán'."
        ),
        "function": get_department_info,
    },
]
