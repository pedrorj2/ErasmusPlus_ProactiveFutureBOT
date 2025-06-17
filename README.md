# <ins>ProactiveFuture Erasmus+ Projects Bot — Telegram Assistant</ins>

> [!NOTE]
> - 🤖 This repository contains the code and setup instructions for the **ProactiveFuture Erasmus+ Telegram Bot**, an initiative to **centralize and simplify access to Erasmus+ opportunities** through a friendly and intelligent Telegram assistant.
> 
> - 🎯 **Objective**: Help to easily find Erasmus+ projects by filtering by date, country, and even **asking in natural language**. Whether you're looking for a mobility in Italy next month or want to explore options in renewable energy, this bot makes it quick and intuitive.
>   
> This guide is written for those with **no prior knowledge of Python**, so you can deploy your own version of the bot with ease.

---

## <ins>Documentation</ins>

- [Telethon Documentation](https://docs.telethon.dev/en/stable/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [ProactiveFuture Website](https://www.proactivefuture.eu/)

---

### <ins>Requirements</ins>

Is needed to have `Python` and the `Telethon` module installed.

We can check if Python is installed and which version by running the following in the terminal/PowerShell:

```bash
python --version
```

If installed, it will return the version (it is recommended to use the same or a newer version):

 `Python 3.12.2`

 <br>

> [!CAUTION]
> If not installed, go to https://www.python.org/downloads. This already include `pip` since `Python 3.4`.

We also need to install `Telethon` module, we install that with `pip` by entering in the terminal/PowerShell:
```bash
pip install telethon
```

We can check the instalation then by doing in the terminal/PowerShell:
```bash
pip list
```

This will return somethin like this in the terminal/PowerShell:
```bash
Package  Version
-------- -------
pip      24.0
pyaes    1.6.1
pyasn1   0.5.1
rsa      4.9
Telethon 1.34.0
```

With this, we finishined using the terminal/PowerShell for now.

<br>

### <ins>Clone the repository</ins>

> [!NOTE]
> This could be done by different programs as Visual Code, Visual Studio, Spyder, etc

We will use `Visual Code` but others are also compatible with it.

Once opened, press `Ctrl + Shift + P`.

In the search bar of Visual Code, a ">" will appear. With this, search for the action `Git: Clone`.

It will ask for the repository name (or URL), enter it:

```bash
https://github.com/pedrorj2/ErasmusPlus_ProactiveFutureBOT
```

It will open the explorer to choose a local path to clone the repository.

After doing this, a tab will appear asking to open the repository; accept it.

<br>

### <ins>Deploy the bot</ins>

Once the repository is cloned and opened with Visual Code, we need to fill in the identification data of our bot, which can be seen in the first commented lines. We need to fill them in and uncomment these lines.

```bash
# Configuración de tu API de Telegram
api_id = ' '
api_hash = ' '
bot_token = ' '
openai_api_key = ' '
```

> [!WARNING]
> You would see a import call like this in my code instead:
> 
> ```bash
> from config import api_id, api_hash, bot_token, openai_api_key
> ```
> This makes possible to get this data from `config.py`, file which is not uploaded to the repository, as indicated on the `.gitignore` file.

`openai_api_key` contains the openai api key for the natural language use. Don't worry about expenses as we use `text-embedding-3-small`, it's cheap.

`api_id` y `api_hash` are obtained by creating a "Telegram Application" through https://my.telegram.org/apps.

`bot_token` is obtained directly from the Telegram app via the [@BotFather](https://t.me/BotFather) bot.
o do this, we need to create a bot, choose its name, and we will get this `bot_token` to access the Telegram HTTP API.

With this, we can run our code, and our computer will host the bot's back-end. As long as it is running, our bot will respond to actions. However, if we close Visual Code, the bot will stop working until we restart it.




