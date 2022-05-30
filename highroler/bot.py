import json
import logging
import os

import BTrees.OOBTree
import discord
import transaction
from dotenv import load_dotenv

from highroler.db import db, User

load_dotenv()

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())
if os.getenv('DEBUG_LOG'):
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)

log.debug("initializing")


@client.event
async def on_ready():
    log.info(f'Initialized as {client.user}')
    log.debug("init db")
    connection = db.open()
    log.debug("session start")
    root = connection.root
    if not hasattr(root, 'users'):
        log.debug("init user root!")
        root.users = BTrees.OOBTree.BTree()
    log.debug("==== getting all members ====")
    for user in client.get_all_members():
        log.debug(f"[USER] {user.guild.id}: {user} -- {user.id}")
        if root.users.get(user.id) is None:
            log.debug("--- user not in database")
            root.users[user.id] = User(user.id)
        log.debug(f"--- {user.roles}")
        root.users[user.id].roles = [role.id for role in user.roles]
    transaction.commit()
    log.debug("==== getting all channels ====")
    for ch in client.get_all_channels():
        log.debug(f"[CHAN] {user.guild.id}: {ch} -- {ch.id}")
        for overwrites in ch.overwrites:
            if type(overwrites) == discord.Member:
                log.debug(f"--- {overwrites}")
                if root.users.get(user.id) is not None:
                    log.debug(f"--- --- updated {ch.overwrites[overwrites].pair()}")
                    root.users[user.id].overwrites[ch.id] = ch.overwrites[overwrites]
    transaction.commit()
    connection.close()


@client.event
async def on_member_update(before, after):
    log.debug("==== member update! ====")
    connection = db.open()
    log.debug("session start")
    root = connection.root
    log.debug(f"[USER] {after.guild.id}: {after} -- {after.id}")
    if root.users.get(after.id) is None:
        log.debug("--- user not in database")
        root.users[after.id] = User(after.id)
    log.debug(f"--- roles {after.roles}")
    root.users[after.id].roles = [role.id for role in after.roles]
    transaction.commit()
    connection.close()


@client.event
async def on_guild_channel_update(before, after):
    log.debug("==== channel update! ====")
    connection = db.open()
    log.debug("session start")
    root = connection.root
    log.debug(f"[CHAN] {after.guild.id}: {after} -- {after.id}")
    for overwrites in after.overwrites:
        if type(overwrites) == discord.Member:
            log.debug(f"--- {overwrites}")
            if root.users.get(overwrites.id) is not None:
                log.debug(f"--- --- updated {after.overwrites[overwrites].pair()}")
                root.users[overwrites.id].overwrites[after.id] = after.overwrites[overwrites]
    transaction.commit()
    connection.close()


@client.event
async def on_member_join(member):
    log.debug("==== member join! ====")
    connection = db.open()
    log.debug("session start")
    root = connection.root
    log.debug(f"[USER] {member.guild.id}: {member} -- {member.id}")
    if root.users.get(member.id) is not None:
        log.debug("--- user in database")
        if root.users[member.id].roles is not None:
            log.debug("--- user has roles")
            roles = []
            for role in root.users[member.id].roles:
                role = member.guild.get_role(role)
                if not (role.is_default() or role.is_bot_managed() or role.is_premium_subscriber() or role.is_integration()):
                    roles.append(role)
            log.debug(f"--- restoring {roles}")
            await member.add_roles(*roles, reason="restoring roles")
        for channel_id, overwrite in root.users[member.id].overwrites.items():
            channel = await client.fetch_channel(channel_id)
            log.debug(f"--- restoring perms {member} @ {channel} ({channel.id}): {overwrite}")
            await channel.set_permissions(member, overwrite=overwrite, reason="restoring access")
    else:
        log.debug("--- user not in database")
    connection.close()


@client.event
async def on_member_remove(member):
    log.debug("==== member leave! ====")
    connection = db.open()
    log.debug("session start")
    root = connection.root
    log.debug(f"[USER] {member.guild.id}: {member} -- {member.id}")
    if root.users.get(member.id) is None:
        log.debug("--- user not in database")
        root.users[member.id] = User(member.id)
    log.debug(f"--- {member.roles}")
    root.users[member.id].roles = [role.id for role in member.roles]

    transaction.commit()
    connection.close()

client.run(os.getenv('TOKEN'))