from openai import OpenAI

#sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16

class OpenAIWrapper:
    """
    Класс-обертка для работы с API OpenAI.
    Позволяет отправлять текстовые запросы и получать результат от модели.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        :param api_key: API ключ OpenAI
        :param model: модель по умолчанию
        """
        self.client = OpenAI(api_key=api_key, base_url="https://api.proxyapi.ru/openai/v1")
        self.model = model

    def send_message(self, message: str, model: str = None) -> str:
        """
        Отправляет строку в OpenAI и возвращает результат.
        
        :param message: текст запроса
        :param model: можно указать другую модель (если None — берется дефолтная)
        :return: строка-ответ
        """
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=[
                {"role": "user", "content": message}
            ]
        )

        return response.choices[0].message.content
