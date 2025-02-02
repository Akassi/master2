import datetime

import discord
from discord.ext import commands
from discord import app_commands
import psycopg2
from psycopg2 import sql
import re
from discord.ext import tasks
import json

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

DB_NAME = config['DB_NAME']
DB_USER = config['DB_USER']
DB_PASSWORD = config['DB_PASSWORD']
DB_HOST = config['DB_HOST']
DB_PORT = config['DB_PORT']
API_KEY = config['API_KEY']
ROLE_ID = config['ROLE_ID']
FARMER_ROLE_ID = config['FARMER_ROLE_ID']
RAID_LEADER_ROLE_ID = config['RAID_LEADER_ROLE_ID']
UNBIND_ROLE_ID = config['UNBIND_ROLE_ID']
CHANNEL_IDS = config['CHANNEL_IDS']
REGISTRATION_CHANNEL_ID = config['REGISTRATION_CHANNEL_ID']
APPROVE_LOG_CHANNEL_ID = config['APPROVE_LOG_CHANNEL_ID']
CITADEL_EU_GUILD = config['CITADEL_EU_GUILD']
CITADEL_EU_CHANNEL = config['CITADEL_EU_CHANNEL']
CITADEL_EU_LOG_CHANNEL_ID = config['CITADEL_EU_LOG_CHANNEL_ID']
FINED_ROLE_ID = config['CITADEL_EU_FINED_ROLE_ID']
CITADEL_EU_BOSS_ROLE_ID = config['CITADEL_EU_BOSS_ROLE_ID']
GOT_FINED_CHANNEL = config['GOT_FINED_CHANNEL']
OTHER_LOG_CHANNEL = config['OTHER_LOG_CHANNEL']
CITADEL_RAID_LEADER_ROLE_ID = config['CITADEL_RAID_LEADER_ROLE_ID']

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
intents.invites = True

bot = commands.Bot(command_prefix='!', intents=intents)

ALLOWED_CHANNEL_ID = config['ALLOWED_CHANNEL_ID']

def check_channel(interaction: discord.Interaction):
    # Логируем команду перед проверкой
    return interaction.guild_id == ALLOWED_CHANNEL_ID

@bot.event
async def on_member_join(member: discord.Member):
    """Triggered when a member joins the guild / Событие, когда пользователь присоединяется к гильдии."""

    if member.guild.id == CITADEL_EU_GUILD:
        try:
            # Подключаемся к базе данных / Connect to the database
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()

            check_approve_query = sql.SQL("""
                SELECT is_approved, approvedbydiscordid FROM public.approve_list
                WHERE discordid = %s AND is_approved = true
            """)

            select_nickname_query = sql.SQL("""
                SELECT nickname FROM public.user_nick
                WHERE discordid = %s AND is_active = true
            """)

            cursor.execute(check_approve_query, (str(member.id),))
            result = cursor.fetchone()

            if not result or not result[0]:
                print(
                    f"Пользователь {member.display_name} не одобрен в системе. / User {member.display_name} is not approved.")
                return

            approvedbydiscordid = result[1]

            role = member.guild.get_role(FARMER_ROLE_ID)

            if role is None:
                print(f"Роль с ID {FARMER_ROLE_ID} не найдена. / Role with ID {FARMER_ROLE_ID} not found.")
                return

            # Назначаем роль / Assign role to the user
            await member.add_roles(role)
            print(
                f"Роль {role.name} успешно выдана пользователю {member.display_name}. / Role {role.name} successfully assigned to {member.display_name}.")

            cursor.execute(select_nickname_query, (str(member.id),))
            nickname_result = cursor.fetchone()

            if nickname_result:
                nickname = nickname_result[0]

                # Проверяем, нужно ли обновить никнейм / Check if nickname needs to be updated
                if member.nick != nickname:
                    try:
                        await member.edit(nick=nickname)
                        print(
                            f"Никнейм {nickname} успешно обновлен для {member.display_name}. / Nickname {nickname} successfully updated for {member.display_name}.")
                    except Exception as e:
                        print(
                            f"Ошибка при изменении никнейма для {member.display_name}: {str(e)} / Error updating nickname for {member.display_name}: {str(e)}")

            log_channel = member.guild.get_channel(CITADEL_EU_LOG_CHANNEL_ID)
            if log_channel:
                approver = member.guild.get_member(int(approvedbydiscordid))
                approver_login = approver.display_name if approver else "Unknown"
                await log_channel.send(
                    f"ApproveMaster: {approvedbydiscordid} ({approver_login})\n"
                    f"Пользователь / User: <@{member.id}>\n"
                    f"DiscordID: {member.id}"
                )

        except Exception as e:
            print(
                f"Произошла ошибка при обработке пользователя {member.display_name}: {str(e)} / Error processing user {member.display_name}: {str(e)}")
        finally:
            cursor.close()
            conn.close()


