# Meeting AI

Локальное веб-приложение для обработки записей рабочих встреч:

**аудио → расшифровка → определение спикеров → анализ Qwen → DOCX-протокол**

Проект выполнен как тестовое задание. После первоначальной загрузки моделей основной AI-pipeline работает локально и не использует внешние AI API.

## Возможности

- загрузка аудио в форматах MP3, WAV и M4A;
- локальная русскоязычная расшифровка через WhisperX `large-v3`;
- alignment расшифровки;
- diarization через `pyannote/speaker-diarization-community-1`;
- автоматическое определение 2–4 участников или ручное указание точного количества: 2, 3 или 4;
- локальный анализ встречи моделью `qwen3.5:9b-q4_K_M` через Ollama;
- выделение существенной информации, решений, поручений, ответственных и сроков;
- отдельное отображение нерешённых и неоднозначных вопросов;
- дополнительная семантическая проверка чисел, сроков и идентификаторов спикеров;
- генерация DOCX по шаблону протокола;
- отображение текущего этапа обработки в веб-интерфейсе;
- удаление временного аудиофайла после завершения обработки;
- работа без интернета после provisioning моделей.

## Архитектура

```text
Browser
   |
   v
FastAPI
   |
   v
Processing Job
   |
   v
MeetingPipeline
   |
   +--> WhisperX large-v3
   |       |
   |       +--> Alignment
   |       |
   |       +--> Pyannote diarization
   |
   +--> Qwen 3.5 9B via Ollama
   |
   +--> Semantic Guard
   |
   +--> DOCX Generator
   |
   v
outputs/<job_id>.docx
```

FastAPI и Ollama запускаются отдельными Docker Compose сервисами. Модели сохраняются в Docker volumes и повторно не скачиваются при обычном перезапуске контейнеров.

## Стек

- Python 3.11
- FastAPI
- WhisperX 3.8.6
- Faster Whisper
- PyTorch 2.8 / CUDA 12.8
- Pyannote Audio
- Ollama
- Qwen 3.5 9B Q4_K_M
- Pydantic
- python-docx
- Docker / Docker Compose
- Vanilla HTML / CSS / JavaScript

## Требования

Текущая конфигурация рассчитана на запуск с NVIDIA GPU и CUDA.

Проверенная конфигурация разработки:

- NVIDIA RTX 3060 Laptop GPU, 6 GB VRAM;
- 16 GB RAM;
- Windows + Docker Desktop / WSL2.

Перед запуском необходимы:

- Docker Desktop с работающим Linux engine;
- Docker Compose;
- NVIDIA driver и доступ GPU из Docker;
- Hugging Face token для первоначального получения модели Pyannote;
- свободное место на диске для Docker images и AI-моделей.

Проверить доступ GPU из Docker можно командой(НЕ ОБЯЗАТЕЛЬНО):

```bash
docker run --rm --gpus all pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime nvidia-smi
```

## Быстрый запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/BAY4K/meetings-ai.git
cd meetings-ai
```

### 2. Создать `.env`

Скопируйте `.env.example` в `.env`.

Linux/macOS:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Укажите Hugging Face token:

```env
HF_TOKEN=hf_your_token_here
```

Настоящий `.env` не должен попадать в Git.

### 3. Собрать приложение

```bash
docker compose build app
```

### 4. Запустить Ollama

```bash
docker compose up -d ollama
```

Проверить состояние:

```bash
docker compose ps
```

### 5. Загрузить Qwen

```bash
docker compose exec ollama ollama pull qwen3.5:9b-q4_K_M
```

Проверить установленную модель:

```bash
docker compose exec ollama ollama list
```

### 6. Запустить весь стек

```bash
docker compose up
```

После запуска приложение доступно по адресу:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Первоначальная прогонка моделей

Первый запуск выполняется с доступом в интернет.

Во время первого полноценного прогона приложение может загрузить и сохранить в Docker cache необходимые модели WhisperX, alignment и Pyannote.

NLTK-ресурсы `punkt` и `punkt_tab`, необходимые WhisperX alignment, загружаются во время сборки Docker image.

Qwen загружается отдельно через:

```bash
docker compose exec ollama ollama pull qwen3.5:9b-q4_K_M
```

Для Pyannote используется переменная:

```env
HF_TOKEN=...
```

После успешного первого E2E-прогона необходимые AI-модели остаются локально в Docker volumes/cache.

> Если в `compose.yaml` включены `HF_HUB_OFFLINE=1` и `TRANSFORMERS_OFFLINE=1`, для первоначального provisioning их нужно временно отключить или выставить в `0`. После загрузки моделей их можно снова включить.

## Offline-режим

После provisioning приложение может работать без подключения к интернету.

Для принудительного Hugging Face / Transformers offline-режима используются:

```yaml
HF_HUB_OFFLINE: "1"
TRANSFORMERS_OFFLINE: "1"
```

После их включения:

```bash
docker compose down
docker compose up
```

Не используйте `docker compose down -v`, если необходимо сохранить скачанные модели: ключ `-v` удаляет Docker volumes.

Offline E2E был проверен для полной работы:

```text
audio
  -> WhisperX
  -> alignment
  -> diarization
  -> Qwen/Ollama
  -> semantic validation
  -> DOCX
