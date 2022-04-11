import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains 
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import datetime
import time
from fuzzywuzzy.fuzz import partial_ratio

cloud_mode = True

load_dotenv()
username = os.getenv('EMAIL')
password = os.getenv('PASSWORD')

PATH = "C:\Program Files (x86)\ChromeDriver\chromedriver.exe"

op = webdriver.ChromeOptions()
op.binary_location = os.environ.get('GOOGLE_CHROME_BIN')
op.add_argument('--headless')
op.add_argument('--no-sandbox')
op.add_argument('--disable-dev-shm-usage')

LOGIN_SITE = 'https://v-class.gunadarma.ac.id/login/index.php'
HOME_SITE = 'https://v-class.gunadarma.ac.id/?redirect=0'
SEMESTER_KEY = 'ATA'    # PTA: Ganjil, ATA: Genap
PTA = '2021 / 2022 '

QUIZ_IMG = 'https://v-class.gunadarma.ac.id/theme/image.php/boost/quiz/1585289926/icon'
ASSIGNMENT_IMG = 'https://v-class.gunadarma.ac.id/theme/image.php/boost/assign/1585289926/icon'
FORUM_IMG = 'https://v-class.gunadarma.ac.id/theme/image.php/boost/forum/1585289926/icon'

class Task():
	QUIZ = 'quiz'
	ASSIGNMENT = 'assignment'
	FORUM = 'forum'

def login(driver):
	driver.get(LOGIN_SITE)
	try:
		username_bar = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'username')))
		password_bar = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'password')))
	except TimeoutException:
		try:
			driver.find_element_by_link_text('Log out').click()
			driver.get(LOGIN_SITE)
			username_bar = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'username')))
			password_bar = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'password')))
		except NoSuchElementException:
			raise NoSuchElementException('We were in ',driver.title)

	login = ActionChains(driver)
	login.move_to_element(username_bar).click().send_keys(username)
	login.move_to_element(password_bar).click().send_keys(password)
	login.send_keys(Keys.RETURN)
	login.perform()

def search_user_class(class_name, driver):
	try:
		search_bar = WebDriverWait(driver, 2).until(
			EC.presence_of_element_located((By.ID, 'shortsearchbox'))
		)
	except TimeoutException:
		login(driver)
		driver.get(HOME_SITE)

		# try to close annoying left drawer
		try:
			left_drawer = WebDriverWait(driver, 2).until(
				EC.element_to_be_clickable((By.CLASS_NAME, 'media-body '))
			)
			left_span = driver.find_element_by_tag_name('button')
			left_span.click()
			print('closed left drawer')
		except TimeoutException:
			pass

		search_bar = WebDriverWait(driver, 5).until(
			EC.presence_of_element_located((By.ID, 'shortsearchbox'))
		)
	search_bar.clear()
	search_bar.send_keys(PTA+class_name)
	search_bar.send_keys(Keys.RETURN)

def get_lecturer_classes(data_dict, class_name, lecturer):
	# filter only the following class year
	class_year = class_name.strip()[0]
	vclass_list = [vclass for vclass in data_dict.keys() if vclass.strip()[0] == class_year and vclass.strip() != class_name.strip() and data_dict[vclass]!='scrapping']

	lecturer_classes = []
	for vclass in vclass_list:
		for course in data_dict[vclass].keys():
			if get_lecturer_name(course) == lecturer:
				lecturer_classes.append(' | '.join(course.split(' | ')[1:3]).strip())
	if len(lecturer_classes) == 0:
		return 'Tidak ditemukkan kelas yang dosennya sama :smiling_face_with_tear:\nBisa jadi kelas itu belum pernah ter-registrasi di UG Minibot'
	return '\n'.join(lecturer_classes)


def get_lecturer_name(course):
	return course.split('|')[-1].split('(')[0].strip()

