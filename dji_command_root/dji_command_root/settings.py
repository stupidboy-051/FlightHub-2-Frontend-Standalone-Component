import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-$^vuuj6l7%#76l-=k!hx#bynkr4h84@8ck&f7bph$=$dq*6qf6"

# 现场调试建议先开着 True，跑通了再改 False
DEBUG = False

ALLOWED_HOSTS = ['*']

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    'dji_command_root',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'corsheaders',
    'telemetry_app',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    # CORS 放在 CommonMiddleware 之前
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ROOT_URLCONF = "dji_command_root.urls"
WSGI_APPLICATION = "dji_command_root.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# 默认使用 SQLite（本地开发）
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "timeout": 30,  # 增加超时时间到 30 秒，解决 database is locked 问题
        }
    }
}

# 如果环境变量中指定了 DB_ENGINE，则使用环境变量配置（如 MySQL）
if os.environ.get("DB_ENGINE"):
    DATABASES["default"] = {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.mysql"),
        "NAME": os.environ.get("DB_NAME", "dji_database"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "root"),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "3306"),
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator", },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator", },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator", },
]

# --- CORS 关键修改 ---
# 离线内网部署强烈建议开启这个，防止因为IP变化导致前端访问失败
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept", "authorization", "content-type", "user-agent",
    "x-csrftoken", "x-requested-with",
]

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,  # 默认每页显示10条记录
    'PAGE_SIZE_QUERY_PARAM': 'page_size',  # 允许客户端通过 page_size 参数控制每页数量
    'MAX_PAGE_SIZE': 1000,  # 限制最大每页数量，防止恶意请求
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter'
    ]
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- 静态文件关键配置 ---
STATIC_URL = "static/"
# 【新增】必须加这一行，否则 Docker build 在第7步会报错
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==== MinIO / 对象存储配置 ====
#MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://192.168.10.10:9000")
# 建议修改逻辑：优先读环境变量，读不到再用 localhost
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'http://127.0.0.1:9000')
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "StrongPassw0rd!")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "dji")
MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")

# ==== FastAPI 算法服务配置 ====
# 假设 FastAPI 部署在内网，例如 http://192.168.10.20:8000
FASTAPI_DETECT_URL = os.getenv(
    "FASTAPI_DETECT_URL",
    "http://localhost:8088/detect"
)

_ENABLE_AUTO_TRIGGER_DETECT_ENV = os.getenv("ENABLE_AUTO_TRIGGER_DETECT", "1").lower()
ENABLE_AUTO_TRIGGER_DETECT = _ENABLE_AUTO_TRIGGER_DETECT_ENV not in ("0", "false", "no", "off")
DETECT_DISTRIBUTION_BATCH_SIZE = int(os.getenv("DETECT_DISTRIBUTION_BATCH_SIZE", "50"))
DETECT_WORKER_IDLE_SLEEP = float(os.getenv("DETECT_WORKER_IDLE_SLEEP", "2"))
DETECT_HTTP_TIMEOUT = int(os.getenv("DETECT_HTTP_TIMEOUT", "180"))

_ENABLE_VIDEO_SCAN_ENV = os.getenv("ENABLE_VIDEO_SCAN", "0").lower()
ENABLE_VIDEO_SCAN = _ENABLE_VIDEO_SCAN_ENV in ("1", "true", "yes", "on")
UUID_MISS_MAX_RETRIES = int(os.getenv("UUID_MISS_MAX_RETRIES", "5"))
UUID_MISS_CACHE_TTL = int(os.getenv("UUID_MISS_CACHE_TTL", "86400"))

REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }


# settings.py (添加到文件末尾)

# =========================================================
# DJI 司空 API 配置 (硬编码版)
# =========================================================
DJI_API_BASE_URL = "http://192.168.10.20:30812"  # 你的司空平台内网地址
DJI_X_USER_TOKEN = "eyJhbGciOiJIUzUxMiIsImNyaXQiOlsidHlwIiwiYWxnIiwia2lkIl0sImtpZCI6IjU3YmQyNmEwLTYyMDktNGE5My1hNjg4LWY4NzUyYmU1ZDE5MSIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50IjoiYWRtaW4iLCJleHAiOjIwODkzNDYyNTcsIm5iZiI6MTc3MzcyNzA1Nywib3JnYW5pemF0aW9uX3V1aWQiOiJiNTlmMTc2Yi0wNjIyLTRkNWEtYWI2Yi04NmE4MTFmNGRiNTkiLCJwcm9qZWN0X3V1aWQiOiIiLCJzdWIiOiJmaDIiLCJ1c2VyX2lkIjoiMTc1ODUxMzQyNDYxOTI4MzY1OCJ9.wjqekGCLHXQGAyfTODH-VTH5nF3-qKHb6rwQN80xRK0mAt_qZ9_dThxgL9mhty9DJO2DHKF7f_h7xeuIRo1o5g" # 你的长Token
DJI_X_PROJECT_UUID = "7b21e3a8-33c8-46cb-b80e-b3ddc53ce644"  # 你的项目ID
DJI_X_Request_ID = "12345678"   # 任意唯一标识
DJI_X_LANGUAGE = "zh"

# =========================================================
# 机场/无人机 映射配置
# =========================================================

# 1. SN -> 流ID 映射 (用于 ZLM 流查找)
# 格式: "无人机SN": "ZLM流ID"
DOCK_STREAM_MAPPING = {
    "1581F8HGX255D00A0DK8": "drone01",   # 工业大学机场-无人机
    "8UUXN4900A052C": "dock01",          # 工业大学机场-监控
    "8UUXN4900A052D": "dock02",          # 示例: 其他机场
}

# 2. SN -> 中文名称 映射 (用于日志显示)
# 格式: "无人机SN": "显示名称"
DOCK_NAME_MAPPING = {
    "1581F8HGX255D00A0DK8": "工业大学无人机",
    "8UUXN4900A052C": "工业大学机场",
    "8UUXN4R00A06Q6": "马贝机场",
}
