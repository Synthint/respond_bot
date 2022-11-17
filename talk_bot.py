from happytransformer import HappyGeneration
from happytransformer import GENSettings
import discord
from discord.ext import commands
import os
import dotenv
import speech_recognition
from gtts import gTTS
import asyncio
import speech_recognition
from pydub import AudioSegment


dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

recognizer = speech_recognition.Recognizer()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)


MAX_CYCLES = 5
args = GENSettings(no_repeat_ngram_size=2)
top_k_sampling_settings = GENSettings(do_sample=True, early_stopping=False,top_k=50,temperature=0.7,no_repeat_ngram_size=2,)
global hap_gen
hap_gen = HappyGeneration("GPT-NEO", "EleutherAI/gpt-neo-125M")
#hap_gen = HappyGeneration("GPT-NEO", "EleutherAI/gpt-neo-1.3B") 



global botVoiceChannel
botVoiceChannel = 0
genCycles = 1


async def connectVoice(ctx, *args):
    global botVoiceChannel
    auth = ctx.author
    voiceChannel = auth.voice.channel
    if voiceChannel != None:
        vc = await voiceChannel.connect()
        botVoiceChannel = vc
    else:
        ctx.send("user not in VC")

@bot.command()
async def disconnectVoice(ctx, *args):
    global botVoiceChannel
    vc = botVoiceChannel
    await vc.disconnect()
    vc = 0
    botVoiceChannel = vc

@bot.command()
async def useSmallGen(ctx, *args):
    global hap_gen
    await ctx.send("swapping, may take a few seconds, will alert when complete")
    hap_gen = HappyGeneration("GPT-NEO", "EleutherAI/gpt-neo-125M")
    await ctx.send("now using EleutherAI/gpt-neo-125M")

@bot.command()
async def useBigGen(ctx, *args):
    global hap_gen
    await ctx.send("swapping, may take a few seconds, will alert when complete")
    hap_gen = HappyGeneration("GPT-NEO", "EleutherAI/gpt-neo-1.3B") 
    await ctx.send("now using EleutherAI/gpt-neo-1.3B")


@bot.command()
async def updateCycles(ctx, *args):
    global genCycles
    if int(args[0]) > MAX_CYCLES:
        await ctx.send(f"{args[0]} is more than MAX_CYCLES = {MAX_CYCLES}")
    genCycles = min(int(args[0]), MAX_CYCLES)
    await ctx.send(f"generation cylces is set to {genCycles}")


@bot.command()
async def listen(ctx):  # If you're using commands.Bot, this will also work.
    voice = ctx.author.voice

    if not voice:
        await ctx.send("You aren't in a voice channel!")
    global botVoiceChannel
    if botVoiceChannel == 0:
        await connectVoice(ctx)

    vc = botVoiceChannel

    vc.start_recording(
        discord.sinks.MP3Sink(),  # The sink type to use.
        once_done,  # What to do once done.
        ctx.channel  # The channel to disconnect from.
    )
    await ctx.send("Started recording!")

@bot.command()
async def respond(ctx):
    global botVoiceChannel
    vc = botVoiceChannel
    vc.stop_recording()  # Stop recording, and call the callback (once_done).


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):  
    files = [
        discord.File(audio.file, f"{user_id}.{sink.encoding}") 
        for user_id, audio in sink.audio_data.items()
        ]
    global genCycles
    for user_id, audio in sink.audio_data.items():
        print(audio.file)
        print(type(audio))
        print(user_id)
        saveInputAudio(audio.file,str(user_id))
        voiceIn = recognizeFromVoice(str(user_id)+".wav")
        output = generateText(promptinit=voiceIn,cycles = genCycles)
        print("\n\nINPUT:\n"+voiceIn+"\n===============================\n\n")
        print("\n\nOUTPUT:\n"+output+"\n===============================\n\n")
        outFile = "temp.mp3"
        saveOutputAudio(output,outFile)
        await speakAudio(outFile)




async def speakAudio(filename):
    global botVoiceChannel
    vc = botVoiceChannel
    vc.play(discord.FFmpegPCMAudio(source=filename), after=print("Done"))
    while vc.is_playing():
            await asyncio.sleep(1)


def recognizeFromVoice(filename,fromLang = "en"):
    with speech_recognition.AudioFile(filename) as source:
        audioData = recognizer.record(source)
    print(type(audioData))
    text = recognizer.recognize_google(audioData,language=fromLang,show_all=True)
    return text["alternative"][0]["transcript"]


def saveOutputAudio(input, filename):
    txt = input
    toLang = "en"
    audio = gTTS(text=txt, lang=toLang, slow=False)
    audio.save(filename)


def saveInputAudio(aud,fileName):
    fileMP3 = fileName+".mp3"
    fileWave = fileName+".wav"
    with open(fileMP3,"wb") as f:
        f.write(aud.read())
    f.close
    # saving as wav file didnt work, resulted in corrupted file
    # saves as mp3, then convert to wav. extra work but
    # allows the program to function
    sound = AudioSegment.from_mp3(fileMP3)
    sound.export(fileWave, format="wav")
    sound = AudioSegment.from_wav(fileWave)
    sound = sound.set_channels(1)
    sound.export(fileWave, format="wav")

def generateText(promptinit = "",prompt="", cycles = 0):
    if cycles > MAX_CYCLES:
        print(f">\n>Max Cycles is {MAX_CYCLES}, defaulting to max\n>")
        cycles = MAX_CYCLES
    if len(promptinit) != 0:
        result = hap_gen.generate_text(promptinit, args = top_k_sampling_settings)
    else:
        result = hap_gen.generate_text(prompt, args = top_k_sampling_settings)
    if cycles == 0:
        return result.text
    else:
        return generateText(prompt = prompt+result.text,cycles = cycles-1)




TOKEN = os.environ.get("TOKEN")
try:
    bot.run(TOKEN)
except discord.errors.LoginFailure as e:
    print("Login unsuccessful.")
    print(e)