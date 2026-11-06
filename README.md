# textDark 3.2

<p align="center">
  <img src="https://raw.githubusercontent.com/mrsiktyyy/textDark/main/logo.png" width="120" alt="textDark logo">
</p>

<h1 align="center">textDark</h1>

<p align="center">
  **Текст. Код. Ничего лишнего.**
  <br>
  Лёгкий тёмный редактор текста и кода для Windows.
</p>

<p align="center">
  <a href="https://github.com/mrsiktyyy/textDark/releases/latest">
    <img src="https://img.shields.io/github/v/release/mrsiktyyy/textDark?style=for-the-badge&color=222222&label=VERSION" alt="Latest release">
  </a>
  <a href="https://github.com/mrsiktyyy/textDark/stargazers">
    <img src="https://img.shields.io/github/stars/mrsiktyyy/textDark?style=for-the-badge&color=222222&label=STARS" alt="GitHub stars">
  </a>
  <a href="https://github.com/mrsiktyyy/textDark">
    <img src="https://img.shields.io/github/license/mrsiktyyy/textDark?style=for-the-badge&color=222222" alt="License">
  </a>
  <img src="https://img.shields.io/badge/PLATFORM-Windows%20x64-222222?style=for-the-badge" alt="Windows x64">
  <img src="https://img.shields.io/badge/BUILT%20WITH-PySide6-222222?style=for-the-badge" alt="PySide6">
</p>

<p align="center">
  <a href="https://github.com/mrsiktyyy/textDark/releases/download/3.2/textDark.exe"><strong>↓ Скачать textDark 3.2</strong></a>
  &nbsp; · &nbsp;
  <a href="https://textdark-website.vercel.app/">Официальный сайт</a>
  &nbsp; · &nbsp;
  <a href="https://github.com/mrsiktyyy/textDark">Исходный код</a>
</p>

---

## ✦ О проекте

**textDark** — это простой и удобный текстовый редактор с полностью тёмным интерфейсом.

Он создан для тех, кому нужно быстро записать заметку, открыть текстовый файл или поработать с исходным кодом без лишних элементов интерфейса.

Начиная с версии 3.2, в приложении доступны два режима работы:

- **Программирование** — для редактирования исходного кода и обычного текста.
- **Блокнот** — для заметок, форматированных документов, изображений и таблиц.

Проект разработан **mrsiktyyy** при помощи ChatGPT и Gemini AI.

## ↓ Скачать

<p align="center">
  <a href="https://github.com/mrsiktyyy/textDark/releases/download/3.2/textDark.exe">
    <img src="https://img.shields.io/badge/DOWNLOAD-textDark%203.2-eeeeee?style=for-the-badge&logo=windows&logoColor=black&labelColor=222222" alt="Download textDark">
  </a>
</p>

| Информация | Значение |
|---|---|
| Последняя версия | 3.2 |
| Операционная система | Windows x64 |
| Формат | Один EXE-файл |
| Интерфейс | PySide6 |
| Тема | Тёмная |
| Установка | Не требует отдельного установщика |

