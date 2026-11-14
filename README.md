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
python manage.py migrate
python manage.py runserver
