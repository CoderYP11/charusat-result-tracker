from database import (
    get_setting,
    set_setting,
    get_settings,
    create_crawl_run,
    update_crawl_run,
    get_crawl_run,
    get_latest_crawl_run,
    log_activity,
    get_activity_logs,
    get_admin_user,
    get_admin_users,
    get_notification_queue_counts,
)


print("=" * 60)
print("DATABASE V2 TEST")
print("=" * 60)


# ------------------------------------------------------------
# 1. SETTINGS
# ------------------------------------------------------------

print("\n1. Testing settings...")

original_interval = get_setting(
    "crawler.interval_minutes"
)

print(
    "Original crawler interval:",
    original_interval
)

set_setting(
    "crawler.interval_minutes",
    15,
    updated_by="test"
)

new_interval = get_setting(
    "crawler.interval_minutes"
)

print(
    "Updated crawler interval:",
    new_interval
)

assert new_interval == 15

print("✅ Settings test passed")


# Restore original value
set_setting(
    "crawler.interval_minutes",
    original_interval,
    updated_by="test_cleanup"
)


# ------------------------------------------------------------
# 2. GET ALL SETTINGS
# ------------------------------------------------------------

print("\n2. Testing get_settings()...")

settings = get_settings()

print(
    "Settings loaded:",
    len(settings)
)

assert "crawler.enabled" in settings
assert "crawler.workers" in settings
assert "notifications.enabled" in settings

print("✅ get_settings() test passed")


# ------------------------------------------------------------
# 3. CRAWL RUN
# ------------------------------------------------------------

print("\n3. Testing crawl run tracking...")

run_id = create_crawl_run(
    workers=11,
    institutes_total=11,
    triggered_by="test",
)

print(
    "Created crawl run:",
    run_id
)

assert run_id is not None

update_crawl_run(
    run_id=run_id,
    status="success",
    duration_ms=80000,
    institutes_completed=11,
    institutes_failed=0,
    results_discovered=6172,
    results_new=0,
)

run = get_crawl_run(run_id)

print(
    "Crawl run:",
    run
)

assert run is not None
assert run[1] == "success"

print("✅ Crawl run test passed")


# ------------------------------------------------------------
# 4. LATEST CRAWL RUN
# ------------------------------------------------------------

print("\n4. Testing latest crawl run...")

latest = get_latest_crawl_run()

print(
    "Latest crawl run ID:",
    latest[0] if latest else None
)

assert latest is not None

print("✅ Latest crawl run test passed")


# ------------------------------------------------------------
# 5. ACTIVITY LOG
# ------------------------------------------------------------

print("\n5. Testing activity logs...")

log_activity(
    level="INFO",
    actor="test",
    action="database_test",
    target="database.py",
    message="Database V2 integration test",
    details={
        "test": True
    },
)

logs = get_activity_logs(
    limit=10,
    actor="test",
)

print(
    "Test activity logs:",
    len(logs)
)

assert len(logs) >= 1

print("✅ Activity log test passed")


# ------------------------------------------------------------
# 6. ADMIN USERS
# ------------------------------------------------------------

print("\n6. Testing admin user table...")

admins = get_admin_users()

print(
    "Admin users currently:",
    len(admins)
)

# We intentionally DO NOT create an admin here.
# Authentication/password hashing will be implemented
# in the FastAPI authentication step.

print("✅ Admin table accessible")


# ------------------------------------------------------------
# 7. NOTIFICATION QUEUE
# ------------------------------------------------------------

print("\n7. Testing notification queue stats...")

queue_counts = get_notification_queue_counts()

print(
    "Queue:",
    queue_counts
)

assert "pending" in queue_counts
assert "sent" in queue_counts
assert "failed" in queue_counts

print("✅ Notification queue test passed")


# ------------------------------------------------------------
# COMPLETE
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("🎉 DATABASE V2 TEST PASSED")
print("=" * 60)