**[Скачать EXE](https://github.com/mrsiktyyy/textDark/releases/download/3.2/textDark.exe)**

Другие версии и история обновлений доступны на странице [GitHub Releases](https://github.com/mrsiktyyy/textDark/releases).

## ✦ Возможности

### 1. Режим «Программирование»

Для работы с исходным кодом и обычными текстовыми файлами.

| Функция | Описание |
|---|---|
| Нумерация строк | Номера слева от текста |
| Подсветка синтаксиса | Базовая подсветка кода |
| Автозакрытие | Скобки и кавычки закрываются автоматически |
| Автоотступ | Помогает при написании кода |
| Вкладки | Несколько документов в одном окне |
| Масштабирование | Увеличение и уменьшение текста |

### 2. Режим «Блокнот»

Для заметок и документов с форматированием.

| Функция | Описание |
|---|---|
| Форматирование | Жирный, курсив, подчёркивание и другие стили |
| Изображения | Вставка изображений в документ |
| Таблицы | Создание таблиц с настройкой размеров |
| Объединение ячеек | Объединение и разделение ячеек |
| Границы | Настройка линий таблицы |
| Списки | Работа со списками |
| Ссылки | Добавление ссылок в документ |

### 3. Общие возможности

- Несколько открытых документов одновременно.
- Автоматическое восстановление несохранённого текста.
- Настройка шрифта и размера текста.
- Собственный фон приложения.
- Сохранение пользовательских настроек.
- Системный трей.
- Настраиваемые сочетания клавиш.
- Интеграция с Windows для открытия текстовых файлов.
- Короткое интро при первом запуске.

## ✦ Собственный формат `.txtd`

У textDark есть собственный формат документов — **`.txtd`**.

Он позволяет сохранять документы в зашифрованном виде с использованием AES-256-GCM.

В режиме «Блокнот» формат `.txtd` поддерживает сохранение форматирования, таблиц и изображений.

**Почему это удобно?**

- Не нужно вводить пароль при открытии.
- Файлами можно обмениваться между копиями textDark.
- Содержимое не отображается как обычный текст при открытии в стандартном редакторе.
- Поддерживается автоматическая расшифровка внутри приложения.

<details>
<summary><strong>Подробнее о безопасности</strong></summary>

Все копии textDark используют общий ключ, встроенный в приложение. Это позволяет открывать `.txtd` без пароля и обмениваться файлами между пользователями.

Однако технически подготовленный человек может извлечь ключ из EXE-файла. Поэтому формат не предназначен для хранения паролей, ключей доступа и особо конфиденциальной информации.

AES-256-GCM обеспечивает шифрование содержимого, но общий встроенный ключ не обеспечивает полноценную защиту от целенаправленного анализа приложения.

</details>

## ⌨️ Сочетания клавиш

Основные сочетания клавиш:

| Сочетание | Действие |
|---|---|
| `Ctrl + =` | Увеличить масштаб |
| `Ctrl + -` | Уменьшить масштаб |
| `Ctrl + 0` | Сбросить масштаб |
| `Ctrl + колесо мыши` | Изменить масштаб |
| `Win + .` | Открыть системную панель эмодзи Windows |

Другие сочетания можно посмотреть в меню справки приложения. В расширенных настройках также доступны пользовательские сочетания клавиш.

## ⚙️ Установка и запуск

### Вариант 1. Скачать готовый EXE

1. Открой страницу [скачивания textDark 3.2](https://github.com/mrsiktyyy/textDark/releases/download/3.2/textDark.exe).
2. Скачай `textDark.exe`.
3. Запусти файл.

Отдельно устанавливать Python и библиотеки не требуется.

### Вариант 2. Запустить из исходного кода

Для запуска из исходников потребуется Python 3.

Клонируй репозиторий:

```powershell
git clone https://github.com/mrsiktyyy/textDark.git
cd textDark
```

Создай виртуальное окружение:

```powershell
py -3 -m venv .venv
```

Активируй его:

```powershell
.\.venv\Scripts\Activate.ps1
```

Установи зависимости:

```powershell
python -m pip install -r requirements.txt
```

Запусти приложение:

```powershell
python main.py
```

## 🛠️ Сборка собственного EXE

В проекте предусмотрен PowerShell-скрипт, который автоматизирует сборку.

Положи `logo.png` рядом с `main.py`, затем открой PowerShell в папке проекта.

Выполни:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\build.ps1
```

Скрипт самостоятельно:

1. Создаст виртуальное окружение `.venv`.
2. Установит необходимые библиотеки.
3. Установит PyInstaller.
4. Подготовит иконку приложения.
5. Соберёт один EXE-файл.

Готовый файл появится здесь:

```text
dist/
└── textDark.exe
```

Для первой сборки требуется подключение к интернету.

## 📁 Структура проекта

```text
textDark/
│
├── main.py
├── requirements.txt
├── README.md
├── logo.png
│
├── scripts/
│   ├── build.ps1
│   └── make_icon.py
│
└── website/
    ├── index.html
    ├── styles.css
    ├── script.js
    ├── vercel.json
    └── assets/
```

## 🌐 Ссылки проекта

| Ресурс | Ссылка |
|---|---|
| Официальный сайт | https://textdark-website.vercel.app/ |
| GitHub | https://github.com/mrsiktyyy/textDark |
| Скачать 3.2 | [GitHub Releases](https://github.com/mrsiktyyy/textDark/releases/download/3.2/textDark.exe) |
| Все версии | [История релизов](https://github.com/mrsiktyyy/textDark/releases) |

## 🖤 Автор

**mrsiktyyy**

Разработка велась при помощи ChatGPT Free и Gemini AI.

Если тебе понравился textDark — поставь ⭐ репозиторию на GitHub. Это помогает проекту развиваться!

---

<p align="center">
  **textDark — меньше лишнего. Больше работы.**
  <br>
  <sub>© mrsiktyyy · textDark 3.2</sub>
</p>
