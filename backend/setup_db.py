import os
import pymysql

# Ajuste conforme seu settings
DB_NAME = 'dsr_db'
DB_USER = 'root'
DB_PASS = 'root'
DB_HOST = '127.0.0.1'
DB_PORT = 3306

conn = pymysql.connect(
    host=DB_HOST, user=DB_USER, password=DB_PASS, port=DB_PORT
)
with conn.cursor() as cursor:
  cursor.execute(
      f'CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4'
      ' COLLATE utf8mb4_unicode_ci;'
  )
conn.close()

print(f'Banco {DB_NAME} verificado/criado.')
os.system('python manage.py makemigrations')
os.system('python manage.py migrate')