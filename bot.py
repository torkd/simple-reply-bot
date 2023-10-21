import asyncio
import logging
import sys
import json
from os import getenv
import time
import re

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import Message, ChatMemberUpdated, Chat, User
from aiogram.utils.markdown import bold
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = getenv("BOT_TOKEN")
OWNER_ID = getenv("OWNER_ID")

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

# Classes
## Admin Handler
class Admins(object):
    def __init__(self, config_path:str, owner_id: int) -> None:
        self.config_path = config_path
        self.private_add = list()
        if not self.load_admins():
            if owner_id:
                self.init_owner(owner_id)
            else:
                self.claimable = True

    def init_owner(self, owner_id: int) -> None:
        self.admin_list = dict()
        self.admin_list["owner"] = [owner_id]
        self.admin_list["admin"] = list()
        self.admin_list["admin_info"] = dict()
        self.claimable = False
        with open(self.config_path, 'w') as fh:
            json.dump(self.admin_list, fh, indent=4)

    def load_admins(self) -> bool:
        try:
            with open(self.config_path, 'r') as fh:
                self.admin_list = json.load(fh)
            if self.admin_list["owner"]:
                self.claimable = False
                return True
        except FileNotFoundError:
            return False
        
    def save_admins(self) -> None:
        with open(self.config_path, 'w') as fh:
            json.dump(self.admin_list, fh, indent=4)

    def is_admin(self, user: User) -> bool:
        if self.is_owner(user) or user.id in self.admin_list["admin"]:
            return True
        else: return False
        
    def is_owner(self, user: User) -> bool:
        if user.id in self.admin_list["owner"]:
            return True
        else: return False
        
    def add_admin(self, user: User) -> bool:
        if user.id in self.admin_list["admin"]: return False
        else:
            self.admin_list["admin"].append(user.id)
            self.admin_list["admin_info"][str(user.id)] = user.first_name
            self.save_admins()
            return True
        
    def remove_admin(self, user_id: str) -> str:
        self.admin_list["admin"].remove(int(user_id))
        admin_name = self.admin_list["admin_info"].pop(user_id)
        self.save_admins()
        return admin_name

    def set_private_add(self, chat: Chat) -> None:
        self.private_add.append(chat.id)
    
    def reset_private_add(self) -> None:
        self.private_add = list()
        
    def claim(self, user: User) -> bool:
        if self.claimable:
            self.init_owner(user.id)
            return True
        else:
            return False

## Commands Handler
class CommandHandler(object):
    def __init__(self, path: str) -> None:
        self.config_path = path
        self.commands_admin, self.commands_user = self.load_commands(path)

    def load_commands(self, path: str) -> dict:
        with open(path, 'r') as fh:
            commands = json.load(fh)
            return commands["admin"], commands["user"]
        
    def add_command(self, command: str, answer: str, type: str) -> None:
        admin_commands, user_commands = self.load_commands(self.config_path)
        if type == "admin":
            admin_commands[str(command)] = answer
            self.commands_admin = admin_commands
        elif type == "user":
            user_commands[str(command)] = answer
            self.commands_user = user_commands
        self.save_commands(admin_commands, user_commands)

    def delete_command(self, command: str) -> bool:
        if command in self.commands_admin:
            self.commands_admin.pop(command)
        elif command in self.commands_user:
            self.commands_user.pop(command)
        else:
            return False
        self.save_commands(self.commands_admin, self.commands_user)
        return True

    def save_commands(self, admin_commands: dict, user_commands: dict) -> None:
        commands = dict()
        commands['admin'] = admin_commands
        commands['user'] = user_commands
        with open(self.config_path, 'w') as fh:
            json.dump(commands, fh, indent=4)

    def get_answer(self, command: str, user: User, admin_handler: Admins) -> str:
        if command in self.commands_admin:
            if admin_handler.is_admin(user):
                return self.commands_admin[command]
        elif command in self.commands_user:
            return self.commands_user[command]
    
    def reload_commands(self, user: User, adming_handler: Admins) -> None:
        if adming_handler.is_owner(user):
            self.commands_admin, self.commands_user = self.load_commands(self.config_path)

