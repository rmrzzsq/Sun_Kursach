import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from reports.services import content_volume, recent_log_entries, user_activity

a = user_activity()
print("ACTIVE:", a["active_users"], "| REGISTRATIONS:", a["registrations"])
for r in a["rows"]:
    print(" ", r["email"], "| up", r["uploads"], "dl", r["downloads"], "rev", r["reviews"], "com", r["comments"], "compl", r["complaints"])
print("TOTALS:", a["totals"])

v = content_volume()
print("MATERIALS:", v["materials_total"], "| FILES:", v["files_count"], "| BYTES:", v["total_bytes"])
print("STATUS:", [(s["label"], s["count"]) for s in v["by_status"]])
print("PUBLISHED:", v["published_in_period"], "| DOWNLOADS:", v["downloads_in_period"])
print("BY TYPE:", v["by_type"])
print("BY DISCIPLINE:", v["by_discipline"])

log = recent_log_entries(5)
print("LOG:", len(log), [e.object_repr for e in log])
from materials.models import Material
print("EVER_PUBLISHED:", Material.objects.filter(published_at__isnull=False).count())