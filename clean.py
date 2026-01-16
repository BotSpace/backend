import re
from datetime import datetime, timezone, timedelta
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

NAMESPACE = "botmother"
DEBUG_MAX_AGE = timedelta(minutes=30)

# 1. Config
try:
    config.load_incluster_config()
except config.ConfigException:
    config.load_kube_config()

apps_v1 = client.AppsV1Api()

deployments = apps_v1.list_namespaced_deployment(namespace=NAMESPACE).items

release_pattern = re.compile(r"^release-(\d+)-(\d+)$")
debug_pattern = re.compile(r"^debug-\d+$")

now = datetime.now(timezone.utc)

release_map = {}
to_delete = set()

# 2. Tahlil
for dep in deployments:
    name = dep.metadata.name
    created_at = dep.metadata.creation_timestamp

    age = now - created_at

    status = dep.status
    available = status.available_replicas or 0
    ready = status.ready_replicas or 0
    healthy = available > 0 and ready > 0

    # DEBUG qoidasi
    if debug_pattern.match(name):
        if age > DEBUG_MAX_AGE:
            to_delete.add(name)
        continue

    # RELEASE qoidasi
    m = release_pattern.match(name)
    if not m:
        continue

    release_id = m.group(1)
    version = int(m.group(2))

    release_map.setdefault(release_id, []).append(
        {
            "name": name,
            "version": version,
            "healthy": healthy,
        }
    )

# 3. RELEASE delete logikasi
for release_id, items in release_map.items():
    healthy_items = [i for i in items if i["healthy"]]
    unhealthy_items = [i for i in items if not i["healthy"]]

    # ishlamaydiganlar har doim o‘chadi
    for i in unhealthy_items:
        to_delete.add(i["name"])

    if healthy_items:
        latest = max(healthy_items, key=lambda x: x["version"])
        for i in healthy_items:
            if i["name"] != latest["name"]:
                to_delete.add(i["name"])
    else:
        # umuman sog‘lom bo‘lmasa → hammasi o‘chadi
        for i in items:
            to_delete.add(i["name"])

# 4. DELETE
for name in sorted(to_delete):
    try:
        print(f"🗑 Deleting deployment: {name}")
        apps_v1.delete_namespaced_deployment(
            name=name,
            namespace=NAMESPACE,
            body=client.V1DeleteOptions(propagation_policy="Foreground"),
        )
    except ApiException as e:
        print(f"❌ Failed to delete {name}: {e}")