## New Commands Handler
class NewCommandHandler(object):
    def __init__(self) -> None:
        self.current_step = None
        self.current_step_id = None
        pass

    def set_busy(self):
        self.current_step = "init"
    
    def set_init_step_id(self, message_id: int, command_type: str) -> None:
        self.current_step = "command"
        self.command_type = command_type
        self.current_step_id = message_id

    def set_command(self, message_id:int, command_text: str) -> None:
        self.current_step = "answer"
        self.new_command = command_text
        self.current_step_id = message_id

    def set_answer(self, answer_text: str) -> None:
        self.current_step = "commit"
        self.new_answer = answer_text #self.auto_escape(answer_text)

    def commit_new_command(self, ch: CommandHandler) -> None:
        ch.add_command(self.new_command, self.new_answer, self.command_type)
        self.reset()

    def reset(self):
        self.current_step = None
        self.current_step_id = None

@dp.callback_query()
async def cb_handler(callback_query: types.CallbackQuery) -> None:    
    if ah.is_admin(callback_query.from_user):
        await callback_query.answer()
        callback_data = callback_query.data
        if callback_data in ("admin", "user"):
            await callback_query.message.edit_reply_markup(reply_markup=None)
            reply = await callback_query.message.answer("This will be a \"{}\" command. Now please reply to this message with the command you'd like to add. "\
                                                "It can't contain any space, nor emoji or markdown.".format(callback_data))
            new_command_handler.set_init_step_id(reply.message_id, callback_data)
        elif callback_data in ("commit", "no_commit"):
            if callback_data == "commit":
                await callback_query.message.edit_reply_markup(reply_markup=None)
                new_command_handler.commit_new_command(ch)
                await callback_query.message.answer("The command has been added!")
            else:
                await callback_query.message.edit_reply_markup(reply_markup=None)
                new_command_handler.reset()
                await callback_query.message.answer("The command has not been added and the process has been reset.")
        elif callback_data.split(":")[0] == "remove_admin" and ah.is_owner(callback_query.from_user):
            admin_name = ah.remove_admin(callback_data.split(":")[1])
            await callback_query.message.edit_reply_markup(reply_markup=None)
            await callback_query.message.answer("*{}* has been removed from the admins\.".format(admin_name), parse_mode=ParseMode.MARKDOWN_V2)
        elif callback_data.split(":")[0] == "remove_command":
            if ch.delete_command(callback_data.split(":")[1]):
                await callback_query.message.edit_reply_markup(reply_markup=None)
                await callback_query.message.answer("The `/{}` command has been deleted\.".format(callback_data.split(":")[1]), parse_mode=ParseMode.MARKDOWN_V2)
    

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    if message.chat.type == "private":
        await message.answer("Hello, {}!\n"\
                             "I'm a bot developed by @e621drake for @ShadowVoyd.\n"\
                             "If you want to run me too, you can find me on [DockerHub](https://hub.docker.com/r/torkd/simple-reply-bot).\n"\
                             "Please if you're not an admin do not send me private messages, I'm not instructed to handle them.".format(bold(message.from_user.full_name), parse_mode=ParseMode.MARKDOWN_V2))
    else: pass

@dp.message(Command("reload"))
async def command_reload(message: Message) -> None:
    """
    This handler reloads the config file.
    """
    if message.chat.type == "private":
        ch.reload_commands(message.from_user, ah)
        await message.answer("Commands loaded.")

