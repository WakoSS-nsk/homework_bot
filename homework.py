import os
from http import HTTPStatus

import logging
import json
import requests
import sys
import time
from dotenv import load_dotenv
from telegram import Bot
from typing import Union

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = 786439790

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class SendMessageException(Exception):
    """Ошибка отправки сообщения в телеграмм."""
    pass


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logger.info('Начал отправку сообщения в Telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Ошибка отправки сообщения в телеграмм')
        raise SendMessageException('Ошибка отправки сообщения в телеграмм')


def get_api_answer(current_timestamp: int) -> Union[dict, None]:
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    params = {'from_date': timestamp}
    params_dict = {'url': ENDPOINT, 'headers': headers, 'params': params}
    try:
        response = requests.get(**params_dict)
        if response.status_code != HTTPStatus.OK:
            logger.error('Сайт не доступен')
            raise ConnectionError(f'Ошибка {response.status_code}!')
        try:
            return response.json()
        except json.JSONDecodeError:
            logger.error('Сервер вернул невалидный json')
            send_message('Сервер вернул невалидный json')
    except Exception as error:
        logger.error(f'Ошибка при запросе: {error}')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Данный формат данных не является словарём')
    if not response:
        logger.error('Dict is empty')
        raise Exception('Dict is empty')
    if 'homeworks' not in response:
        logger.error('homeworks отсутствует в ответе API')
        raise Exception('homeworks отсутствует в ответе API')
    if not isinstance(response['homeworks'], list):
        logger.error('Неверный формат данных')
        raise TypeError('Данный формат данных не является списком')
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('Работы с таким именем не обнаружено')
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error('Неверный статус работы')
        raise KeyError('Неверный статус работы')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие всех токенов."""
    try:
        return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    except KeyError:
        logger.critical('Отсутсвует один из элементов')


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - 2629743)
    check_tokens()
    if check_tokens() is not True:
        logger.critical('Отсутсвует один из токенов')
        sys.exit('Отсутсвует один из токенов')
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
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s,%(lineno)d, %(funcName)s,'
               '%(pathname)s, %(message)s',
        handlers=[logging.FileHandler('main.log', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)]
    )

    main()
