import discord
from discord.ext import commands
from datetime import datetime
import sqlite3
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from datetime import timedelta


# =========================
# CONFIGURACION
# =========================

import os

TOKEN = os.getenv("DISCORD_TOKEN")

CANAL_VOTOS = 1469416472391712945

# =========================
# DISCORD
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# PATRON DE VOTOS
# =========================

patron = re.compile(
    r"^(.*?) acaba de votar por el servidor!$",
    re.IGNORECASE
)

# =========================
# BASE DE DATOS
# =========================

db = sqlite3.connect("votos.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS votos (
    mensaje_id INTEGER PRIMARY KEY,
    usuario TEXT,
    fecha TEXT
)
""")

db.commit()

# =========================
# EVENTOS
# =========================

@bot.event
async def on_ready():

    print(f"✅ Bot conectado como {bot.user}")

    if not hasattr(bot, "scheduler"):

        scheduler = AsyncIOScheduler(
            timezone=ZoneInfo("Europe/Madrid")
        )

        scheduler.add_job(
            publicar_top_semanal,
            CronTrigger(
                day_of_week="sun",
                hour=20,
                minute=0
            )
        )

        scheduler.add_job(
            publicar_top_mensual,
            CronTrigger(
                day=1,
                hour=20,
                minute=0
            )
        )

        scheduler.start()

        bot.scheduler = scheduler

        print("📅 Automatización iniciada")


@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    resultado = patron.match(message.content)

    if resultado:

        usuario = resultado.group(1).strip()

        print(f"VOTO DETECTADO: {usuario}")

        cursor.execute(
            "SELECT mensaje_id FROM votos WHERE mensaje_id=?",
            (message.id,)
        )

        existe = cursor.fetchone()

        if not existe:

            cursor.execute(
                """
                INSERT INTO votos
                (mensaje_id, usuario, fecha)
                VALUES (?, ?, ?)
                """,
                (
                    message.id,
                    usuario.casefold(),
                    message.created_at.isoformat()
                )
            )

            db.commit()

    await bot.process_commands(message)

# =========================
# COMANDOS
# =========================

@bot.command()
async def ping(ctx):
    await ctx.send("pong")


@bot.command()
async def total(ctx):

    cursor.execute(
        "SELECT COUNT(*) FROM votos"
    )

    total_votos = cursor.fetchone()[0]

    await ctx.send(
        f"📊 Total de votos guardados: {total_votos}"
    )


@bot.command()
async def importar(ctx):

    canal = bot.get_channel(CANAL_VOTOS)

    if canal is None:
        await ctx.send("❌ No encuentro el canal.")
        return

    contador = 0

    async for mensaje in canal.history(limit=None):

        resultado = patron.match(mensaje.content)

        if not resultado:
            continue

        usuario = resultado.group(1).strip().casefold()

        cursor.execute(
            "SELECT mensaje_id FROM votos WHERE mensaje_id=?",
            (mensaje.id,)
        )

        if cursor.fetchone():
            continue

        cursor.execute(
            """
            INSERT INTO votos
            (mensaje_id, usuario, fecha)
            VALUES (?, ?, ?)
            """,
            (
                mensaje.id,
                usuario,
                mensaje.created_at.isoformat()
            )
        )

        contador += 1

    db.commit()

    await ctx.send(
        f"✅ Importados {contador} votos."
    )


@bot.command()
async def topvotos(ctx):

    ahora = datetime.utcnow()

    cursor.execute(
        """
        SELECT usuario,
               COUNT(*) as votos
        FROM votos
        WHERE strftime('%m', fecha)=?
        AND strftime('%Y', fecha)=?
        GROUP BY usuario
        ORDER BY votos DESC
        LIMIT 10
        """,
        (
            f"{ahora.month:02}",
            str(ahora.year)
        )
    )

    ranking = cursor.fetchall()

    if not ranking:
        await ctx.send("❌ No hay votos este mes.")
        return

    texto = "🏆 TOP VOTANTES DEL MES 🏆\n\n"

    for i, (usuario, votos) in enumerate(ranking):

        nombre = usuario.title()

        if i == 0:
            texto += f"🥇 {nombre} - {votos} votos 💰 Premio: 150.000\n"

        elif i == 1:
            texto += f"🥈 {nombre} - {votos} votos 💰 Premio: 75.000\n"

        elif i == 2:
            texto += f"🥉 {nombre} - {votos} votos 💰 Premio: 50.000\n"

        else:
            texto += f"{i+1}. {nombre} - {votos} votos\n"

    await ctx.send(texto)
@bot.command()
async def topsemanal(ctx):

    from datetime import timedelta

    fecha_limite = datetime.utcnow() - timedelta(days=7)

    cursor.execute(
        """
        SELECT usuario,
               COUNT(*) as votos
        FROM votos
        WHERE fecha >= ?
        GROUP BY usuario
        ORDER BY votos DESC
        LIMIT 10
        """,
        (fecha_limite.isoformat(),)
    )

    ranking = cursor.fetchall()

    if not ranking:
        await ctx.send("❌ No hay votos esta semana.")
        return

    texto = "🏆 TOP 10 SEMANAL 🏆\n\n"

    for i, (usuario, votos) in enumerate(ranking):

        nombre = usuario.title()

        if i == 0:
            texto += f"🥇 {nombre} - {votos} votos 💰 Premio: 150.000\n"

        elif i == 1:
            texto += f"🥈 {nombre} - {votos} votos 💰 Premio: 75.000\n"

        elif i == 2:
            texto += f"🥉 {nombre} - {votos} votos 💰 Premio: 50.000\n"

        else:
            texto += f"{i+1}. {nombre} - {votos} votos\n"

    await ctx.send(texto)
MESES = [
"ENERO", "FEBRERO", "MARZO", "ABRIL",
"MAYO", "JUNIO", "JULIO", "AGOSTO",
"SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

async def publicar_top_semanal():

    canal = bot.get_channel(CANAL_VOTOS)

    if canal is None:
        return

    fecha_limite = datetime.utcnow() - timedelta(days=7)

    cursor.execute(
        """
        SELECT usuario,
               COUNT(*) as votos
        FROM votos
        WHERE fecha >= ?
        GROUP BY usuario
        ORDER BY votos DESC
        LIMIT 10
        """,
        (fecha_limite.isoformat(),)
    )

    ranking = cursor.fetchall()

    if not ranking:
        return

    texto = "🏆 TOP 10 SEMANAL 🏆\n\n"

    for i, (usuario, votos) in enumerate(ranking):

        nombre = usuario.title()

        if i == 0:
            texto += f"🥇 {nombre} - {votos} votos 💰 Premio: 150.000\n"
        elif i == 1:
            texto += f"🥈 {nombre} - {votos} votos 💰 Premio: 75.000\n"
        elif i == 2:
            texto += f"🥉 {nombre} - {votos} votos 💰 Premio: 50.000\n"
        else:
            texto += f"{i+1}. {nombre} - {votos} votos\n"

    await canal.send(texto)
async def publicar_top_mensual():

    canal = bot.get_channel(CANAL_VOTOS)

    if canal is None:
        return

    ahora = datetime.utcnow()

    if ahora.month == 1:
        mes = 12
        año = ahora.year - 1
    else:
        mes = ahora.month - 1
        año = ahora.year

    cursor.execute(
        """
        SELECT usuario,
               COUNT(*) as votos
        FROM votos
        WHERE strftime('%m', fecha)=?
        AND strftime('%Y', fecha)=?
        GROUP BY usuario
        ORDER BY votos DESC
        LIMIT 10
        """,
        (
            f"{mes:02}",
            str(año)
        )
    )

    ranking = cursor.fetchall()

    if not ranking:
        return

    texto = f"🏆 RESULTADOS FINALES DE {MESES[mes-1]} 🏆\n\n"

    for i, (usuario, votos) in enumerate(ranking):

        nombre = usuario.title()

        if i == 0:
            texto += f"🥇 {nombre} - {votos} votos 💰 Premio: 150.000\n"

        elif i == 1:
            texto += f"🥈 {nombre} - {votos} votos 💰 Premio: 75.000\n"

        elif i == 2:
            texto += f"🥉 {nombre} - {votos} votos 💰 Premio: 50.000\n"

        else:
            texto += f"{i+1}. {nombre} - {votos} votos\n"

    await canal.send(texto)


@bot.command()
async def testsemanal(ctx):

    await publicar_top_semanal()
    
@bot.command()
async def testmensual(ctx):
    await publicar_top_mensual()


# =========================
# INICIO
# =========================

bot.run(TOKEN)