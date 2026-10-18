"""Message formatting for new-result Telegram notifications.

Delivery is done by notification_worker.py through telegram_db.send_message();
this module only builds the message text.
"""


def format_result(
    institute_name,
    degree_name,
    semester_name,
    exam_name,
):
    """Format one result notification."""

    return (
        "🆕 NEW CHARUSAT RESULT\n\n"
        f"🏫 Institute: {institute_name}\n"
        f"📚 Degree: {degree_name}\n"
        f"🎓 Semester: {semester_name}\n"
        f"📄 Exam: {exam_name}"
    )
