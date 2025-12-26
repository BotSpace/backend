import logging
from typing import Optional
from telebot import TeleBot
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from core.apps.api.exceptions.bot import ReleaseBotTokenNotFound
from core.apps.api.models.project import EnviromentModel, ProjectModel


class TelegramBotService:

    def __init__(self, project: ProjectModel = None) -> None:
        self.storage = default_storage
        self.project = project
        self.me = None
        self.bot = None

    def set_bot(self, token: str):
        self.bot = TeleBot(token)

    def check_bot(self):
        if self.bot is None:
            raise Exception("Bot not set")

    def get_me(self):
        self.check_bot()
        if self.me is None:
            self.me = self.bot.get_me()
            return self.me
        return self.me

    def save(self):
        self.project.save()

    def set_project(self, project: ProjectModel):
        self.project = project
        try:
            token = EnviromentModel.objects.get(project=project, key="RELEASE_BOT_TOKEN").value
        except EnviromentModel.DoesNotExist:
            raise ReleaseBotTokenNotFound("RELEASE_BOT_TOKEN not found")
        self.set_bot(token)

    def get_me_username(self):
        return self.get_me().username

    def update_me_photo(self) -> Optional[str]:
        self.check_bot()
        me_id = self.get_me().id
        photos = self.bot.get_user_profile_photos(me_id).photos
        if len(photos) <= 0:
            return None
        file_id = photos[0][-1].file_id
        if self.project.avatar_file_id == file_id:
            return self.project.avatar.file_path
        self.project.avatar_file_id = file_id
        file_path = self.bot.get_file(file_id).file_path
        content = ContentFile(self.bot.download_file(file_path))
        avatar = self.storage.save("avatar/%s.jpg" % me_id, content)
        self.project.avatar = avatar
        logging.info("bot avatar updated=%s", avatar)
        return avatar

    def update_username(self):
        self.check_bot()
        username = self.get_me().username
        if username == self.project.username:
            return username
        self.project.username = username
        logging.info("bot username updated username=%s", username)
        return self.project.username