def get_due_date(time, title):
	try:	
		str_time = ''.join(time.replace('.','').split(',')[1:]).strip()
		date_time = datetime.datetime.strptime(str_time, '%d %B %Y %I:%M %p')
		return '\nTutup Pada: {}:{} {} | {} {} {}'.format(date_time.strftime('%I'), date_time.strftime('%M'), date_time.strftime('%p'), date_time.strftime('%d'), date_time.strftime('%B'), date_time.strftime('%Y'))
	except ValueError:
		pass

	try:

		for line in time.split('\n'):
			if 'Due date' in line:
				time = line
				break
		str_time = time.replace('Due date ','').strip()
		date_time = datetime.datetime.strptime(str_time, '%A, %d %B %Y, %I:%M %p')
		return '\nTutup Pada: {}:{} {} | {} {} {}'.format(date_time.strftime('%I'), date_time.strftime('%M'), date_time.strftime('%p'), date_time.strftime('%d'), date_time.strftime('%B'), date_time.strftime('%Y'))
	except (ValueError, IndexError):
		pass

	# print('Deadline not found: {} \n{}', title.replace('\n',''), time)

	return ''

def is_expired(task):
	str_time = ''.join([line for line in task.split('\n') if 'Tutup Pada: ' in line])
	str_time = str_time.replace('Tutup Pada: ','').replace('```','').strip()
	try:
		date_time = datetime.datetime.strptime(str_time, '%I:%M %p | %d %B %Y')
		if datetime.datetime.now() < date_time:
			return False
	except ValueError:
		pass
	return True


def get_quiz_info(quiz, attribute):
	lines = quiz.text.split('\n')

	# get title
	title = '\n' + lines[0]


	result = ''

	# get due date
	for line in lines:
		if 'This quiz' in line and not 'open' in line:
			result += get_due_date(line, lines[0])
			break

	# get time limit
	for line in lines:
		if 'Time limit:' in line:
			result += '\n' +  'Batas Waktu: '+ line.split(':')[-1]
			break

	# get max attempts
	for line in lines:
		if 'Attempts allowed:' in line:
			result += '\n' + 'Batas Percobaan: '+ line.split(':')[-1] + ' kali'
			break

	# get grading method
	for line in lines:
		if 'Grading method:' in line:
			result += '\n' +  'Penilaian: '+ line.split(':')[-1]
			break

	if len(result) == 0:
		result = title + 'tidak ada info tercantum'
	else:
		result = title + result

	return Task.QUIZ + ' ' + attribute['href'] + ' ' + attribute['section'] + result

def get_assignment_info(assignment, attribute):
	# get title
	title = '\n' + assignment.text.split('\n')[0]

	# get due dates
	str_time = assignment.find_element_by_class_name('generaltable').text
	due_date = get_due_date(str_time, title)

	if len(due_date) == 0:
		result = title + '\ntidak ada info tercantum'
	else:
		result = title + due_date
	return Task.ASSIGNMENT + ' ' + attribute['href'] + ' ' + attribute['section'] + result

def get_forum_info(forum, attribute):
	# get title
	title = '\n' + forum.text.split('\n')[0]

	# get discussion topic
	try:
		desc = '\n' + forum.find_element_by_id('intro').text
	except NoSuchElementException:
		desc = '\nForum'

	result = title + desc
	return Task.FORUM + ' ' + attribute['href'] + ' ' + attribute['section'] + result

def scrape_tasks(driver):
	quiz_count = 0
	assignment_count = 0
	forum_count = 0
	other_count = 0

	tasks = []

	activities = WebDriverWait(driver, 1).until(
		EC.presence_of_element_located((By.CLASS_NAME, 'activityinstance'))
	)

	activities = driver.find_elements_by_class_name('activityinstance')
	buttons = []

	for activity in activities:
		if not 'Announcements' in activity.text: # exclude announcement forums
			try:
				buttons += [{
					'href':activity.find_element_by_tag_name('a').get_attribute('href'),
					'src':activity.find_element_by_tag_name('img').get_attribute('src'),
					'section':activity.find_element_by_xpath('./../../../../../../..').get_attribute('id'),
				}]
			except NoSuchElementException:
				pass

	for button in buttons:
		if QUIZ_IMG == button['src']:
			driver.get(button['href'])
			try:
				quiz = WebDriverWait(driver, 2).until(
					EC.presence_of_element_located((By.ID, 'region-main'))
				)
				tasks.append(get_quiz_info(quiz, button))
				quiz_count+=1
			except:
				print('cant get quiz on: ', format_course_name(driver.title) + '-' + button['section'])
			driver.back()
		elif ASSIGNMENT_IMG == button['src']:
			for i in range(10):
				try:
					driver.get(button['href'])
					assignment = WebDriverWait(driver, 2).until(
						EC.presence_of_element_located((By.ID, 'region-main-box'))
					)
					assignment_desc = get_assignment_info(assignment, button)
				except NoSuchElementException:
					time.sleep(2)
					continue
				finally:
					driver.back()
				break

			try:
				tasks.append(assignment_desc)
				assignment_count+=1
			except UnboundLocalError:
				print('cant get assignment on: ', format_course_name(driver.title) + '-' + button['section'])
		elif FORUM_IMG == button['src']:
			driver.get(button['href'])
			forum = WebDriverWait(driver, 2).until(
				EC.presence_of_element_located((By.ID, 'region-main'))
			)
			tasks.append(get_forum_info(forum, button))
			forum_count+=1
			driver.back()
		else:
			other_count+=1
	return {'task':tasks,'quiz_count':quiz_count, 'assignment_count':assignment_count, 'other_count':other_count}

