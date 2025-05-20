<h1><ins>Autonomous Learning in Engineering through Gamified Activities Telegram Bot - ETSIAE UPM</ins></h1>


> [!NOTE]
> - 🗂️ This repository contains the progress and code of the [IE24.1401 Educational Innovation Project](https://innovacioneducativa.upm.es/proyectos-ie/informacion?anyo=2023-2024&id=1160)
> 
> - 🎯 Objective: Enable students to perform self-assessment activities in a more autonomous and approachable way, using gamification techniques. By incorporating elements of game design, such as rewards, challenges, and progress tracking, we aim to make self-assessment more engaging and enjoyable for students.
>   
> This `README.md` is made for those who are not even familiar with `Python`, so they can set up their bot by themselves.

### <ins>Documentation</ins>

 - [Telethon Documentation](https://docs.telethon.dev/en/stable/)
 - [Manual and Project Report](https://blogs.upm.es/apgamtel/wp-content/uploads/sites/1189/2024/11/PIE24_1401_Telegram_Aeroelasticidad_Manual_v01.pdf)

<br>

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
https://github.com/pedrorj2/Telegram-Gamification-UPM/
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
lista_profesores = []
```

> [!WARNING]
> You would see a import call like this in my code instead:
> 
> ```bash
> from config import api_id, api_hash, bot_token, lista_profesores
> ```
> This makes possible to get this data from `config.py`, file which is not uploaded to the repository, as indicated on the `.gitignore` file.

`lista_profesores` contains the user_ids of those who are granted access to restricted commands.

`api_id` y `api_hash` are obtained by creating a "Telegram Application" through https://my.telegram.org/apps.

`bot_token` is obtained directly from the Telegram app via the [@BotFather](https://t.me/BotFather) bot.
o do this, we need to create a bot, choose its name, and we will get this `bot_token` to access the Telegram HTTP API.

With this, we can run our code, and our computer will host the bot's back-end. As long as it is running, our bot will respond to actions. However, if we close Visual Code, the bot will stop working until we restart it.

### <ins>Admin Commands for Professors</ins>

```bash
/rankingprofesor  # Full user ranking with scores
/media            # Average score and max score info
/lista            # List of all registered users
/reset            # Confirm and delete all user response data
/id               # Display your Telegram sender ID
```




