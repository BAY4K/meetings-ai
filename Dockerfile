FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV HF_HOME=/root/.cache/huggingface
ENV TORCH_HOME=/root/.cache/torch
ENV XDG_CACHE_HOME=/root/.cache


WORKDIR /app

# FFmpeg нужен WhisperX / TorchCodec.
# libsndfile нужен части audio stack.
RUN apt-get update \
    && apt-get install -y \
        ffmpeg \
        libsndfile1 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cu128 \
    -r requirements.txt

# WhisperX alignment использует NLTK sentence tokenizer.
# Загружаем данные во время сборки image,
# чтобы runtime мог работать полностью offline.
ENV NLTK_DATA=/usr/local/share/nltk_data

RUN python -m nltk.downloader \
    -d /usr/local/share/nltk_data \
    punkt \
    punkt_tab

# Копируем проект после установки зависимостей
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]