def find_course_match(keyword, course_names):
	#get title + acronym
	objects = []
	for obj in course_names:
		objects.append(obj + ' ' + ''.join([w[0] for w in obj.split('|')[2].replace('&','').split()]))

	match = course_names[0]
	match_score = 0
	for i, obj in enumerate(objects):
		if partial_ratio(keyword.lower(), obj.lower()) > match_score:
			match_score = partial_ratio(keyword.lower(), obj.lower())
			match = course_names[i]
	return match

def find_match(keyword, object_list):

	match = object_list[0]
	match_score = 0
	for i, obj in enumerate(object_list):
		if partial_ratio(keyword.lower(), obj.lower()) > match_score:
			match_score = partial_ratio(keyword.lower(), obj.lower())
			match = object_list[i]
	return match

def format_task_result(task_dict, exclude_expired=False, exclude_empty_course=False):
	courses = list(task_dict.keys())

	result = ''
	for course in courses:
		active_sections = []

		quiz_count = 0
		assignment_count = 0
		forum_count = 0
		title = '\n**'+course.upper()+'**\n'
		tasks = ''

		# quiz and assignments
		for task in task_dict[course]['task']:
			task_type = task.split('\n')[0].split()[0]
			task_link = task.split('\n')[0].split()[1]
			task_sect = task.split('\n')[0].split()[2]
			task_desc = task.split('\n')[1:]
			task_desc[0] = '['+task_desc[0]+']'+'({})\n'.format(task_link)
			task_desc = task_desc[0] + '```'+'\n'.join(task_desc[1:])+'```'
			if (exclude_expired and is_expired(task_desc)) or task_type == Task.FORUM:
				continue
			active_sections.append(task_sect)
			if task_type == Task.QUIZ:
				quiz_count+=1
			elif task_type == Task.ASSIGNMENT:
				assignment_count+=1
			tasks += task_desc


		# forums -- forums dont have due date, so i used their section to decide if they are active. a section which has quiz/assignment active means all of its forums are active too.
		active_sections = set(active_sections)
		for task in task_dict[course]['task']:
			task_type = task.split('\n')[0].split()[0]
			task_link = task.split('\n')[0].split()[1]
			task_sect = task.split('\n')[0].split()[2]
			task_desc = task.split('\n')[1:]
			task_desc[0] = '['+task_desc[0]+']'+'({})\n'.format(task_link)
			task_desc = task_desc[0] + '```'+'\n'.join(task_desc[1:])+'```'
			if (exclude_expired and not task_sect in active_sections) or task_type != Task.FORUM:
				continue
			forum_count+=1
			tasks += task_desc

		if quiz_count + assignment_count != 0:
			result += title + tasks 
			result += '`{} Tugas & {} Forum`\n'.format(quiz_count + assignment_count, forum_count)
		else:
			if not exclude_empty_course:
				result += title + '\nTidak ada tugas :partying_face:\n'

	if result == '':
		return '\nTidak ada tugas :partying_face:\n'
	return result

def format_course_name(course_names):
	course_names_clean = []
	for name in course_names.split('\n'):
		name_clean = []
		for i, section in enumerate(name.split('|')):
			if i == 0:
				name_clean.append('/'.join([semester.replace('Course: ','').strip() for semester in section.split('/')]).strip())
			else: 
				name_clean.append(section.replace('/','').replace('\\','').strip())
		course_names_clean.append(' | '.join(name_clean))
	return '\n'.join(course_names_clean).replace('*','')

