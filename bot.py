def run():
    import os
    import re
    import random
    import discord
    import datetime
    import asyncio
    import time
    from threading import Timer, Thread
    from discord.ext import commands
    from dotenv import load_dotenv
    import numpy as np
    import baak
    import vclass
    import google_drive
    import json
    import pytz

    cloud_mode = True 

    easter_counter = 0
    EASTER_LIMIT = 5

    GREETINGS = ['Halo!','Hai!','Halo $user!','Hai $user!','Haloo!','Hi There!','Iyaa?','MAMA MIA LEZATOS','Sokin Mau Nanya Apa']
    EMOJIS = ['👋','🤩','🥳','🤟','😎','✌️','🤌','💩','😍','🥳','🤟','😎','✌️']
    VCLASS_SYMBOLS = [':blue_book:',':green_book:',':orange_book:',':closed_book:',':point_right:',':pencil2:',':mortar_board:',':purple_circle',':trident:']
    VCI_EASTER = ['buat apa gw nge scek, ngerjain aja kg -anon','Halah matlan -anon','Tidak ada tugas :partying_face: \n\n\n\n`Tapi boong`', 'Halo, perkenalkan nama saya siapa', 'Moga2 vclass ga down', 'too bad.. your free trial has expired', 'Kalo teman mu marah, diamkan bebarapa saat, goreng, lalu tiriskan \n-sumanto', 'males.']
    REMIND_VCI = ['Reminder tugas masih kosong nih.. Yuk ketik \n`{}vclass incoming` untuk cek tugas ʕ•́ᴥ•̀ʔっ', 'Jangan lupa cek vclass kamu! ketik \n`{}vclass incoming` untuk lihat deadline terdekat ⏱️', 'Kadang tugas kamu gak masuk calendar vclass loh! Yuk ketik \n`{}vclass incoming` untuk melihat tugas secara lengkap', 'Tau gak sih? Kalo vclass sedang down, kamu tetap bisa cek tugas dengan ketik `{}vclass incoming`', 'Bingung cara pake ugminibot? ketik `{}help` untuk lihat panduan ʕ•́ᴥ•̀ʔっ']
     
    DEFAULT_DATA = {
        'PREFIX':'#',
        'MAX_ROWS':5,
        'CHANNELS':[],
        'REMINDER':[],
        'REMIND_CHANNEL':'',
    }

    load_dotenv()
    if cloud_mode:
        TOKEN = os.getenv('DISCORD_TOKEN')
        GUILD = os.getenv('DISCORD_GUILD')
    else:
        TOKEN = os.getenv('DISCORD_TOKEN_LOCAL')
        GUILD = os.getenv('DISCORD_GUILD')

    BOT_DATA_PATH = 'bot-data.json'
    N_VCLASS_SCRAPE_PROCESSES = 1

    intents = discord.Intents.all()
    client = discord.Client(intents=intents)

# ---- BOT DATA ---- #
    def dump_bot_data(data):
        with open(BOT_DATA_PATH,'w') as f:
            json.dump(data, f, indent=2)

    def load_bot_data():
        with open(BOT_DATA_PATH,'r') as f:
            return json.load(f)

    def back_up_bot_data():
        google_drive.upload_file(BOT_DATA_PATH)
        
        interval = datetime.timedelta(hours=1).total_seconds()
        timer = Timer(interval, back_up_bot_data)
        timer.daemon = True
        timer.start()

# ---- TEXTS ---- #
    def create_help_text(message, data):
        prefix = data['guild'][str(message.guild.id)]['PREFIX']

        # get all the texts
        with open('help-text/main.txt','r') as txt:
            help_main = ''.join(txt.readlines()).replace('[p]', prefix)
        with open('help-text/vclass.txt','r') as txt:
            help_vclass = ''.join(txt.readlines()).replace('[p]', prefix)
        with open('help-text/baak.txt','r') as txt:
            help_baak = ''.join(txt.readlines()).replace('[p]', prefix)
        with open('help-text/remind.txt','r') as txt:
            help_remind = ''.join(txt.readlines()).replace('[p]', prefix)
        with open('help-text/set.txt','r') as txt:
            help_set = ''.join(txt.readlines()).replace('[p]', prefix)

        # create all embeds
        embed_main = discord.Embed(
            title = 'HELP',
            description = help_main,
            colour = discord.Colour.lighter_gray(),
        )
        embed_main.set_footer(text='Bot invite link: bit.ly/ug-minibot')

        embed_vclass = discord.Embed(
            title = 'HELP',
            description = help_vclass,
            colour = discord.Colour.lighter_gray(),
        )
        embed_vclass.set_footer(text='Bot invite link: bit.ly/ug-minibot')

        embed_baak = discord.Embed(
            title = 'HELP',
            description = help_baak,
            colour = discord.Colour.lighter_gray(),
        )
        embed_baak.set_footer(text='Bot invite link: bit.ly/ug-minibot')

        embed_remind = discord.Embed(
            title = 'HELP',
            description = help_remind,
            colour = discord.Colour.lighter_gray(),
        )
        embed_remind.set_footer(text='Bot invite link: bit.ly/ugminibot')

        embed_set = discord.Embed(
            title = 'HELP',
            description = help_set,
            colour = discord.Colour.lighter_gray(),
        )
        embed_set.set_footer(text='Bot invite link: bit.ly/ug-minibot')


        embeds = {'main':embed_main, 'vclass':embed_vclass, 'baak':embed_baak, 'remind':embed_remind, 'set':embed_set}
        return embeds

    def create_intro_text(guild):
        with open('help-text/intro.txt','r') as txt:
            txt = ''.join(txt.readlines())
            return txt.format(guild.name)

    def create_info_text(message, data):

        with open('help-text/info.txt','r') as txt:
            txt = ''.join(txt.readlines())
            return txt.format(message.guild.name)

    def create_greetings(message):
        reply_idx = int(np.abs(np.floor(np.random.normal()*3)))
        reply = GREETINGS[reply_idx]

        emoji_idx = int(np.abs(np.floor(np.random.normal()*3)))
        emoji = EMOJIS[emoji_idx]
        reply = reply.replace('$user', message.author.name)
        return reply, emoji

