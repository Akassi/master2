import discord
from discord.ext import commands
import json

# Загрузка конфигурации из config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

API_KEY = config['API_KEY']

# Инициализация намерений и бота
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
intents.invites = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Команда для отправки информационного сообщения
@bot.command(name="message")
async def send_application_instructions(ctx):
    """Отправляет сообщение с инструкцией по подаче заявки."""
    embed = discord.Embed(
        title="📋 Подача заявки",
        description="Для получения доступа к нашему Discord-серверу, выполните следующие шаги:",
        color=discord.Color.green()
    )

    # Шаг 1: Регистрация игрового аккаунта
    embed.add_field(
        name="1️⃣ Шаг 1: Зарегистрируйте игровой аккаунт",
        value=(
            "Введите команду `/bind` в любом текстовом канале. Откроется окно, где нужно указать ваш игровой никнейм и ссылку на профиль Murderledger.\n\n"
            "- **Игровой никнейм**: Укажите ваш никнейм в игре (например, `Cruentis`).\n"
            "- **Ссылка на Murderledger**: Вставьте ссылку на ваш профиль (например, "
            "`https://murderledger-europe.albiononline2d.com/players/Cruentis/ledger`).\n\n"
            "После отправки формы ваш аккаунт будет зарегистрирован в нашей системе."
        ),
        inline=False
    )

    # Шаг 2: Присвоение роли
    embed.add_field(
        name="2️⃣ Шаг 2: Получение роли",
        value=(
            "После успешной регистрации аккаунта, вам будет автоматически присвоена роль `Registered`.\n\n"
            "Эта роль даст вам доступ к дальнейшим этапам подачи заявки."
        ),
        inline=False
    )

    embed.add_field(
        name="ℹ️ Дополнительная информация",
        value=(
            "Если у вас возникли вопросы или трудности с подачей заявки, "
            "вы можете обратиться за помощью к <@&1240091082717397106>."
        ),
        inline=False
    )

    # Добавление изображения
    embed.set_image(url="https://avatars.mds.yandex.net/i?id=eb6f0c989e5748db831c8a53045e5a34_l-5299374-images-thumbs&n=13")

    # Добавление миниатюры (логотип сервера или другой значок)
    embed.set_thumbnail(url="")

    # Добавление футера
    embed.set_footer(
        text="Server Application Team",
        icon_url="https://yt3.googleusercontent.com/NHyY4wQiak-sbpxba3Oyj5V_xJe8GJeMScF9eMFoCFazWsAuacSyHEKJLZWGMKSdQKBsE4Rknw=s900-c-k-c0x00ffffff-no-rj"
    )

    # Отправка сообщения
    await ctx.send(embed=embed)


@bot.command(name="message1")
async def send_application_instructions(ctx):
    """Sends a message with application submission instructions."""
    embed = discord.Embed(
        title="📋 Application Submission",
        description="To gain access to our Discord server, please follow these steps:",
        color=discord.Color.green()
    )

    # Step 1: Game Account Registration
    embed.add_field(
        name="1️⃣ Step 1: Register your Game Account",
        value=(
            "Use the `/bind` command in any text channel. A window will appear where you need to enter your game nickname and Murderledger profile link.\n\n"
            "- **Game Nickname**: Provide your in-game nickname (e.g., `Cruentis`).\n"
            "- **Murderledger Link**: Paste the link to your profile (e.g., "
            "`https://murderledger-europe.albiononline2d.com/players/Cruentis/ledger`).\n\n"
            "After submitting the form, your account will be registered in our system."
        ),
        inline=False
    )

    # Step 2: Role Assignment
    embed.add_field(
        name="2️⃣ Step 2: Role Assignment",
        value=(
            "After your game account has been successfully registered, you will automatically receive the `Registered` role.\n\n"
            "This role will give you access to the next steps in the application process."
        ),
        inline=False
    )

    # Additional Information
    embed.add_field(
        name="ℹ️ Additional Information",
        value=(
            "If you have any questions or encounter any issues during the application process, "
            "feel free to reach out to <@&1240091082717397106> for assistance."
        ),
        inline=False
    )

    # Adding an image
    embed.set_image(url="https://avatars.mds.yandex.net/i?id=eb6f0c989e5748db831c8a53045e5a34_l-5299374-images-thumbs&n=13")

    # Setting a thumbnail (optional logo or icon)
    embed.set_thumbnail(url="")

    # Adding a footer
    embed.set_footer(
        text="Server Application Team",
        icon_url="https://yt3.googleusercontent.com/NHyY4wQiak-sbpxba3Oyj5V_xJe8GJeMScF9eMFoCFazWsAuacSyHEKJLZWGMKSdQKBsE4Rknw=s900-c-k-c0x00ffffff-no-rj"
    )

    # Sending the message
    await ctx.send(embed=embed)


# Запуск бота
bot.run(API_KEY)