import os
from http import HTTPStatus

import logging
import requests
import sys
import time
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s',
    handlers=[logging.FileHandler('main.log', encoding='UTF-8'),
              logging.StreamHandler(sys.stdout)]
)

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = 786439790

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """ Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.error(f'Ошибка при запросе: {error}')
    if response.status_code != HTTPStatus.OK:
        logger.error('Сайт не доступен')
        raise ConnectionError(f'Ошибка {response.status_code}!')
    try:
        return response.json()
    except json.JSONDecodeError:
        logger.error('Сервер вернул невалидный json')
        send_message('Сервер вернул невалидный json')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        logger.error('Неверный формат данных')
        raise TypeError('Неверный формат данных')
    else:
        if response:
            if 'homeworks' in response:
                if not isinstance(response['homeworks'], list):
                    logger.error('Неверный формат данных')
                    raise TypeError('Неверный формат данных')
                return response.get('homeworks')
            else:
                logger.error('homeworks отсутствует')
                raise Exception('homeworks отсутствует')
        logging.error('Dict is empty')
        raise Exception('Dict is empty')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        logger.error('Работы с таким именем нет')
        raise KeyError('Работы с таким именем не обнаружено')
    if homework_status not in HOMEWORK_STATUSES.keys():
        logger.error('Неверный статус работы')
        raise KeyError('Неверный статус работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие всех токенов."""
    try:
        if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
            return True
    except KeyError:
        logger.critical('Отсутсвует один из элементов')


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1620741126
    check_tokens()
    if check_tokens() is True:
        while True:
            try:
                response = get_api_answer(current_timestamp)
                current_timestamp = response.get('current_date')
                homework = check_response(response)
                message = parse_status(homework[0])
                bot.send_message(TELEGRAM_CHAT_ID, message)
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                bot.send_message(TELEGRAM_CHAT_ID, message)
                time.sleep(RETRY_TIME)
    else:
        raise KeyError('Отсутсвует один из элементов')
        logger.critical('Отсутсвует один из элементов')


if __name__ == '__main__':
    main()
