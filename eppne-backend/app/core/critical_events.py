# app/core/critical_events.py
"""
خريطة الأحداث الحرجة (Critical Events) اللي محتاجة تتوصّل عبر Celery
بالإضافة إلى Redis Pub/Sub العادي في EventBus.publish().

أول حدث حرج حقيقي: "academy.bootcamp_enrollment.created" — لازم يتوصّل
بضمان retry (max_retries=3 في dispatch_critical_event_task) لأنه بيحدّث
user_network_stats.bootcamp_network_size (walk-up على سلسلة الإحالة)،
فقدانه بصمت يعني عداد شبكة غلط بلا أي أثر يُكتشف. راجع:
.claude/reports/achievement-network-tracking-implementation-session-log.md

ثاني حدث حرج: "academy.course.completed" — منح مباشر (بلا عتبة، بلا
walk-up) لتعريفات TRAINING النشطة. راجع:
.claude/reports/achievement-auto-grant-training-session-log.md

تالت حدث حرج: "project.contribution.received" — حدث موجود بالفعل من
قبل في projects/service.py (بلا أي تعديل عليه هنا)، منح مباشر (بلا
عتبة) لتعريفات PROJECT_FUNDING النشطة — نفس نمط TRAINING بالحرف. راجع:
.claude/reports/achievement-auto-grant-project-funding-session-log.md
"""

CRITICAL_EVENT_HANDLERS: dict[str, str] = {
    "academy.bootcamp_enrollment.created": "achievements.update_bootcamp_network_stats",
    "academy.course.completed": "achievements.grant_training_achievements_for_course_completion",
    "project.contribution.received": "achievements.grant_project_funding_achievements_for_contribution",
}