@dp.message(Command("addcommand"))
async def add_command(message: Message) -> None:    
    if message.chat.type == "private":
        if ah.is_admin(message.from_user):
            if len(message.text[1:].split(" ")) > 1:
                if message.text[1:].split(" ")[1] == "reset":
                    new_command_handler.reset()
                    await message.answer("The process of adding a new command has been reset.")
            else:
                if new_command_handler.current_step == None:        
                    builder = InlineKeyboardBuilder()
                    builder.button(text="Admin", callback_data="admin").button(text="User", callback_data="user")
                    await message.answer("Who should be able to answer to this command?", reply_markup=builder.as_markup())
                else:
                    await message.reply("A new command is already being added, please complete the process or reset it with `/addcommand reset`\.", parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(Command("delcommand"))
async def delete_command(message: Message) -> None:
    if message.chat.type == "private" and ah.is_admin(message.from_user):
        builder = InlineKeyboardBuilder()
        for command in ch.commands_admin.keys():
            builder.button(text="/{}".format(command), callback_data="remove_command:{}".format(command))
        for command in ch.commands_user.keys():
            builder.button(text="/{}".format(command), callback_data="remove_command:{}".format(command))
        builder.adjust(4, repeat=True)
        await message.answer("Which command do you wish to remove?", reply_markup=builder.as_markup())

@dp.message(Command("claim"))
async def claim_bot(message: Message) -> None:
    if message.chat.type == "private":    
        if ah.claim(message.from_user):
            await message.answer("Congratulations {}\! You are now my owner\. "\
                                 "You can now add new admins by using the `/addadmin` command\."
                                 .format(message.from_user.first_name), parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await message.answer("I'm sorry, but I already have an owner.")

@dp.message(Command("addadmin"))
async def add_admin(message: Message) -> None:
    if ah.is_owner(message.from_user):
        if message.chat.type == "private":
            ah.set_private_add(message.chat)
            await message.answer("Alright, now forward me a message from the person you wish to add as an admin.")
        if message.chat.type in ("group", "supergroup"):
            if message.reply_to_message:
                if ah.add_admin(message.reply_to_message.from_user):
                    await message.answer("*{}* has been added as an admin\!".format(message.reply_to_message.from_user.first_name), parse_mode=ParseMode.MARKDOWN_V2)
                else:
                    await message.answer("*{}* is already an admin\.".format(message.reply_to_message.from_user.first_name), parse_mode=ParseMode.MARKDOWN_V2)
            else:
                await message.answer("To add an admin you need to reply to the person you wish to add as an admin with the `/addadmin` command\.", parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(Command("deladmin"))
async def delete_admin(message: Message) -> None:
    if ah.is_owner(message.from_user):
        if message.chat.type == "private":
            builder = InlineKeyboardBuilder()
            for user in ah.admin_list["admin_info"].keys():
                builder.button(text="{}".format(ah.admin_list["admin_info"][user]), callback_data="remove_admin:{}".format(user))
            builder.adjust(3, repeat=True)
            await message.answer("Who would you like to remove?", reply_markup=builder.as_markup())

@dp.message()
async def general_commands_handler(message: Message) -> None:
    """
    This handler receives all messages and passes the ones with a '/' prefix through the given config JSON file.
    A match will answer with the text found in the config file.
    """

    if message.reply_to_message and message.reply_to_message.message_id == new_command_handler.current_step_id and ah.is_admin(message.from_user):
            if new_command_handler.current_step == "command":
                if " " in message.text:
                    await message.reply("The command contains spaces, which are not allowed. Please reply to the previous message again.")
                else:
                    if message.text not in (list(ch.commands_admin.keys()) + list(ch.commands_user.keys())):
                        reply = await message.reply("Alright, now reply to this message with the desired answer\.\n"\
                                                    "It can only contain text and emojis, but you can format it as you wish\ (bold, italics, strikethrough, links, etc)!", parse_mode=ParseMode.MARKDOWN_V2)
                        new_command_handler.set_command(reply.message_id, message.text)
                    else:
                        await message.reply("That command already exists\. "\
                                            "Please reply to the previous message again with a different one or reset the procedure with `/addcommand reset`\.\n"\
                                            "You can also delete a command with `/delcommand`\.", parse_mode=ParseMode.MARKDOWN_V2)
            elif new_command_handler.current_step == "answer":
                new_command_handler.set_answer(message.md_text)
                builder = InlineKeyboardBuilder()
                builder.button(text="Yes", callback_data="commit").button(text="No", callback_data="no_commit")
                await message.reply("Alright\! Let's recap the new command\.\n"\
                                    "*Command type*: {}\n"\
                                    "*Command*: /{}\n"\
                                    "*Answer*: {}\n"\
                                    "Do you want to commit this command?"
                                    .format(new_command_handler.command_type, new_command_handler.new_command, new_command_handler.new_answer), reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN_V2)

    if message.chat.type == "private" and message.forward_from and (message.chat.id in ah.private_add):
        ah.reset_private_add()
        if ah.add_admin(message.forward_from):            
            await message.answer("Alright, *{}* has been added as an admin\.".format(message.forward_from.first_name), parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await message.answer("*{}* is already an admin\.".format(message.forward_from.first_name), parse_mode=ParseMode.MARKDOWN_V2)
        
    if message.text[0] == "/" and (message.chat.type in ("group", "supergroup")):
        try:
            if "@" in message.text:
                message_text = message.text.split("@")[0]
            else: message_text = message.text
            await message.answer(ch.get_answer(message_text[1:], message.from_user, ah), parse_mode=ParseMode.MARKDOWN_V2)
        except KeyError:
            logging.warning("Command not found: {}".format(message.text[1:]))
    else: pass

async def main() -> None:
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(TOKEN, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    # And the run events dispatching
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    ch = CommandHandler("/bot/config/config.json")
    new_command_handler = NewCommandHandler()
    ah = Admins("/bot/config/admins.json", OWNER_ID)
    asyncio.run(main())