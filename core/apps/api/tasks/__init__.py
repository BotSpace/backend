from .docker_task import *  # noqa
from .message import *  # noqa
from .project import *  # noqa
from .debug import *  # noqa
from .chat import *  # noqa
# Quyidagilarsiz celery worker bu modullardagi @shared_task'larni ro'yxatga olmaydi
# (autodiscover faqat tasks/__init__.py import qilgan modullarni ko'radi) → beat
# yuborgan task "unregistered" bo'lib tushadi.
from .file import *  # noqa
from .release import *  # noqa
from .monitoring import *  # noqa