```

## Использование

1. Откройте `http://127.0.0.1:8000`.
2. Выберите MP3, WAV или M4A.
3. При необходимости укажите точное количество участников: 2, 3 или 4. Если оно неизвестно, оставьте автоматический режим.
4. Нажмите **«Обработать запись»**.
5. Дождитесь завершения pipeline.
6. Просмотрите протокол и расшифровку.
7. Скачайте готовый DOCX.

Во время выполнения интерфейс показывает текущий этап, например:

```text
Распознавание речи...
Выравнивание текста...
Определение участников...
Анализ встречи...
Проверка результата...
Создание DOCX...
```

## Результат анализа

Qwen формирует структурированные данные для блоков протокола вида:

```text
Заслушали:

[Докладчик / Спикер]

[Краткая существенная информация по обсуждаемому вопросу.]

Решение:
– [решение / поручение; ответственный и срок — только если названы в записи].
```

Системный prompt запрещает самостоятельно придумывать отсутствующие имена, факты, решения, поручения, суммы, даты, сроки, версии и количества.

Неоднозначные фрагменты и вопросы без окончательного решения выделяются отдельно.

## Файлы

Временные загруженные аудиофайлы сохраняются в:

```text
uploads/
```

После завершения работы, в том числе при ошибке, временный аудиофайл удаляется.

Готовые документы сохраняются в:

```text
outputs/
```

При Docker-запуске эта директория подключена к контейнеру через bind mount, поэтому DOCX остаётся доступен на host-системе.

## Основные API endpoints

Создание background job:

```http
POST /process/jobs
```

Получение текущего состояния:

```http
GET /process/jobs/{job_id}
```

Скачивание готового DOCX:

```http
GET /download/{file_id}
```

Состояния обработки:

```text
queued
running
completed
failed
```

## Структура проекта

```text
app/
├── api/                  # FastAPI routes
├── asr/                  # WhisperX и diarization
├── core/                 # конфигурация и lifespan
├── docx_generator/       # генерация протокола
├── llm/                  # локальный Qwen / Ollama
├── prompts/              # system prompt
├── schemas/              # Pydantic schemas
├── services/             # pipeline, jobs, semantic guard
├── static/               # web UI
└── templates/            # DOCX template

Dockerfile
compose.yaml
requirements.txt
.env.example
README.md
```

## Настройки моделей

Основная конфигурация находится в:

```text
app/core/settings.py
```

Текущий профиль:

```text
ASR: Whisper large-v3
Language: ru
Device: CUDA
Compute type: float16
Diarization: pyannote/speaker-diarization-community-1
Qwen: qwen3.5:9b-q4_K_M
Context: 8192
```

Адрес Ollama задаётся переменной окружения:

```env
OLLAMA_BASE_URL=http://ollama:11434
```
В будущем хотелось бы добавить возможность менять настройки прямо из веб-интерфеса

## Ограничения

- Pipeline ориентирован на русскоязычные рабочие встречи.
- Качество итогового протокола зависит от качества исходного аудио и ASR.
- Если ASR ошибочно распознал плохо слышимое число как другое правдоподобное число, LLM не может надёжно восстановить исходное значение.
- Автоматический режим diarization настроен на встречи с 2–4 участниками. Можно сделать больше, но для этого требуется больше ресурсов.
- Текущая конфигурация ориентирована на один тяжёлый GPU job одновременно; отдельная серверная очередь для конкурентных GPU-задач не реализована.
- Первый прогон требует подключения к интернету. После загрузки моделей AI-pipeline может работать без доступа в интернет.

## Остановка

Остановить контейнеры:

```bash
docker compose down
```

Для сохранения моделей не используйте:

```bash
docker compose down -v
```

так как `-v` удаляет volumes.

## Примечание

Проект предназначен для локальной обработки записей. Аудио не отправляется во внешние AI API: ASR выполняется локально, а анализ выполняется локальной моделью Qwen через Ollama.
Приложение не точное и не гарантирует сто процентного верного протокола.