def get_reminder_dict(task_dict, channel_id):
	courses = list(task_dict.keys())

	result = []
	for course in courses:
		quiz_count = 0
		assignment_count = 0
		title = ':small_red_triangle_down:'+course.upper()
		tasks = ''
		for task in task_dict[course]['task']:
			task_type = task.split('\n')[0].split()[0]
			task_link = task.split('\n')[0].split()[1]
			task_sect = task.split('\n')[0].split()[2]
			task_desc = task.split('\n')[1:]
			task_desc[0] = '['+task_desc[0]+']'+'({})\n'.format(task_link)
			task_desc = task_desc[0] + '```'+'\n'.join(task_desc[1:])+'```'
			# filter expired task
			if is_expired(task_desc) or task_type == Task.FORUM:
				continue

			# get the date
			str_time = ''.join([line for line in task.split('\n') if 'Tutup Pada: ' in line])
			str_time = str_time.replace('Tutup Pada: ','').strip()

			result.append({'title':title, 'desc': task_desc, 'channel_id':channel_id, 'due':str_time, 'vclass':True})
	return result

def find_courses(task_dict):
	courses = list(task_dict.keys())

	result = '\n'.join(courses)
	return result

def find_lecturer(data_dict, class_name, lecturer_keyword):
	courses = list(data_dict[class_name].keys())
	lecturers = [get_lecturer_name(course) for course in courses]

	# find which lecturer match keyword
	match_lecturer = find_match(lecturer_keyword, lecturers)

	# find lecturer's classes
	lecturer_classes = get_lecturer_classes(data_dict, class_name, match_lecturer)


	result = '**' + match_lecturer + '**' + '\nKelas dengan dosen yang sama:\n' + lecturer_classes

	return result

def find_task(task_dict, course_keyword):
	course_names = list(task_dict.keys())

	# Get Matching to Keyword Course
	match_course = find_course_match(course_keyword, course_names)
	course_dict = {match_course:task_dict[match_course]}

	return format_task_result(course_dict)

def enroll_course(driver):
	enroll_button = driver.find_element_by_id('id_submitbutton')
	enroll_button.click()

def unenroll_course(driver):
	dropdown = driver.find_elements_by_class_name('dropdown')[-1]
	dropdown.click()
	unenroll = dropdown.find_element_by_class_name('dropdown-item')
	unenroll.click()
	driver.find_element_by_tag_name('form').click()

def find_all_task_data(class_name):
	if cloud_mode:
		driver = webdriver.Chrome(executable_path=os.environ.get('CHROMEDRIVER_PATH'), chrome_options=op)
	else:
		driver = webdriver.Chrome(PATH)
	driver.get(HOME_SITE)
	try:
		search_user_class(class_name, driver)
		courses = WebDriverWait(driver, 5).until(
			EC.presence_of_element_located((By.ID, 'region-main-box'))
		)
		# Get Clickable Course Page
		courses = driver.find_elements_by_partial_link_text(SEMESTER_KEY)
		links = []
		for course in courses:
			if not 'TEAM TEACHING' in course.text.upper():
				links += [course.get_attribute("href")]

		results = {}

		for link in links:	
			driver.get(link)
			course_name = format_course_name(driver.title)
			while course_name in results:  # handle lecturer who two or more identical vclass accidentaly
				course_name+=' (2)'
			try:
				results[course_name] = scrape_tasks(driver)
			except TimeoutException: # When Course is not enrolled yet
				try:
					enroll_course(driver)
					course_name = format_course_name(driver.title)
					while course_name in results:  # handle lecturer who two or more identical vclass accidentaly
						course_name+=' (2)'
					results[course_name] = scrape_tasks(driver)
				except (TimeoutException, NoSuchElementException):
					print('{} task undetected'.format(course_name))
					results[course_name] = {'task':[],'quiz_count':0, 'assignment_count':0, 'other_count':0}
			finally:
				driver.get(link)
				if not '3ia09' in course_name.lower() or 'pendidikan agama islam' in course_name.lower():
					unenroll_course(driver)
				driver.get(HOME_SITE)
		return results
	finally:
		driver.quit()