# ---- VCLASS SCRAPPING ---- #

    def update_vclass_data(force=False):
        print('Checking Vclass Update..')

        data = load_bot_data()
        last_updated = data['vclass']['TIME']
        today = datetime.datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%d %B')

        if last_updated != today or force:
            print('Scrapping..')
            class_names = [class_name for class_name in list(data['vclass'].keys()) if class_name!='TIME']
            print('{} classes, {} batch size'.format(len(class_names), N_VCLASS_SCRAPE_PROCESSES))
            for i in range(0, len(class_names), N_VCLASS_SCRAPE_PROCESSES):
                print('Batch {}: {}'.format(i/N_VCLASS_SCRAPE_PROCESSES + 1, class_names[i : i + N_VCLASS_SCRAPE_PROCESSES]))
                scrape_thread = []
                for class_name in class_names[i : i + N_VCLASS_SCRAPE_PROCESSES]:
                    scrape_thread.append(Thread(target=get_task_from_vclass, args=[class_name]))
                for thread in scrape_thread:
                    thread.start()
                for thread in scrape_thread:
                    thread.join()

            data = load_bot_data()
            data['vclass']['TIME'] = today
            dump_bot_data(data)
            if cloud_mode:
                back_up_bot_data()
            print('Scrapping completed!')
        else:
            print('All up to date!')

        if not force:
            today = datetime.datetime.now(pytz.timezone('Asia/Jakarta'))
            tomorrow_early = today.replace(day=today.day, hour=1, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
            next_update_time = (tomorrow_early-today).total_seconds()
            timer = Timer(next_update_time, update_vclass_data)
            timer.daemon = True
            timer.start()

    def add_new_vclass_data(message, data):
        msg = message.content[1:] # Remove prefix
        new_class = ''.join(msg.split()[2]).strip().lower()
        data['vclass'][new_class] = 'scrapping'
        dump_bot_data(data)

        new_vclass = vclass.find_all_task_data(new_class)
        data = load_bot_data()
        data['vclass'][new_class] = new_vclass
        dump_bot_data(data)

# ---- UNEXPECTED COMMAND HANDLING ---- #

    def create_invalid_command_text(message, data):
        return 'Command Invalid! Ketik `{}help` untuk melihat panduan^^'.format(data['guild'][str(message.guild.id)]['PREFIX'])

    def create_class_required_text(message, data):
        return 'Kelas kamu belum tercatat! Masukkan nama kelas kamu yuk.. contoh: `{}set class 3ia01`'.format(data['guild'][str(message.guild.id)]['PREFIX'])

    def create_on_scrapping_message(message, data):
        return 'Wih, kamu orang pertama dari kelasmu yang pake ugminibot nih. Data kelasmu baru akan siap dalam 5 menit. Setelah itu kamu boleh ketik `{}vclass incoming` ʕ•́ᴥ•̀ʔっ'.format(data['guild'][str(message.guild.id)]['PREFIX'])

# ---- BAAK SEARCH ---- #

    def create_baak_search(message, data):
        msg = message.content[1:] # Remove prefix
        keyword = ' '.join(msg.split()[1:])
        if keyword != '':
            max_row = data['guild'][str(message.guild.id)]['MAX_ROWS']
            hasil = baak.search(keyword, max_row)
            title = 'Hasil Pencarian BAAK untuk \"{}\":'.format(keyword)
            embed = discord.Embed(
                title = title,
                description = hasil,
                colour = discord.Colour.lighter_gray(),
            )
            return '', embed
        else:
            return create_invalid_command_text(message, data), None

    def create_baak_schedule_search(message, data):
        msg = message.content[1:] # Remove prefix
        keyword = ' '.join(msg.split()[2:])
        if keyword != '':
            title = 'Hasil Pencarian Jadwal BAAK untuk \"{}\": \n'.format(keyword)
            hasil = baak.get_schedule(keyword)
            embed = discord.Embed(
                title = title,
                description = hasil,
                colour =discord.Colour.lighter_gray(),
            )
            return '', embed
        else:
            return create_invalid_command_text(message, data), None

# ---- VCLASS SEARCH ---- #

    def get_task_from_vclass(class_name):
        vclass_data = vclass.find_all_task_data(class_name)

        data = load_bot_data()
        data['vclass'][class_name] = vclass_data
        dump_bot_data(data)

    def create_vclass_course_list_search(message, data):
        if check_class(message, data):
            class_name = data['user'][str(message.author.id)]['CLASS']
            class_data = data['vclass'][class_name]
            if class_data == 'scrapping':
                return create_on_scrapping_message(message, data), None
            title = 'DAFTAR VCLASS {}'.format(class_name.upper())
            hasil = vclass.find_courses(class_data).split('\n')
            if ''.join(hasil).strip() != '':
                emoji_idx = int(np.abs(np.floor(np.random.normal()*3)))
                emoji = VCLASS_SYMBOLS[emoji_idx]
                description = f'{emoji}  '+ f'\n{emoji}  '.join(hasil)
            else:
                description = 'Course Tidak Ditemukkan'
            embed = discord.Embed(
                title = title,  
                description = description,
                colour =discord.Colour.lighter_gray(),
             )
            return '', embed
        else:
            return create_class_required_text(message, data), None

    def shorten_vclass_result(result):
        while len(result) >= 2048:
            title = result.split('\n[')[0] + '\n'
            desc = '\n['.join(result.split('\n[')[1:])
            desc = '[' + '```['.join(desc.split('```[')[1:])
            result = title + desc
        return result

    def create_vclass_course_search(message, data):
        if check_class(message, data):
            msg = message.content[1:] # Remove prefix
            keyword = ' '.join(msg.split()[1:]).strip()
            command = msg.split()[:3][-1].strip().lower()

            if command == 'list':
                return create_vclass_course_list_search(message, data)

            if keyword != '':
                class_name = data['user'][str(message.author.id)]['CLASS']
                class_data = data['vclass'][class_name]
                if class_data == 'scrapping':
                    return create_on_scrapping_message(message, data), None
                result = vclass.find_task(class_data, command)
                result = shorten_vclass_result(result) # due to char limit
                embed = discord.Embed(
                    description = result,
                    colour =discord.Colour.lighter_gray(),
                 )
                return '', embed
            else:
                return create_invalid_command_text(message, data), None
        else:
            return create_class_required_text(message, data), None

    def create_vclass_incoming_search(message, data):
        if check_class(message, data):	
            msg = message.content[1:] # Remove prefix
            keyword = ' '.join(msg.split()[2:]).strip()
            if keyword == '':
                class_name = data['user'][str(message.author.id)]['CLASS']
                class_data = data['vclass'][class_name]
                if class_data == 'scrapping':
                    return create_on_scrapping_message(message, data), None
                result = vclass.format_task_result(class_data, exclude_expired=True, exclude_empty_course=True)[:1990] # limited text
                if 'Tidak ada tugas' in result:
                    return result, None
                result+= '\n*react pesan ini untuk menyalakan reminder* ✅'
                embed = discord.Embed(        
                    description = result,
                    colour =discord.Colour.lighter_gray(),
                 )
                return '*Invite link: https://www.bit.ly/ugminibot*', embed
            else:
                return create_invalid_command_text(message, data), None
        else:
            return create_class_required_text(message, data), None

    def create_vclass_lecturer_search(message, data):
        if check_class(message, data):	
            msg = message.content[1:] # Remove prefix
            keyword = ' '.join(msg.split()[2:]).strip()
            command = msg.split()[:3][-1].strip().lower() 

            if command == 'list':
                return create_vclass_course_list_search(message, data)

            if keyword != '':
                class_name = data['user'][str(message.author.id)]['CLASS']
                class_data = data['vclass'][class_name]
                if class_data == 'scrapping':
                    return create_on_scrapping_message(message, data)
                result = vclass.find_lecturer(data['vclass'], class_name, keyword)
                title = result.split('\n')[0]
                desc = result.split('\n')[1:]
                embed = discord.Embed(
                    title = title,  
                    description = '\n'.join(desc),
                    colour =discord.Colour.lighter_gray(),
                 )
                return '', embed
            else:
                return create_invalid_command_text(message, data), None
        else:
            return create_class_required_text(message, data), None

# ---- SETTINGS ---- #

    def change_prefix(message, data):
        msg = message.content[1:] # Remove prefix
        new_prefix = ''.join(msg.split()[2:]).strip()
        if len(new_prefix) == 1:
            if new_prefix == data['guild'][str(message.guild.id)]['PREFIX']:
                return 'Prefix baru masih sama seperti sebelumnya'
            old_prefix = data['guild'][str(message.guild.id)]['PREFIX']
            data['guild'][str(message.guild.id)]['PREFIX'] = new_prefix
            reply = 'prefix diganti dari {} menjadi {}'.format(old_prefix, new_prefix)

            dump_bot_data(data)

            return reply
        else:
            return create_invalid_command_text(message, data)

    def change_max_rows(message, data):
        msg = message.content[1:] # Remove prefix
        new_max = ''.join(msg.split()[2:])
        if len(new_max) == 1 and new_max != data['guild'][str(message.guild.id)]['MAX_ROWS']:
            old_max = data['guild'][str(message.guild.id)]['MAX_ROWS']
            data['guild'][str(message.guild.id)]['MAX_ROWS'] = new_max
            reply = 'Batas baris diganti dari {} menjadi {}'.format(old_max, new_max)

            dump_bot_data(data)

            return reply
        else:
            return create_invalid_command_text(message, data)

    def change_reply_channel(message, data):
        msg = message.content[1:] # Remove prefix
        command = msg.split()[:3][-1].strip().lower()

        PREFIX = data['guild'][str(message.guild.id)]['PREFIX']
        if command == 'reset':
            data['guild'][str(message.guild.id)]['CHANNELS'] = []
            dump_bot_data(data)
            return 'Daftar channel direset'

        if command == 'list':
            if len(data['guild'][str(message.guild.id)]['CHANNELS']) == 0:
                return 'Daftar channel belum teregistrasi! Ketik `{}set channel <nama-nama channel>` untuk menambahkan channel\n\ncontoh: `{}set channel <nama-nama channel> #general #tugas`'.format(PREFIX, PREFIX)
            else:
                return 'UG-minibot aktif di {}'.format(' '.join(['<#'+channel+'>' for channel in data['guild'][str(message.guild.id)]['CHANNELS']]))

        new_channels = re.findall('\D(\d{18})\D', ' '.join(msg.split()[2:]))
        if len(new_channels) > 0:
            data['guild'][str(message.guild.id)]['CHANNELS'] = new_channels
            dump_bot_data(data)
            return 'UG Minibot akan aktif di {}'.format(' '.join(['<#'+channel+'>' for channel in new_channels]))

        return create_invalid_command_text(message, data)

    def store_class_data(message, data):
        msg = message.content[1:] # Remove prefix
        new_class = ''.join(msg.split()[2]).strip().lower()
        try:
            if data['vclass'][new_class] == 'scrapping':
                raise KeyError
        except KeyError:
            print('Scrapping {}'.format(new_class))
            t = Thread(target=add_new_vclass_data, args=(message, data,))
            t.start()

    def set_class(message, data):
        PREFIX = data['guild'][str(message.guild.id)]['PREFIX']
        msg = message.content[1:] # Remove prefix
        new_class = ''.join(msg.split()[2:])
        reply=''
        if re.search('^[0-9][a-z|A-Z]{2}[0-9]{2}$',new_class):
            new_class = new_class.strip().lower()
            old_class = data['user'][str(message.author.id)]['CLASS']

            if new_class == old_class:
                return 'Kelas kamu masih sama seperti sebelumnya'


            class_exist = check_class(message, data)

            data['user'][str(message.author.id)]['CLASS'] = new_class
            if len(old_class)>1:
                if class_exist:
                    reply = 'Kelas kamu diganti dari {} menjadi {}'.format(old_class, new_class)
                else:
                    reply = 'Kelas kamu diganti dari {} menjadi {}\n\n'.format(old_class, new_class, create_on_scrapping_message(message, data))
            else:
                if class_exist:
                    reply = 'Kamu terdaftar di kelas {}, ketik `{}vclass incoming` untuk melihat terdekat'.format(new_class, PREFIX)
                else:
                    reply = 'Kamu terdaftar di kelas {}\n\n{}'.format(new_class, create_on_scrapping_message(message, data))

            store_class_data(message, data) # Handle unknown/unscrapped class
            dump_bot_data(data)

            return reply
        else:
            return create_invalid_command_text(message, data)

    def check_class(message, data):
        if data['user'][str(message.author.id)]['CLASS'] == '':
            return False
        else:
            return True

# ---- REMINDER ---- #

    async def send_reminder(remind_msg, guild_id, channel_id, wait_time, destroy=True,tags=''):
        await asyncio.sleep(max(wait_time.total_seconds(), 0))
        channel = client.get_channel(int(channel_id))
        guild = client.get_guild(int(guild_id))
        data = load_bot_data()

        if destroy:
            actual_msg = '\n'.join(remind_msg.split('\n')[1:]) # get pure message (removing time description)
            for sending_reminder in [task for task in data['guild'][guild_id]['REMINDER'] if task['title'] + '\n' + task['desc'] == actual_msg]:
                data['guild'][guild_id]['REMINDER'].remove(sending_reminder)
            dump_bot_data(data)

        title = remind_msg.split('\n')[0]
        desc = remind_msg.split('\n')[1:]
        embed = discord.Embed(
            title = '**REMINDER** | ' + title,
            description = '\n'.join(desc),
            colour =discord.Colour.lighter_gray(),
         ) 

        try:
            if 'class_member' in tags:
                class_name = '\n'.join(desc).split('|')[1].strip().lower()

                ids = [member.id for member in guild.members if str(member.id) in data['user'].keys()]
                tag_id = [client.get_user(int(user_id)).mention	 for user_id in ids if data['user'][str(user_id)]['CLASS'].lower()==class_name]
                tags = ' '.join(tag_id)
        except:
            print(int(guild_id))

        await channel.send(tags, embed=embed)

    def set_reminder(remind_msg, guild_id, channel_id, time, vclass=True):
        date_time = datetime.datetime.strptime(time, '%I:%M %p | %d %B %Y')
        date_time = date_time.replace(tzinfo=pytz.timezone('Asia/Jakarta'))
        now = datetime.datetime.now(pytz.timezone('Asia/Jakarta'))

        hour_left, remainder = (divmod((date_time - now).total_seconds(), 3600))
        if hour_left < 48:
            if vclass:
                # remind a day in advance
                day_time = date_time - datetime.timedelta(days=1)
                remind_time = (day_time - now)
                if remind_time.total_seconds() > 0:
                    remind_msg = '1 hari lagi\n'.format(int(hour_left))+remind_msg
                    client.loop.create_task(send_reminder(remind_msg, guild_id, channel_id, remind_time, destroy=False, tags='class_member'))
                    return

                # remind 2 hours in advance	
                now_time = date_time - datetime.timedelta(hours=2)
                remind_time = (now_time - now)
                remind_msg = 'sebentar lagi\n'.format(int(hour_left))+remind_msg
                client.loop.create_task(send_reminder(remind_msg, guild_id, channel_id, remind_time, destroy=True, tags='class_member'))
                return

    def startup_vclass_reminder():
        data = load_bot_data()
        for guild_id in data['guild'].keys():
            try:
                for task in data['guild'][guild_id]['REMINDER']:
                    remind_msg = task['title'] + '\n' + task['desc']
                    channel_id = task['channel_id']
                    time = task['due']
                    vclass_mode = task['vclass']

                    if len(data['guild'][guild_id]['REMIND_CHANNEL'])>0:
                        channel_id=data['guild'][guild_id]['REMIND_CHANNEL']
                    set_reminder(remind_msg, guild_id, channel_id, time, vclass_mode)
            except KeyError:
                pass

        today = datetime.datetime.now(pytz.timezone('Asia/Jakarta'))
        tomorrow_early = today.replace(day=today.day, hour=1, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        next_update_time = (tomorrow_early-today).total_seconds()
        timer = Timer(next_update_time, startup_vclass_reminder)
        timer.daemon = True
        timer.start()

    def add_vclass_reminder(message, data):
        class_name = data['user'][str(message.author.id)]['CLASS']
        class_data = data['vclass'][class_name]
        if class_data == 'scrapping':
            return create_on_scrapping_message(message, data)

        vclass_remind_dict = vclass.get_reminder_dict(class_data, str(message.channel.id))

        # filter vclass reminder which already exist
        reminder_dict = [reminder for reminder in vclass_remind_dict if not reminder in data['guild'][str(message.guild.id)]['REMINDER']]
        data['guild'][str(message.guild.id)]['REMINDER'] += reminder_dict
        dump_bot_data(data)

        for task in reminder_dict:
            remind_msg = task['title'] + '\n' + task['desc']
            guild_id = str(message.guild.id)
            channel_id = task['channel_id']
            time = task['due']
            vclass_mode = task['vclass']

            if len(data['guild'][str(message.guild.id)]['REMIND_CHANNEL'])>0:
                channel_id=data['guild'][str(message.guild.id)]['REMIND_CHANNEL']
            set_reminder(remind_msg, guild_id, channel_id, time, vclass_mode)

        return 'Reminder untuk {} tugas ditambahkan. Ketik `{}remind list` lihat daftar reminder'.format(len(vclass_remind_dict), data['guild'][str(message.guild.id)]['PREFIX'])

    def get_reminder_list(message, data):
        reminders = data['guild'][str(message.guild.id)]['REMINDER']

        # sort vclass reminder by due date
        reminder_due_dicts = {}
        for reminder in reminders:
            if reminder['vclass']:
                str_time = reminder['due']
                date_time = datetime.datetime.strptime(str_time, '%I:%M %p | %d %B %Y')
                reminder_due_dicts[date_time] = reminder

        # format reminder
        result = []
        for i, reminder_due in enumerate(sorted(reminder_due_dicts.items())):
            due, reminder = reminder_due
            class_name = reminder['title'].split('|')[1].strip().lower()
            result.append('{}. `{}` {}'.format(i+1, reminder['due'], reminder['title']))

        # create reply
        if len(result)==0:
            return 'Tidak ada reminder', None
        else:
            embed = discord.Embed(        
                title = 'Daftar Reminder:',
                description = '\n'.join(result),
                colour =discord.Colour.lighter_gray(),
             )
            return None, embed

    def reset_reminder(message, data):
        n_reminder = len(data['guild'][str(message.guild.id)]['REMINDER'])

        if n_reminder > 0:
            data['guild'][str(message.guild.id)]['REMINDER'] = []
            dump_bot_data(data)
            return '{} reminder dihapus'.format(n_reminder)
        else:
            return 'Tidak ada reminder'

    def remove_reminder(message, data):
        msg = message.content[1:] # Remove prefix

        PREFIX = data['guild'][str(message.guild.id)]['PREFIX']

        remove_idx = msg.replace('.',' ').split()[2:]
        if len(remove_idx) == 1:
            remove_idx = int(remove_idx[0]) - 1
            data['guild'][str(message.guild.id)]['REMINDER'].pop(remove_idx)
            dump_bot_data(data)
            return 'Reminder ke-{} dihapus'.format(remove_idx + 1)

        return create_invalid_command_text(message, data)

    def change_reminder_channel(message, data):
        msg = message.content[1:] # Remove prefix
        command = msg.split()[:3][-1].strip().lower()

        PREFIX = data['guild'][str(message.guild.id)]['PREFIX']
        if command == 'reset':
            data['guild'][str(message.guild.id)]['REMIND_CHANNEL'] = ''
            dump_bot_data(data)
            return 'Channel reminder direset'

        if command == 'list':
            if len(data['guild'][str(message.guild.id)]['REMIND_CHANNEL']) == 0:
                return 'Channel reminder belum ditentukan! Ketik `{}remind channel <nama channel>` untuk memilih channel reminder\n\ncontoh: `{}remind channel #general`'.format(PREFIX, PREFIX)
            else:
                return 'Reminder akan di kirim pada {}'.format('<#'+data['guild'][str(message.guild.id)]['REMIND_CHANNEL']+'>')

        new_channels = re.findall('\D(\d{18})\D', ' '.join(msg.split()[2:]))
        if len(new_channels) == 1:
            data['guild'][str(message.guild.id)]['REMIND_CHANNEL'] = new_channels[0]
            dump_bot_data(data)
            return 'Reminder akan di kirim pada {}'.format('<#'+data['guild'][str(message.guild.id)]['REMIND_CHANNEL']+'>')

        return create_invalid_command_text(message, data)


# ---- ADMIN ---- #

    async def remind_all_guilds_to_check_vclass():
        reminded_guilds = []
        for guild in client.guilds:
            if cloud_mode:
                google_drive.download_file(BOT_DATA_PATH)
            data = load_bot_data()

            # im really sorry for this horrible code, i was angry when doing this one
            try:
                if len(data['guild'][str(guild.id)]['REMINDER'])==0:
                    PREFIX = data['guild'][str(guild.id)]['PREFIX']

                    channel = ''
                    for text_channel in guild.text_channels:
                        for user_channel_id in data['guild'][str(guild.id)]['CHANNELS']:
                            if str(text_channel.id) == user_channel_id:
                                channel = text_channel
                                break
                        if not channel == '':
                            break
                        if not channel == '' and text_channel.name == 'general':
                            channel = text_channel
                    if channel == '':
                        channel = guild.text_channels[1]

                    idx = random.randint(0, len(REMIND_VCI)-1)
                    await channel.send(REMIND_VCI[idx].format(PREFIX))

                    reminded_guilds.append(guild.name)
            except Exception as e:
                print('unable to send to ', guild.name, ": ", e)


        return 'Reminded guilds:\n- {}'.format('\n- '.join(reminded_guilds))

    async def send_admin_message_to_all(admin_message):
        reminded_guilds = []
        for guild in client.guilds:
            if cloud_mode:
                google_drive.download_file(BOT_DATA_PATH)
            data = load_bot_data()

            # im really sorry for this horrible code, i was angry when copying this one
            try:
                if len(data['guild'][str(guild.id)]['REMINDER'])==0:

                    channel = ''
                    for text_channel in guild.text_channels:
                        for user_channel_id in data['guild'][str(guild.id)]['CHANNELS']:
                            if str(text_channel.id) == user_channel_id:
                                channel = text_channel
                                break
                        if not channel == '':
                            break
                        if not channel == '' and text_channel.name == 'general':
                            channel = text_channel
                    if channel == '':
                        channel = guild.text_channels[1]

                    await channel.send(admin_message)

                    reminded_guilds.append(guild.name)
            except Exception as e:
                print('unable to send to ', guild.name, ": ", e)


        return 'Reminded guilds:\n- {}'.format('\n- '.join(reminded_guilds))

    async def send_intro_message(guild):
        data = load_bot_data()
        data['guild'][str(guild.id)] = dict(DEFAULT_DATA)
        dump_bot_data(data)

        sending_channel = guild.text_channels[0]
        if guild.system_channel: 
            sending_channel = guild.system_channel
        await sending_channel.send(create_intro_text(guild), file=discord.File('imgs/guide1.png'))
        await sending_channel.send(file=discord.File('imgs/guide2.png'))
        await sending_channel.send(file=discord.File('imgs/guide3.png'))

    async def send_intro_message_to_all():
        reminded_guilds = []
        for guild in client.guilds:
            if cloud_mode:
                google_drive.download_file(BOT_DATA_PATH)
            # im really sorry for this horrible code, i was angry when doing this one
            try:
                await send_intro_message(guild)
                reminded_guilds.append(guild.name)
            except Exception as e:
                print('unable to send to ', guild.name, ": ", e)


# ---/                              \--- #
# ---  THIS IS WHERE THE BOT STARTS  --- #
# ---\                              /--- #
        
    @client.event
    async def on_ready():
        print('We have logged in as {0.user} in:'.format(client))

        for guild in client.guilds:
            if cloud_mode:
                google_drive.download_file(BOT_DATA_PATH)
            data = load_bot_data()

            try:
                print(guild.name, '({} reminders)'.format(len(data['guild'][str(guild.id)]['REMINDER'])))
            except KeyError:
                print(guild.name)
                continue
                
            # if len(data['guild'][str(guild.id)]['REMINDER'])==0:
            # 	PREFIX = data['guild'][str(guild.id)]['PREFIX']
            # 	await guild.text_channels[0].send('ʕ•́ᴥ•̀ʔっ Sepertinya reminder tugas masih kosong nih.. ketik `{}set class <nama kelas>` untuk mulai'.format(PREFIX))
            

        if cloud_mode:
            # Load Data From Google Drive
            google_drive.download_file(BOT_DATA_PATH)

            # Update Vclass Data
            data = load_bot_data()
            time.sleep(30)
            update_vclass_thread = Thread(target=update_vclass_data)
            update_vclass_thread.start()
            baak.start_up()

        # set all reminder
        startup_vclass_reminder()


    @client.event
    async def on_guild_join(guild):
        data = load_bot_data()
        data['guild'][str(guild.id)] = dict(DEFAULT_DATA)
        dump_bot_data(data)

        sending_channel = guild.text_channels[0]
        if guild.system_channel: 
            sending_channel = guild.system_channel
        await sending_channel.send(create_intro_text(guild), file=discord.File('imgs/guide1.png'))
        await sending_channel.send(file=discord.File('imgs/guide2.png'))
        await sending_channel.send(file=discord.File('imgs/guide3.png'))

    @client.event
    async def on_message(message):

        if message.author == client.user:
            return

        # GREETINGS =======================================================

        if '792985450486693918' in message.content:
            if random.randint(0,20) == 0:
                await message.channel.send('https://tenor.com/view/baby-yoda-baby-yoda-wave-baby-yoda-waving-hi-hello-gif-15975082')
            else:
                reply, emoji = create_greetings(message)
                await message.add_reaction(emoji)
                await message.channel.send(reply)
            return

        if 'ug' in message.content.split() and random.randint(0,20) == 0:
            reply, emoji = create_greetings(message)
            await message.add_reaction(emoji)
            await message.channel.send(reply)


        # COMMANDS ===================================================

        data = load_bot_data()

        # Check if server is registered
        try:	
            for key in DEFAULT_DATA.keys():
                data['guild'][str(message.guild.id)][key]
        except KeyError:

            data['guild'][str(message.guild.id)] = dict(DEFAULT_DATA)
            dump_bot_data(data)

            await message.channel.send(create_intro_text(message.guild), file=discord.File('imgs/guide1.png'))
            await message.channel.send(file=discord.File('imgs/guide2.png'))
            await message.channel.send(file=discord.File('imgs/guide3.png'))

            return

        if len(data['guild'][str(message.guild.id)]['CHANNELS']) != 0:
            if not str(message.channel.id) in ''.join(data['guild'][str(message.guild.id)]['CHANNELS']):
                return

        if not message.content.startswith(data['guild'][str(message.guild.id)]['PREFIX']):
            return

        msg = message.content[1:].lower() # Remove prefix
        if msg == '':
            await message.channel.send(create_invalid_command_text(message, data))
            return

        # Check if author is registered
        try:	
            data['user'][str(message.author.id)]
        except KeyError:
            data['user'][str(message.author.id)] = {'CLASS':''}
            dump_bot_data(data)

            reply, emoji = create_greetings(message)
            await message.add_reaction(emoji)
            await message.channel.send(reply)


        # Get Main Command
        if len(msg.split()) >= 1:
            main_command = msg.split()[0]
        else:
            main_command = None

        # Get Sub command
        if len(msg.split()) >= 2:
            sub_command = msg.split()[1]
        else:
            sub_command = None


        if main_command == 'help' or main_command == 'h':
            txt_help = create_help_text(message, data)

            bot_message = await message.channel.send(embed=txt_help['main'])
            await bot_message.add_reaction('🟠')
            await bot_message.add_reaction('🔵')
            await bot_message.add_reaction('🟢')
            await bot_message.add_reaction('⚪')

            def check(reaction, user):
                return reaction.message == bot_message and user != client.user

            reaction = None

            while True:
                if str(reaction) == '🟠':
                    await bot_message.edit(embed = txt_help['vclass'])
                elif str(reaction) == '🔵':
                    await bot_message.edit(embed = txt_help['baak'])
                elif str(reaction) == '🟢':
                    await bot_message.edit(embed = txt_help['remind'])
                elif str(reaction) == '⚪':
                    await bot_message.edit(embed = txt_help['set'])
                try:
                    reaction, user = await client.wait_for('reaction_add', timeout = 300.0, check = check)
                    try:
                        await bot_message.remove_reaction(reaction, user)
                    except discord.errors.Forbidden:
                        continue
                except asyncio.TimeoutError:
                    break

            await bot_message.clear_reactions()
            return

        if main_command == 'info':
            await message.channel.send(create_info_text(message, data))
            return

        if main_command == 'baak' and sub_command != None:
            if sub_command == 'jadwal':
                reply, embed = create_baak_schedule_search(message, data)
                await message.channel.send(reply, embed=embed)
                return

            reply, embed = create_baak_search(message, data)
            await message.channel.send(reply, embed=embed)
            return

        if main_command == 'vci':
            reply, embed = create_vclass_incoming_search(message, data)
            if embed:
                if easter_counter < EASTER_LIMIT and  random.randint(0, 10) == 0:
                    idx = random.randint(0, len(VCI_EASTER)-1)
                    bot_message = await message.channel.send(VCI_EASTER[idx])
                    await asyncio.sleep(6)
                    await bot_message.edit(content=reply, embed=embed)
                else:
                    bot_message = await message.channel.send(reply, embed=embed)
                await bot_message.add_reaction('⏰')

                ### looking for reaction ###
                def check(reaction, user):
                    return reaction.message == bot_message and user != client.user

                try:
                    reaction, user = await client.wait_for('reaction_add', timeout=300.0, check=check)
                except asyncio.TimeoutError:
                    await bot_message.clear_reactions()
                    pass
                else:
                    reply = add_vclass_reminder(message, data)
                    await message.channel.send(reply)
                ### looking for reaction ###
            else:
                await message.channel.send(reply)
            return

        if (main_command == 'vclass' or main_command == 'vc') and sub_command != None:
            if sub_command == 'dosen':
                reply, embed = create_vclass_lecturer_search(message, data)
                await message.channel.send(reply, embed=embed)
                return
            if sub_command == 'incoming':
                reply, embed = create_vclass_incoming_search(message, data)
                if embed:
                    if easter_counter < EASTER_LIMIT and  random.randint(0, 10) == 0:
                        idx = random.randint(0, len(VCI_EASTER)-1)
                        bot_message = await message.channel.send(VCI_EASTER[idx])
                        await asyncio.sleep(5)
                        await bot_message.edit(content=reply, embed=embed)
                    else:
                        bot_message = await message.channel.send(reply, embed=embed)
                    await bot_message.add_reaction('⏰')

                    ### looking for reaction ###
                    def check(reaction, user):
                        return reaction.message == bot_message and user != client.user

                    try:
                        reaction, user = await client.wait_for('reaction_add', timeout=300.0, check=check)
                    except asyncio.TimeoutError:
                        await bot_message.clear_reactions()
                        pass
                    else:
                        reply = add_vclass_reminder(message, data)
                        await message.channel.send(reply)
                    ### looking for reaction ###
                else:
                    await message.channel.send(reply)
                return

            reply, embed = create_vclass_course_search(message, data)
            await message.channel.send(reply, embed=embed)
            return

                    
        if main_command == 'set' and sub_command != None:
            if sub_command == 'prefix':
                await message.channel.send(change_prefix(message, data))
                return

            if sub_command == 'row':
                await message.channel.send(change_max_rows(message, data))
                return

            if sub_command == 'channel':
                await message.channel.send(change_reply_channel(message, data))
                return

            if sub_command == 'class':
                reply = set_class(message, data)
                await message.channel.send(reply)
                return

        if main_command == 'remind':
            if sub_command == 'list':
                reply, embed = get_reminder_list(message, data)
                await message.channel.send(reply, embed=embed)
                return

            if sub_command == 'remove':
                reply = remove_reminder(message, data)
                await message.channel.send(reply)
                return

            if sub_command == 'reset':
                reply = reset_reminder(message, data)
                await message.channel.send(reply)
                return

            if sub_command == 'channel':
                reply = change_reminder_channel(message, data)
                await message.channel.send(reply)
                return

        # ADMINS =======================================================
        if message.author.id == 281399663150628864:
            if main_command == 'admin-rescrape':
                update_vclass_data(True)
                await message.channel.send('Rescrapping..')
                return

            if main_command == 'admin-remind-check':
                reply = await remind_all_guilds_to_check_vclass()
                await message.channel.send(reply)
                return

            if main_command == 'admin-send':
                admin_message = ' '.join(msg.split()[1:])
                reply = await send_admin_message_to_all(admin_message)
                await message.channel.send(reply)
                return

            if main_command == 'admin-intro':
                reply = await  send_intro_message_to_all()
                await message.channel.send(reply)
                return


        await message.channel.send(create_invalid_command_text(message, data))
        return

    client.run(TOKEN)
