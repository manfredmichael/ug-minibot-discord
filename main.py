from utils import bot_is_running
import bot


if __name__ == '__main__':
    if bot_is_running():
        print('Bot is running..')
        bot.run()
    else:
        print('Bot is not running today..')
