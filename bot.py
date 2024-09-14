#!/usr/bin/env python3

"""Importing"""
# Importing External Packages
from pyrogram import Client, filters
from pyrogram.types import Update, Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.exceptions.bad_request_400 import (
    PeerIdInvalid, UserNotParticipant, ChannelPrivate, ChatIdInvalid, ChannelInvalid
)
from pymongo import MongoClient
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importing Credentials & Required Data
try:
    from testexp.config import *
except ModuleNotFoundError:
    from config import *

"""Connecting to Bot"""
app = Client(
    name="requesttracker",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Connecting To Database
mongo_client = MongoClient(Config.MONGO_STR)
db_bot = mongo_client['RequestTrackerBot']
collection_ID = db_bot['channelGroupID']

# Regular Expression for #request
requestRegex = "#[rR][eE][qQ][uU][eE][sS][tT] "

"""Handlers"""
# Start & Help Handler
@app.on_message(filters.private & filters.command(["start", "help"]))
async def startHandler(bot: Update, msg: Message):
    botInfo = await bot.get_me()
    await msg.reply_text(
        "Hi, this is SiC Request Bot 🤖.\n\nThe requests can be registered by typing ( #request ) in Dump group.\nMovies will be uploaded in UPLOADS CHANNEL only.\nRest of the things will be handled by Admins itself.\n\nMaintainer: Chaitanya Gupta (Team SiC)",
        parse_mode="markdown",
        reply_markup=InlineKeyboardMarkup(
            [InlineKeyboardButton("📤UPLOADS CHANNEL📤", url="https://t.me/+B_q7PnIdPJk5ZmY1")]
        )
    )

# Return group id when bot is added to group
@app.on_message(filters.new_chat_members)
async def chatHandler(bot: Update, msg: Message):
    if msg.new_chat_members[0].is_self:  # If bot is added
        await msg.reply_text(
            f"Hey😁, Your Group ID is {msg.chat.id}",
            parse_mode="markdown"
        )

# Return channel id when message/post from channel is forwarded
@app.on_message(filters.forwarded & filters.private)
async def forwardedHandler(bot: Update, msg: Message):
    forwardInfo = msg.forward_from_chat
    if forwardInfo.type == "channel":  # If message forwarded from channel
        await msg.reply_text(
            f"Hey😁, Your Channel ID is {forwardInfo.id}\n\n",
            parse_mode="markdown"
        )

# /add handler to add group id & channel id with database
@app.on_message(filters.private & filters.command("add"))
async def groupChannelIDHandler(bot: Update, msg: Message):
    message = msg.text.split(" ")
    if len(message) == 3:  # If command is valid
        _, groupID, channelID = message
        try:
            int(groupID)
            int(channelID)
        except ValueError:  # If Ids are not integer type
            await msg.reply_text(
                "Group ID & Channel ID should be integer type😒.",
                parse_mode="markdown"
            )
            return

        # If Ids are integer type
        documents = collection_ID.find()
        for document in documents:
            try:
                document[groupID]
            except KeyError:
                pass
            else:  # If group id found in database
                await msg.reply_text(
                    "Your Group ID already Added.",
                    parse_mode="markdown"
                )
                return

        # If group id & channel not found in db
        try:
            botSelfGroup = await bot.get_chat_member(int(groupID), 'me')
        except (PeerIdInvalid, ValueError):  # If given group id is invalid
            await msg.reply_text(
                "😒Group ID is wrong.\n",
                parse_mode="markdown"
            )
            return
        except UserNotParticipant:  # If bot is not in group
            await msg.reply_text(
                "😁Add me in group and make me admin, then use /add.\n",
                parse_mode="markdown"
            )
            return

        if botSelfGroup.status != "administrator":  # If bot is not admin in group
            await msg.reply_text(
                "🥲Make me admin in Group, Then use /add.\n\n",
                parse_mode="markdown"
            )
            return

        try:
            botSelfChannel = await bot.get_chat_member(int(channelID), 'me')
        except (UserNotParticipant, ChannelPrivate):  # If bot not in channel
            await msg.reply_text(
                "😁Add me in Channel and make me admin, then use /add.",
                parse_mode="markdown"
            )
            return
        except (ChatIdInvalid, ChannelInvalid):  # If given channel id is invalid
            await msg.reply_text(
                "😒Channel ID is wrong.\n\n",
                parse_mode="markdown"
            )
            return

        if not (botSelfChannel.can_post_messages and botSelfChannel.can_edit_messages and botSelfChannel.can_delete_messages):  # If bot has not enough permissions
            await msg.reply_text(
                "🥲Make sure to give Permissions like Post Messages, Edit Messages & Delete Messages.",
                parse_mode="markdown"
            )
            return

        # Adding Group ID, Channel ID & User ID in group
        collection_ID.insert_one({
            groupID: [channelID, msg.chat.id]
        })
        await msg.reply_text(
            "Your Group and Channel has now been added Successfully🥳.",
            parse_mode="markdown"
        )
    else:  # If command is invalid
        await msg.reply_text(
            "Invalid Format😒\nSend Group ID & Channel ID in this format /add GroupID ChannelID.\n",
            parse_mode="markdown"
        )

# /remove handler to remove group id & channel id from database
@app.on_message(filters.private & filters.command("remove"))
async def channelgroupRemover(bot: Update, msg: Message):
    message = msg.text.split(" ")
    if len(message) == 2:  # If command is valid
        _, groupID = message
        try:
            int(groupID)
        except ValueError:  # If group id not integer type
            await msg.reply_text(
                "Group ID should be integer type😒.",
                parse_mode="markdown"
            )
            return

        # If group id is integer type
        documents = collection_ID.find()
        for document in documents:
            try:
                document[groupID]
            except KeyError:
                continue
            else:  # If group id found in database
                if document[groupID][1] == msg.chat.id:  # If group id, channel id is removing by one who added
                    collection_ID.delete_one(document)
                    await msg.reply_text(
                        "Your Channel ID & Group ID has now been Deleted😢 from our Database.\nYou can add them again by using /add GroupID ChannelID.",
                        parse_mode="markdown"
                    )
                    return
                else:  # If group id, channel id is not removing by one who added
                    await msg.reply_text(
                        "😒You are not the one who added this Channel ID & Group ID.",
                        parse_mode="markdown"
                    )
                    return
        else:  # If group id not found in database
            await msg.reply_text(
                "Given Group ID is not found in our Database🤔.\n",
                parse_mode="markdown"
            )
            return
    else:  # If command is invalid
        await msg.reply_text(
            "Invalid Command😒\nUse /remove GroupID.",
            parse_mode="markdown"
        )

# #request handler
@app.on_message(filters.group & filters.regex(requestRegex + "(.*)"))
async def requestHandler(bot: Update, msg: Message):
    groupID = str(msg.chat.id)
    documents = collection_ID.find()
    for document in documents:
        try:
            document[groupID]
        except KeyError:
            continue
        else:  # If group id found in database
            channelID = document[groupID][0]
            fromUser = msg.from_user
            mentionUser = f"{fromUser.first_name}"
            requestText = f"Request by {mentionUser}\n\n{msg.text}"
            originalMSG = msg.text
            findRegexStr = match(requestRegex, originalMSG)
            requestString = findRegexStr.group()
            contentRequested = originalMSG.split(requestString)[1]

            try:
                groupIDPro = groupID.removeprefix(str(-100))
                channelIDPro = channelID.removeprefix(str(-100))
            except AttributeError:
                groupIDPro = groupID[4:]
                channelIDPro = channelID[4:]

            # Sending request in channel
            requestMSG = await bot.send_message(
                int(channelID),
                requestText,
                reply_markup=InlineKeyboardMarkup(
                    [
                        InlineKeyboardButton("Requested Message", url=f"https://t.me/c/{groupIDPro}/{msg.message_id}"),
                        InlineKeyboardButton("🚫Reject", "reject"),
                        InlineKeyboardButton("Done✅", "done"),
                        InlineKeyboardButton("⚠️Unavailable⚠️", "unavailable")
                    ]
                )
            )

            replyText = f"👋 Hello {mentionUser} !!\n\n Your Request has been added to queue.\n\n 👇 See Your Request Status Here 👇"
            # Sending message for user in group
            await msg.reply_text(
                replyText,
                parse_mode="markdown",
                reply_to_message_id=msg.message_id,
                reply_markup=InlineKeyboardMarkup(
                    [InlineKeyboardButton("⏳Request Status⏳", url=f"https://t.me/c/{channelIDPro}/{requestMSG.message_id}")]
                )
            )
            return

# Callback buttons handler
@app.on_callback_query()
async def callBackButton(bot: Update, callback_query: CallbackQuery):
    channelID = str(callback_query.message.chat.id)
    documents = collection_ID.find()
    for document in documents:
        for key in document:
            if key == "_id":
                continue
            else:
                if document[key][0] != channelID:
                    continue
                else:  # If channel id found in database
                    groupID = key
                    data = callback_query.data

                    if data == "rejected":
                        await callback_query.answer("This request is rejected💔...\nSearch in channel and request again", show_alert=True)
                        return
                    elif data == "completed":
                        await callback_query.answer("This request Is Completed🥳...\nCheckout in Channel😊", show_alert=True)
                        user = await bot.get_chat_member(int(channelID), callback_query.from_user.id)
                        if user.status not in ("administrator", "creator"):
                            # If accepting, rejecting request tried to be done by neither admin nor owner
                            await callback_query.answer("Wait.....??\nYou are not Admin😒.", show_alert=True)
                            return
                        else:
                            # If accepting, rejecting request tried to be done by either admin or owner
                            if data == "reject":
                                result = "REJECTED"
                                groupResult = "has been Rejected💔."
                                button = InlineKeyboardButton("Request Rejected🚫", "request again")
                            elif data == "done":
                                result = "COMPLETED"
                                groupResult = "is Completed🥳."
                                button = InlineKeyboardButton("Request Completed✅", "completed")
                            elif data == "unavailable":
                                result = "UNAVAILABLE"
                                groupResult = "has been rejected💔 due to Unavailability🥲."
                                button = InlineKeyboardButton("Request Rejected🚫", "request again")

                            msg = callback_query.message
                            userid = 12345678
                            for m in msg.entities:
                                if m.type == "text_mention":
                                    userid = m.user.id

                            originalMsg = msg.text
                            findRegexStr = search(requestRegex, originalMsg)
                            requestString = findRegexStr.group()
                            contentRequested = originalMsg.split(requestString)[1]
                            requestedBy = originalMsg.removeprefix("Request by ").split('\n\n')[0]
                            mentionUser = f"{requestedBy}"
                            originalMsgMod = originalMsg.replace(requestedBy, mentionUser)
                            originalMsgMod = f"{originalMsgMod}"
                            newMsg = f"{result}\n\n{originalMsgMod}"

                            # Editing request message in channel
                            await callback_query.edit_message_text(
                                newMsg,
                                parse_mode="markdown",
                                reply_markup=InlineKeyboardMarkup([button])
                            )

                            # Result of request sent to group
                            replyText = f"Dear {mentionUser}🧑\nYour request for {groupResult}\n(Team SiC)"
                            await bot.send_message(
                                int(groupID),
                                replyText,
                                parse_mode="markdown",
                                reply_markup=InlineKeyboardMarkup(
                                    [InlineKeyboardButton("📤UPLOAD CHANNEL📤", url="https://t.me/+B_q7PnIdPJk5ZmY1")]
                                )
                            )
                            return

"""Bot is Started"""
print("Bot has been Started!!!")
app.run()
