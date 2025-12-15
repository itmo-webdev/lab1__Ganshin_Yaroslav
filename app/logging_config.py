import structlog
import logging
import sys
import os

def setup_hybrid_logging():
    
    #Гибридная настройка: structlog + стандартный logging.Старое логгирование пока оставил, потом с ним зарберусь, если оно мне будет мешать...Записывает JSON логи в файл для Logstash
   
    
    #Настраиваем structlog для JSON вывода
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()  # JSON формат
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Создам директорию для логов если её нет ( у меня же она есть,туда шли логи воркера)
    logs_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Настраиваем стандартный logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Обработчик для записи в файл (JSON логи для Logstash)
    file_handler = logging.FileHandler(
        os.path.join(logs_dir, "app.json.log"),
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(file_handler)
    
    # Обработчик для консоли, в сл. отладки
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console_handler)
    
    # Возвращаю логгер для использования
    return structlog.get_logger()