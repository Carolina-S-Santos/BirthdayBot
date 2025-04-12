import discord
import json
from datetime import datetime
import asyncio
import os
from dotenv import load_dotenv
import os
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta

load_dotenv()

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
MY_GUILD = discord.Object(id=GUILD_ID)

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CANAL_ANIVERSARIO = '🎂-birthdays'
ARQUIVO_JSON = "birthdays.json"

# Função para carregar aniversários
def carregar_aniversarios():
    if not os.path.exists(ARQUIVO_JSON):
        return []
    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

# Função para salvar aniversários
def salvar_aniversarios(aniversarios):
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(aniversarios, f, indent=2, ensure_ascii=False)

# Comando para adicionar um aniversário
@tree.command(name="adicionaraniversario", description="Adiciona aniversário de um membro", guild=MY_GUILD)

@app_commands.describe(membro="Usuário do servidor", data="Data no formato DD/MM (ex: 29/03)")
async def adicionaraniversario(interaction: discord.Interaction, membro: discord.Member, data: str):
    try:
        datetime.strptime(data, "%d/%m")
    except ValueError:
        await interaction.response.send_message("❌ Data inválida. Use o formato DD/MM", ephemeral=True)
        return

    aniversarios = carregar_aniversarios()

    for pessoa in aniversarios:
        if pessoa["user_id"] == membro.id:
            pessoa["data"] = data
            pessoa["nome"] = membro.display_name
            break
    else:
        aniversarios.append({
            "nome": membro.display_name,
            "user_id": membro.id,
            "data": data,
            "ultimo_envio": "nunca"
        })

    salvar_aniversarios(aniversarios)
    await interaction.response.send_message(f"✅ Aniversário de {membro.mention} salvo para {data}!")

@tree.command(name="adicionaraniversarioexterno", description="Adiciona aniversário de alguém que não está no servidor", guild=MY_GUILD)
@app_commands.describe(nome="Nome da pessoa", data="Data no formato DD/MM (ex: 29/03)")
async def adicionaraniversarianteexterno(interaction: discord.Interaction, nome: str, data: str):
    try:
        datetime.strptime(data, "%d/%m")
    except ValueError:
        await interaction.response.send_message("❌ Data inválida. Use o formato DD/MM", ephemeral=True)
        return

    aniversarios = carregar_aniversarios()

    for pessoa in aniversarios:
        if pessoa.get("nome") == nome and pessoa.get("user_id") is None:
            pessoa["data"] = data
            break
    else:
        aniversarios.append({
            "nome": nome,
            "user_id": None,
            "data": data,
            "ultimo_envio": "nunca"
        })

    salvar_aniversarios(aniversarios)
    await interaction.response.send_message(f"✅ Aniversário de {nome} salvo para {data}!")


# Tarefa que verifica aniversários diariamente
async def verificar_aniversarios_diario():
    await bot.wait_until_ready()

    while not bot.is_closed():
        agora = datetime.now()
        proxima_execucao = agora.replace(hour=7, minute=30, second=0, microsecond=0)

        # Se já passou de 07:30 hoje, agenda para amanhã
        if agora >= proxima_execucao:
            # === Verifica aniversários ===
            await verifica_aniversarios()
            proxima_execucao += timedelta(days=1)  # Fallback para final do mês
            
        segundos_ate_execucao = (proxima_execucao - agora).total_seconds()
        print(f"⏰ Próxima verificação em {segundos_ate_execucao/60:.1f} minutos")
        await asyncio.sleep(segundos_ate_execucao)

        # === Verifica aniversários ===
        await verifica_aniversarios()


async def verifica_aniversarios():
    hoje = datetime.now().strftime("%d/%m")
    aniversarios = carregar_aniversarios()
    canal = discord.utils.get(bot.get_all_channels(), name=CANAL_ANIVERSARIO)

    if not canal:
        print("❌ Canal de aniversários não encontrado.")
        return

    guild = bot.get_guild(GUILD_ID)

    for pessoa in aniversarios:
        if pessoa["data"] == hoje and pessoa["ultimo_envio"] != datetime.now().strftime("%d/%m/%Y"):
            try:
                if pessoa.get("user_id"):
                    membro = guild.get_member(pessoa["user_id"])
                    if not membro:
                        print(f"⚠️ Membro com ID {pessoa['user_id']} não encontrado.")
                        continue

                    roles = [role.name.lower() for role in membro.roles]

                    if "world-class developer" in roles:
                        await canal.send(f"💻 Atenção @everyone !\n🎉 Feliz aniversário, {membro.mention}! 🎉 Hoje o seu bug foi promovido a feature: mais um ano de vida! 🎂")
                    elif "world-class designer" in roles:
                        await canal.send(f"🎨 Atenção @everyone !\n🎉 Feliz aniversário, {membro.mention} Seu ciclo de vida foi atualizado com sucesso:\n✔️ Versão nova\n✔️ Melhor experiência do usuário\n❌ Nenhuma melhoria de performance após o café 🎉")

                else:
                    # Para aniversariantes externos
                    await canal.send(f"Atenção @everyone !\n🎉 Sistema detectou aniversário de **{pessoa['nome']}**.\nStatus: Not Found\nInterpretação: Fugindo da equipe pra evitar parabéns.\nResultado: Falhou. Parabéns enviado mesmo assim. 🎈")
                
                # Registrar que foi enviado uma mensagem de aniversario 
                pessoa["ultimo_envio"] = datetime.now().strftime("%d/%m/%Y")
            except Exception as e:
                print(f"Erro ao enviar mensagem: {e}")
                
    # Salva os aniversarios para registrar as mensagens enviadas
    salvar_aniversarios(aniversarios)

verificacao_em_andamento = False
@bot.event
async def on_ready():
    global verificacao_em_andamento
    print(f"✅ Bot conectado como {bot.user}")
    await tree.sync(guild=MY_GUILD)

    if not verificacao_em_andamento:
        verificacao_em_andamento = True
        asyncio.create_task(verificar_aniversarios_diario())

bot.run(TOKEN)
