Sun_Kursach
StudySwap

Веб-платформа обмена учебными материалами между студентами: загрузка, модерация, каталог с фильтрами, скачивание, оценки, комментарии и жалобы.

Автор: Сун Роман Сергеевич (GitHub: [@rmrzzsq](https://github.com/rmrzzsq))
Группа: ИУК5-53Б

## Стек

- Python 3.12, Django 5.2
- PostgreSQL
- Bootstrap 5.3

## Запуск (Windows, PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# переменные окружения: DJANGO_SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
python manage.py migrate
python manage.py runserver
