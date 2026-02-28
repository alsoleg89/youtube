# Деплой на Yandex Cloud VM

## Требования

- VM с 2+ vCPU, 4+ GB RAM, 20+ GB диска
- Ubuntu 22.04
- Открытые порты: 80 (HTTP), 443 (HTTPS, опционально)

## Установка Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker
```

## Клонирование и настройка

```bash
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> ~/youtube
cd ~/youtube

cp .env.example .env
nano .env
# Укажите OPENAI_API_KEY
```

## Запуск

```bash
cd ~/youtube/infra
docker compose -f docker-compose.prod.yml up -d --build
```

Приложение будет доступно на порту 80.

## Обновление

```bash
cd ~/youtube
git pull
cd infra
docker compose -f docker-compose.prod.yml up -d --build
```

## Мониторинг логов

```bash
cd ~/youtube/infra

# Все сервисы
docker compose -f docker-compose.prod.yml logs -f

# Отдельный сервис
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker
```

## Настройка домена (опционально)

1. Направьте A-запись домена на IP вашей VM.

2. Отредактируйте `infra/nginx.conf` — замените `server_name _` на ваш домен:

```nginx
server_name yourdomain.ru;
```

3. Установите Certbot для SSL:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.ru
```

4. Перезапустите сервисы:

```bash
cd ~/youtube/infra
docker compose -f docker-compose.prod.yml restart nginx
```