@bot.tree.command(name="getlink", description="Получить ссылку для вступления в канал / Get the invite link")
@app_commands.checks.check(check_channel)  # Проверка на разрешенный канал
async def get_invite_link(interaction: discord.Interaction):
    """Команда для получения одноразовой ссылки на приглашение / Command to get a one-time invite link."""
    discord_id = interaction.user.id
    
    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        # Подключение к базе данных / Connect to the database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Проверка аппрува / Check if the user is approved
        check_approve_query = sql.SQL("""
            SELECT is_approved FROM public.approve_list 
            WHERE discordid = %s AND is_approved = true
        """)

        # Проверка, есть ли уже ссылка / Check if an invite link already exists
        check_link_query = sql.SQL("""
            SELECT invite_link FROM public.invite_link 
            WHERE discordid = %s
        """)

        # Вставка новой ссылки / Insert a new invite link
        insert_link_query = sql.SQL("""
            INSERT INTO public.invite_link (discordid, invite_link) 
            VALUES (%s, %s)
        """)

        # Проверка статуса аппрува / Check approval status
        cursor.execute(check_approve_query, (str(discord_id),))
        result = cursor.fetchone()

        if not result or not result[0]:
            await interaction.followup.send(
                "Ваш аккаунт не был одобрен или вы не подавали заявку. / Your account is not approved or you have not applied.",
                ephemeral=True
            )
            return

        cursor.execute(check_link_query, (str(discord_id),))
        link_result = cursor.fetchone()

        if link_result:
            await interaction.followup.send(
                f"Ваша ссылка для вступления: {link_result[0]} / Your invite link: {link_result[0]}",
                ephemeral=True
            )
            return

        citadel_guild = bot.get_guild(CITADEL_EU_GUILD)
        if not citadel_guild:
            await interaction.followup.send(
                "Не удалось найти указанную гильдию. / Could not find the specified guild.",
                ephemeral=True
            )
            return

        member = citadel_guild.get_member(discord_id)
        if member:
            await interaction.followup.send(
                "Вы уже являетесь участником этого дискорда, ссылка не требуется. / You are already a member of this Discord, no invite required.",
                ephemeral=True
            )
            return

        # Получаем канал для инвайта / Get the invite channel
        invite_channel = citadel_guild.get_channel(CITADEL_EU_CHANNEL)
        if invite_channel is None:
            await interaction.followup.send(
                "Не удалось найти указанный канал для создания инвайта. / Could not find the specified channel for invite creation.",
                ephemeral=True
            )
            return

        invite = await invite_channel.create_invite(max_uses=1, max_age=86400, unique=True)

        # Вставляем новую ссылку / Insert the new invite link
        cursor.execute(insert_link_query, (str(discord_id), invite.url))
        conn.commit()

        await interaction.followup.send(
            f"Ваша ссылка для вступления: {invite.url} / Your invite link: {invite.url}",
            ephemeral=True
        )

    except Exception as e:
        conn.rollback()
        await interaction.followup.send(
            f"Произошла ошибка при создании ссылки: {str(e)} / Error creating the invite link: {str(e)}",
            ephemeral=True
        )
    finally:
        cursor.close()
        conn.close()

