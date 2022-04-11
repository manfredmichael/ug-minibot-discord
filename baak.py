from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import os

cloud_mode = True

PATH = "C:\Program Files (x86)\ChromeDriver\chromedriver.exe"

op = webdriver.ChromeOptions()
op.binary_location = os.environ.get('GOOGLE_CHROME_BIN')
op.add_argument('--headless')
op.add_argument('--no-sandbox')
op.add_argument('--disable-dev-shm-usage')


if cloud_mode:
	driver = webdriver.Chrome(executable_path=os.environ.get('CHROMEDRIVER_PATH'), chrome_options=op)
else:
	driver = webdriver.Chrome(PATH)

def start_up():
	driver.get('https://baak.gunadarma.ac.id/')

# Expand Search Bar Kelas Baru

def format_table(table, max_row=100):
	rows = table.split('\n')[1:] # Remove Column Names
	rows = [' '.join(row.split(' ')[1:]) for row in rows][:int(max_row)]
	return '\n'.join(rows)

def find_name(student_name, max_row):
	# Click Name Radio
	radio_nama = driver.find_elements_by_name('tipeKelasBaru')[0]
	radio_nama.click()

	# Insert Keyword Into Search Bar
	search_bar = driver.find_elements_by_class_name('form-control')[-1]
	search_bar.clear()
	search_bar.send_keys(student_name)
	search_bar.send_keys(Keys.RETURN)

	# Scrape data
	try:
		element = WebDriverWait(driver, 2).until(
			EC.presence_of_element_located((By.TAG_NAME, 'table'))
		)
		student_table = driver.find_elements_by_tag_name('table')[-1]
		if re.search('[0-9]{2}.[0-9]{2}-[0-9]{2}.[0-9]{2} WIB', student_table.text):
			start_up()
			return search(student_npm, max_row)
		return(format_table(student_table.text, max_row))
	except:
		return('Data tidak ditemukkan')

def find_npm(student_npm, max_row):
	# Click NPM Radio
	radio_npm = driver.find_elements_by_name('tipeKelasBaru')[1]
	radio_npm.click()

	# Insert Keyword Into Search Bar
	search_bar = driver.find_elements_by_class_name('form-control')[-1]
	search_bar.clear()
	search_bar.send_keys(student_npm)
	search_bar.send_keys(Keys.RETURN)

	# Scrape data
	try:

		element = WebDriverWait(driver, 2).until(
			EC.presence_of_element_located((By.TAG_NAME, 'table'))
		)
		student_table = driver.find_elements_by_tag_name('table')[-1]
		if re.search('[0-9]{2}.[0-9]{2}-[0-9]{2}.[0-9]{2} WIB', student_table.text):
			start_up()
			return search(student_npm, max_row)
		return(format_table(student_table.text, max_row))
	except:
		return('Data tidak ditemukkan')

def find_class(class_name, max_row):
	radio_kelas = driver.find_elements_by_name('tipeKelasBaru')[2]
	radio_kelas.click()
	
	# Insert Keyword Into Search Bar
	search_bar = driver.find_elements_by_class_name('form-control')[-1]
	search_bar.clear()
	search_bar.send_keys(class_name)
	search_bar.send_keys(Keys.RETURN)

	# Scrape data
	try:
		element = WebDriverWait(driver, 2).until(
			EC.presence_of_element_located((By.TAG_NAME, 'table'))
		)
		student_table = driver.find_elements_by_tag_name('table')[-1]
		if re.search('[0-9]{2}.[0-9]{2}-[0-9]{2}.[0-9]{2} WIB', student_table.text):
			start_up()
			return search(student_npm, max_row)
		return(format_table(student_table.text, max_row))
	except:
		return('Data tidak ditemukkan')

# =======================================================================================

def search(keyword, max_row):
	try:
		element = WebDriverWait(driver, 2).until(
			EC.element_to_be_clickable((By.NAME, 'tipeKelasBaru'))
		)
	except:
		arrow = driver.find_elements_by_class_name('resp-arrow')[1]
		arrow.click()

	try:
		# Input Keyword
		keyword = keyword.strip()

		# Avoid chat popup
		driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

		# Find Keyword
		if re.search('[0-9][a-z|A-Z]{2}[0-9]{2}', keyword):
			return find_class(keyword, max_row)
		elif re.search('[0-9]{8}', keyword):
			return find_npm(keyword, max_row)
		else:
			return find_name(keyword, max_row)
	finally:
		driver.back()

def get_schedule(class_name):
	# Insert Keyword Into Search Bar
	search_bar = driver.find_elements_by_class_name('form-control')[0]
	search_bar.send_keys(class_name)
	search_bar.send_keys(Keys.RETURN)
	
	# Scrape data
	try:
		element = WebDriverWait(driver, 2).until(
			EC.presence_of_element_located((By.TAG_NAME, 'table'))
		)
		schedule_table = driver.find_elements_by_tag_name('table')[-1]
		if re.search('[0-9]{2}.[0-9]{2}-[0-9]{2}.[0-9]{2} WIB', schedule_table.text):
			start_up()
			return get_schedule(class_name)
		return(format_table(schedule_table.text))
	except:
		return('Data tidak ditemukkan')
	finally:
		start_up()