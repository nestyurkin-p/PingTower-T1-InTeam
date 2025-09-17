# Деплой
## 1) Установка зависимостей

- Установите `Python 3.11` (например, через `pyenv`)
- [Установите](https://python-poetry.org/docs/#installation) `Poetry`
- Установите `Docker` (или `Docker Desktop` - для `macOS`)


## 2) **Проброс сети Docker'а**
   
 ```bash
 docker network create broker_network
 ```

## 3) **Запуск проекта**

 В корневой директории

```bash
docker-compose up --build
 ```

# Если есть желание потыкать

В браузере откройте [страницу отслеживания очередей](http://localhost:15672/#/queues/%2F/pinger-to-web-queue)

- Логин: `root`

- Пароль: `toor`

Опубликуйте сообщение
```json
{
  "some_message": "the message we sent",
  "something": {"bob": "alice"}
}
```

в поле ввода:![img.png](sources/img.png)

Сообщение появится в логах
```
example_service  | 2025-09-17 09:17:52,542 [INFO] root: Got message: some_message='the message we sent' something={'bob': 'alice'}
```