@bot.tree.command(name="approve", description="Аппрувнуть игровую учетную запись / Approve game account")
@app_commands.checks.check(check_channel)  # Проверка на разрешенный канал
@app_commands.checks.has_role(UNBIND_ROLE_ID)
async def approve_account(interaction: discord.Interaction, member: discord.Member):
    """Команда для аппрува аккаунта / Command to approve a game account."""
    discord_id = member.id
    approver_id = interaction.user.id

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        update_approve_query = sql.SQL("""
            UPDATE public.approve_list
            SET is_approved = true, approvedbydiscordid = %s
            WHERE discordid = %s AND is_applicant = true AND is_approved = false
        """)
        cursor.execute(update_approve_query, (str(approver_id), str(discord_id)))
        conn.commit()

        if cursor.rowcount == 0:
            await interaction.followup.send(
                f"Не удалось аппрувнуть {member.mention}, возможно, он уже аппрувнут или не подавал заявку. / Could not approve {member.mention}, they might already be approved or did not apply.",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            f"Аккаунт {member.mention} успешно аппрувнут. / Account {member.mention} successfully approved.",
            ephemeral=True
        )

        approve_log_channel = interaction.guild.get_channel(APPROVE_LOG_CHANNEL_ID)
        if approve_log_channel:
            await approve_log_channel.send(
                f"ApproveMaster: <@{approver_id}>\n"
                f"Пользователь / User: <@{discord_id}>\n"
                f"DiscordID: {discord_id}"
            )

        embed = discord.Embed(
            title="🎉 Поздравляем! / Congratulations! 🎉",
            description=(
                f"**{member.mention}, ваша заявка была успешно одобрена!**\n"
                "➡️ Для получения ссылки на приглашение в основной дискорд канал введите команду `/getlink`.\n\n"
                f"**{member.mention}, your application has been successfully approved!**\n"
                "➡️ To receive the invite link to the main Discord, please use the `/getlink` command."
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="Server Application Team",
            icon_url="https://yt3.googleusercontent.com/NHyY4wQiak-sbpxba3Oyj5V_xJe8GJeMScF9eMFoCFazWsAuacSyHEKJLZWGMKSdQKBsE4Rknw=s900-c-k-c0x00ffffff-no-rj"
        )

        await interaction.channel.send(content=f"{member.mention}", embed=embed)

    except Exception as e:
        conn.rollback()
        await interaction.followup.send(
            f"Произошла ошибка при аппруве аккаунта: {str(e)} / Error approving account: {str(e)}",
            ephemeral=True
        )
    finally:
        cursor.close()
        conn.close()


@bot.tree.command(name="unbind", description="Деактивировать игровую учетную запись / Unbind game account")
@app_commands.checks.check(check_channel)  # Проверка на разрешенный канал
@app_commands.checks.has_role(UNBIND_ROLE_ID)
async def unbind_account(interaction: discord.Interaction, member: discord.Member):

    """Команда для деактивации аккаунта и удаления роли / Command to unbind a game account and remove a role."""
    discord_id = member.id

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        # Подключение к базе данных / Connect to the database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        delete_approve_query = sql.SQL("""
            DELETE FROM public.approve_list
            WHERE discordid = %s AND is_applicant = true
        """)
        cursor.execute(delete_approve_query, (str(discord_id),))
        conn.commit()

        update_query = sql.SQL("""
            UPDATE public.user_nick
            SET is_active = false
            WHERE discordid = %s AND is_active = true
        """)
        cursor.execute(update_query, (str(discord_id),))
        conn.commit()

        role = interaction.guild.get_role(ROLE_ID)
        if role and role in member.roles:
            await member.remove_roles(role)

        await interaction.followup.send(
            f"Аккаунт {member.mention} деактивирован и роль {role.name} удалена. / Account {member.mention} deactivated and role {role.name} removed.",
            ephemeral=True
        )

    except Exception as e:
        conn.rollback()
        await interaction.followup.send(
            f"Произошла ошибка при деактивации аккаунта: {str(e)} / Error deactivating account: {str(e)}",
            ephemeral=True
        )
    finally:
        cursor.close()
        conn.close()


@bot.tree.command(name="bind", description="Привязать игровой аккаунт / Bind your game account")
@app_commands.checks.check(check_channel)  # Проверка на разрешенный канал
async def bind_account(interaction: discord.Interaction):

    """Команда для привязки игрового аккаунта / Slash command to bind a game account via a modal."""
    modal = AccountModal()
    await interaction.response.send_modal(modal)


class AccountModal(discord.ui.Modal, title="Bind Account"):
    """Модальное окно для привязки аккаунта / Modal window for account binding."""
    nickname = discord.ui.TextInput(
        label="Игровой никнейм / Game Nickname",
        placeholder="Например, Cruentis / e.g., Cruentis"
    )
    murderledger = discord.ui.TextInput(
        label="Ссылка на murderledger / Murderledger Link",
        placeholder="Например, https://murderledger-europe.albiononline2d.com/players/Adeyno/ledger"
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Обработка данных из модального окна / Process data from modal."""
        discord_id = interaction.user.id
        nickname = self.nickname.value
        murderledger = self.murderledger.value

        await interaction.response.defer(ephemeral=True, thinking=True)

        url_pattern = re.compile(r'^https://')
        if not url_pattern.match(murderledger):
            await interaction.followup.send(
                "Неверный формат ссылки! Invalid link format!",
                ephemeral=True
            )
            return

        try:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()

            check_active_account_query = sql.SQL("""
                SELECT is_active FROM public.user_nick 
                WHERE discordid = %s AND is_active = true
            """)
            cursor.execute(check_active_account_query, (str(discord_id),))
            active_account = cursor.fetchone()

            if active_account:
                await interaction.followup.send(
                    "У вас уже есть активная регистрация. Повторная регистрация невозможна. / You already have an active registration. Multiple registrations are not allowed.",
                    ephemeral=True
                )
                return

            insert_user_query = sql.SQL("""
                INSERT INTO public.user_nick (discordid, murderledger, nickname)
                VALUES (%s, %s, %s)
            """)
            cursor.execute(insert_user_query, (str(discord_id), murderledger, nickname))
            conn.commit()

            insert_approve_query = sql.SQL("""
                INSERT INTO public.approve_list (discordid, is_applicant, is_approved)
                VALUES (%s, true, false)
            """)
            cursor.execute(insert_approve_query, (str(discord_id),))
            conn.commit()

            role = interaction.guild.get_role(ROLE_ID)
            if role:
                await interaction.user.add_roles(role)
                await interaction.followup.send(
                    "Аккаунт успешно привязан / Account successfully bound.",
                    ephemeral=True
                )

                registration_channel = interaction.guild.get_channel(REGISTRATION_CHANNEL_ID)
                if registration_channel:
                    await registration_channel.send(
                        f"<@{discord_id}>\n"
                        f"DiscordID: {discord_id} \n"
                        f"Nickname: {nickname}\n"
                        f"Murderledger: {murderledger}"
                    )

                increment_ticket_count_query = sql.SQL("""
                    UPDATE public.tickets_count
                    SET count = count + 1
                    RETURNING count;
                """)
                cursor.execute(increment_ticket_count_query)
                ticket_count = cursor.fetchone()[0]
                conn.commit()

                await create_ticket_channel(interaction, ticket_count)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(
            f"Произошла ошибка при записи в базу данных: {str(e)} / Error writing to the database: {str(e)}",
            ephemeral=True)
        finally:
            cursor.close()
            conn.close()


@tasks.loop(minutes=1.5)
async def update_nicknames():
    """Периодически обновляет никнеймы пользователей / Periodically updates nicknames for users with a certain role."""
    for guild in bot.guilds:
        nickname_role = guild.get_role(ROLE_ID)
        if not nickname_role:
            continue

        try:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()

            select_query = sql.SQL("""
                SELECT discordid, nickname FROM public.user_nick WHERE is_active = true
            """)
            cursor.execute(select_query)
            user_nick_data = cursor.fetchall()

            for discord_id, nickname in user_nick_data:
                member = guild.get_member(int(discord_id))
                if member and nickname_role in member.roles:
                    if member.nick != nickname:
                        try:
                            await member.edit(nick=nickname)
                            print(
                                f"Никнейм обновлен для {member}: {nickname} / Nickname updated for {member}: {nickname}")
                        except Exception as e:
                            print(
                                f"Ошибка при изменении никнейма для {member}: {str(e)} / Error updating nickname for {member}: {str(e)}")

        except Exception as e:
            print(f"Ошибка при получении данных из базы: {str(e)} / Error fetching data from the database: {str(e)}")
        finally:
            cursor.close()
            conn.close()


@tasks.loop(minutes=1)
async def auto_assign_role():
    """Периодически проверяет approve_list и автоматически назначает роль / Periodically checks approve_list and assigns roles automatically."""
    for guild in bot.guilds:
        role = guild.get_role(ROLE_ID)
        if not role:
            continue

        try:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()

            select_approve_query = sql.SQL("""
                SELECT discordid FROM public.approve_list WHERE is_applicant = true
            """)
            cursor.execute(select_approve_query)
            applicants = cursor.fetchall()

            for (discord_id,) in applicants:
                member = guild.get_member(int(discord_id))
                if member and role not in member.roles:
                    try:
                        await member.add_roles(role)
                        print(
                            f"Роль {role.name} выдана {member} автоматически. / Role {role.name} automatically assigned to {member}.")
                    except Exception as e:
                        print(
                            f"Ошибка при выдаче роли {role.name} для {member}: {str(e)} / Error assigning role {role.name} to {member}: {str(e)}")

        except Exception as e:
            print(
                f"Ошибка при получении данных из approve_list: {str(e)} / Error fetching data from approve_list: {str(e)}")
        finally:
            cursor.close()
            conn.close()


@bot.event
async def on_message(message: discord.Message):
    """Удаляет все сообщения в указанных каналах, кроме сообщений от бота / Deletes all messages in specified channels except the bot's messages."""
    if message.channel.id in CHANNEL_IDS and message.author != bot.user:
        await message.delete()

    await bot.process_commands(message)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready and logged in as {bot.user}")

    if not update_nicknames.is_running():
        update_nicknames.start()
        print("Задача update_nicknames запущена. / Nickname update task started.")

    # Запускаем задачу для автоматической выдачи ролей / Start the role assignment task
    if not auto_assign_role.is_running():
        auto_assign_role.start()
        print("Задача auto_assign_role запущена. / Role assignment task started.")

async def create_ticket_category(guild: discord.Guild, ticket_count: int):
    """Создаёт или находит категорию для тикетов в зависимости от диапазона."""

    print(f"[INFO] Старт создания текстового канала для тикета {ticket_count}")

    lower_bound = (ticket_count - 1) // 50 * 50 + 1
    upper_bound = lower_bound + 49
    category_name = f"tickets_{lower_bound}-{upper_bound}"

    print(f"[INFO] Определен диапазон тикетов: {lower_bound}-{upper_bound} (Название категории: {category_name})")

    # Проверяем, существует ли уже такая категория
    category = discord.utils.get(guild.categories, name=category_name)

    if category:
        print(f"[INFO] Найдена существующая категория: {category_name}")
    else:
        print(f"[INFO] Категория {category_name} не найдена. Создание новой категории.")

        guild_id = ALLOWED_CHANNEL_ID  # Указанный ID гильдии
        guild = bot.get_guild(guild_id)  # Используем ID для получения гильдии

        if guild:
            print(f"[INFO] Гильдия с ID {guild_id} найдена. Создание новой категории в ней.")
            category = await guild.create_category(name=category_name)
        else:
            print(f"[ERROR] Гильдия с ID {guild_id} не найдена.")
            return None

    print(f"[INFO] Категория {category_name} успешно обработана.")
    return category

async def create_ticket_channel(interaction: discord.Interaction, ticket_count: int):
    """Создаёт канал тикета в нужной категории."""
    category = await create_ticket_category(interaction.guild, ticket_count)

    ticket_channel_name = f"ticket_{ticket_count}"
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        # Default users cannot see the channel
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        # User can see and send messages
        interaction.guild.get_role(RAID_LEADER_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    ticket_channel = await category.create_text_channel(ticket_channel_name, overwrites=overwrites)

    embed = discord.Embed(
        title="⚠️ Важно!!! / Important!!! ⚠️",
        description=(
            "Информация для русскоязычных игроков:**\n"
            "🌍 **Этот дискорд предназначен только для Европейского сервера.**\n"
            "🚫 **Не пингуйте никого после подачи заявки.**\n\n"

            "__📋 Обязательные поля для заполнения:__\n"
            "```"
            "- Ник (Европа):\n"
            "- Ник (Америка) (если есть):\n"
            "- Дискорд РЛ/офицера, кто вас позвал:\n"
            "- Сколько вам лет:\n"
            "- Есть ли опыт фарма мировых боссов:\n"
            "- Есть ли опыт ПВП на мировых боссах:\n"
            "- Ссылка на ваш профиль на murderledger.com:\n"
            "- Ссылка на ваш профиль на albiondb.net:\n"
            "- Скриншот выбора персонажа:\n"
            "- Скриншот параметров в игре:\n"
            "```\n\n"

            "\nInformation for English-speaking players:**\n"
            "🌍 **This Discord is for the European server only.**\n"
            "🚫 **Do not ping anyone after applying.**\n\n"

            "__📋 Required fields to fill in:__\n"
            "```"
            "- Nickname (Europe):\n"
            "- Nickname (America) (if applicable):\n"
            "- Discord of RL/officer who invited you:\n"
            "- Your age:\n"
            "- Do you have experience in farming world bosses:\n"
            "- Do you have experience in PvP on world bosses:\n"
            "- Link to your murderledger.com profile:\n"
            "- Link to your albiondb.net profile:\n"
            "- Screenshot of character selection:\n"
            "- Screenshot of in-game stats:\n"
            "```"
        ),
        color=discord.Color.blue()

    )
    embed.set_footer(
        text="Server Application Team",
        icon_url="https://yt3.googleusercontent.com/NHyY4wQiak-sbpxba3Oyj5V_xJe8GJeMScF9eMFoCFazWsAuacSyHEKJLZWGMKSdQKBsE4Rknw=s900-c-k-c0x00ffffff-no-rj"
    )

    await ticket_channel.send(content=f"<@{interaction.user.id}>", embed=embed)

@bot.tree.command(name="finedlistadd", description="Добавить пользователя в список оштрафованных и выдать штрафную роль")
@app_commands.checks.has_role(CITADEL_EU_BOSS_ROLE_ID)
async def finedlistadd(interaction: discord.Interaction, member: discord.Member):
    """Команда для добавления пользователя в таблицу fined_list и выдачи штрафной роли."""
    await interaction.response.defer(ephemeral=True)  # Делаем defer, чтобы избежать ошибки времени ожидания

    if interaction.guild.id != CITADEL_EU_GUILD:
        await interaction.followup.send("Эту команду можно использовать только в целевой гильдии.", ephemeral=True)
        return

    if member.voice is not None and member.voice.channel is not None:
        await interaction.followup.send(f"Пользователь {member.mention} находится в голосовом канале. Штраф невозможен.", ephemeral=True)
        return

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        select_fine_query = sql.SQL("""
            SELECT * FROM public.fined_list
            WHERE discordid = %s AND is_active = %s
        """)
        cursor.execute(select_fine_query, (str(member.id), True))
        existing_fine = cursor.fetchone()

        if existing_fine:
            await interaction.followup.send(f"Пользователь {member.mention} уже оштрафован и имеет активный штраф.", ephemeral=True)
            return

        current_roles = [role.id for role in member.roles if role != interaction.guild.default_role]

        role_list_str = ','.join(map(str, current_roles))
        create_date = datetime.datetime.now()  # Изменяем вызов datetime

        insert_fine_query = sql.SQL("""
            INSERT INTO public.fined_list (discordid, role_list, create_date, is_active)
            VALUES (%s, %s, %s, %s)
        """)
        cursor.execute(insert_fine_query, (str(member.id), role_list_str, create_date, True))
        conn.commit()

        fined_role = discord.utils.get(interaction.guild.roles, id=FINED_ROLE_ID)
        await member.edit(roles=[fined_role])

    except Exception as e:
        conn.rollback()
        await interaction.followup.send(f"Произошла ошибка при добавлении пользователя в список оштрафованных: {str(e)}", ephemeral=True)
    finally:
        cursor.close()
        conn.close()

    # Создаём Embed-сообщение
    embed = discord.Embed(
        title="🚫 Вы оштрафованы! / You have been fined! 🚫",
        description=(f"**{member.mention}, вы получили штраф и ваши роли были временно сняты.**\n\n"
                     "➡️ На оплату штрафа у вас есть 24 часа. В течение этого времени вы ограничены в доступе к основным каналам.\n"
                     "Если вы записаны на таймер (рейд, событие и т.д.), **немедленно предупредите вашего РЛА** о вашем штрафе.\n\n"
                     "📝 **Инструкция по оплате штрафа:**\n"
                     "* Вы должны внести штраф в гильдию через любого вашего глазика или попросить кого-то другого это сделать за вас.\n"
                     "* После пополнения необходимо сделать скриншот подтверждения и загрузить его в соответствующую ветку канала.\n"
                     f"**{member.mention}, you have been fined and your roles have been temporarily removed.**\n\n"
                     "➡️ You have 24 hours to pay the fine. During this period, you are restricted from accessing main channels.\n"
                     "If you are scheduled for a timer (raid, event, etc.), **immediately notify your raid leader (RLA)** about your fine.\n\n"
                     "📝 **Fine payment instructions:**\n"
                     "* You need to deposit the fine into the guild bank through any of your eyes or ask someone else to do it for you.\n"
                     "* After the payment, you must take a screenshot of the confirmation and upload it to the designated channel thread.\n"),
        color=discord.Color.red()
    )

    embed.set_footer(
        text="Администрация сервера / Server Administration",
        icon_url="https://yt3.googleusercontent.com/NHyY4wQiak-sbpxba3Oyj5V_xJe8GJeMScF9eMFoCFazWsAuacSyHEKJLZWGMKSdQKBsE4Rknw=s900-c-k-c0x00ffffff-no-rj"
    )

    await interaction.channel.send(content=f"{member.mention}", embed=embed)
    await interaction.followup.send(f"Пользователь {member.mention} оштрафован, и его роли сохранены.", ephemeral=True)

@bot.tree.command(name="finedlistremove", description="Удалить пользователя из списка оштрафованных и восстановить его роли")
@app_commands.checks.has_role(CITADEL_EU_BOSS_ROLE_ID)
async def finedlistremove(interaction: discord.Interaction, member: discord.Member):
    """Команда для удаления пользователя из fined_list и возврата всех ролей."""
    await interaction.response.defer(ephemeral=True)  # Делаем defer, чтобы избежать ошибки времени ожидания

    if interaction.guild.id != CITADEL_EU_GUILD:
        await interaction.followup.send("Эту команду можно использовать только в целевой гильдии.", ephemeral=True)
        return

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        select_fine_query = sql.SQL("""
            SELECT role_list FROM public.fined_list
            WHERE discordid = %s AND is_active = %s
        """)
        cursor.execute(select_fine_query, (str(member.id), True))
        row = cursor.fetchone()

        if row is None:
            await interaction.followup.send(f"Активного штрафа для {member.mention} не найдено.", ephemeral=True)
            return

        role_ids = map(int, row[0].split(','))
        roles = [discord.utils.get(interaction.guild.roles, id=role_id) for role_id in role_ids if discord.utils.get(interaction.guild.roles, id=role_id) is not None]
        await member.edit(roles=roles)

        fined_role = discord.utils.get(interaction.guild.roles, id=FINED_ROLE_ID)
        await member.remove_roles(fined_role)

        update_fine_query = sql.SQL("""
            UPDATE public.fined_list
            SET is_active = %s
            WHERE discordid = %s AND is_active = %s
        """)
        cursor.execute(update_fine_query, (False, str(member.id), True))
        conn.commit()

    except Exception as e:
        conn.rollback()
        await interaction.followup.send(f"Произошла ошибка при удалении пользователя из списка оштрафованных: {str(e)}", ephemeral=True)
    finally:
        cursor.close()
        conn.close()

    await interaction.followup.send(f"Пользователь {member.mention} больше не оштрафован, и его роли восстановлены.", ephemeral=True)

@bot.tree.command(name="got_fined", description="Штрафовать пользователя и записать штраф в базу данных")
@app_commands.checks.has_any_role(CITADEL_RAID_LEADER_ROLE_ID, CITADEL_EU_BOSS_ROLE_ID)
async def got_fined(interaction: discord.Interaction, member: discord.Member, amount: int, reason: str):
    """Команда для штрафа пользователя и записи штрафа в базу данных, а также создания ветки в канале для обсуждения штрафа"""

    if interaction.guild.id != CITADEL_EU_GUILD:
        await interaction.response.send_message("Эту команду можно использовать только в целевой гильдии.",
                                                ephemeral=True)
        return

    discord_id = interaction.user.id  # ID того, кто выполняет команду
    fined_discordid = member.id  # ID того, кто получает штраф

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        insert_fine_query = sql.SQL("""
            INSERT INTO public.got_fined (discordid, fined_discordid, amount, reason)
            VALUES (%s, %s, %s, %s)
        """)
        cursor.execute(insert_fine_query, (str(discord_id), str(fined_discordid), amount, reason))
        conn.commit()

        await interaction.response.send_message(
            f"Пользователь {member.mention} был оштрафован на сумму {amount} за причину: {reason}.",
            ephemeral=True
        )

        log_channel = interaction.guild.get_channel(OTHER_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(
                f"**Fine**\n"
                f"Fined by: <@{discord_id}> ({discord_id})\n"
                f"Fined user: <@{fined_discordid}> ({fined_discordid})\n"
                f"Amount: {amount}kk\n"
                f"Reason: {reason}"
            )

        target_channel = interaction.guild.get_channel(GOT_FINED_CHANNEL)
        if target_channel:
            # Создаем обычное текстовое сообщение
            fine_message_text = (
                f"🚫 **New Fine!** 🚫\n\n"
                f"**User:** {member.mention}\n"
                f"**Fine amount:** {amount}kk\n"
                f"**Reason:** {reason}\n"
                f"**Fined by:** {interaction.user.mention}\n"  # Упоминание того, кто выписал штраф
            )

            fine_message = await target_channel.send(fine_message_text)

            fine_thread = await fine_message.create_thread(name=f"{member.display_name}")

            embed = discord.Embed(
                title="🚨 Внимание! / Warning! 🚨",
                description=(
                    f"**{member.mention}, вы получили штраф в размере {amount}kk за нарушение правил.**\n"
                    "🚫 На данный момент вы еще не потеряли доступ к основным каналам, но **если вы не оплатите штраф в течение ближайших 24 часов**, "
                    "ваш доступ ко всем каналам будет ограничен, и вам грозит полный бан!\n\n"
                    "🔴 **Оплатите штраф как можно быстрее, чтобы избежать дальнейших проблем.**\n\n"
                    "📝 **Инструкция по оплате штрафа:**\n"
                    "* Штраф необходимо внести в гильдию через вашего глазика или попросить другого игрока сделать это за вас.\n"
                    "* После оплаты обязательно сделайте скриншот подтверждения и загрузите его в эту ветку.\n"
                    "⚠️ **Если вы не оплатите штраф в течение 24 часов, вы потеряете доступ ко всем каналам и получите дальнейшие санкции.**\n"
                    "Пожалуйста, не затягивайте с оплатой, чтобы избежать дополнительных последствий.\n\n"
                    "❗ **Если вы не согласны со штрафом**, вы должны **полностью обосновать свою позицию** и приложить соответствующие скриншоты или любую дополнительную информацию "
                    "в эту ветку. Это поможет рассмотреть вашу жалобу и вынести окончательное решение.\n\n"
                    f"**{member.mention}, you have been fined {amount}kk.**\n"
                    "🚫 You still have access to the main channels, but **if you do not pay the fine within the next 24 hours**, "
                    "your access to all channels will be revoked, and you risk getting banned!\n\n"
                    "🔴 **Pay the fine as soon as possible to avoid further issues.**\n\n"
                    "📝 **Fine payment instructions:**\n"
                    "* You need to deposit the fine into the guild bank through your eyes or ask someone else to do it for you.\n"
                    "* After the payment, take a screenshot of the confirmation and upload it to this thread.\n"
                    "⚠️ **If you do not pay the fine within 24 hours, you will lose access to all channels and face further sanctions.**\n"
                    "Please do not delay the payment to avoid additional consequences.\n\n"
                    "❗ **If you disagree with the fine**, you must **fully explain your position** and provide relevant screenshots or any additional information "
                    "in this thread. This will help review your case and make a final decision."
                ),
                color=discord.Color.red()  # Цвет красный для указания на важность
            )

            # Отправка сообщения в ветку
            await fine_thread.send(content=f"{member.mention}", embed=embed)

    except Exception as e:
        conn.rollback()
        await interaction.followup.send(f"Произошла ошибка при записи штрафа: {str(e)}", ephemeral=True)
    finally:
        cursor.close()
        conn.close()

# Запуск бота / Run the bot
bot.run(API_KEY)
