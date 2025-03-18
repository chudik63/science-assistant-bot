# Environment Variables  
```env
POSTGRES_PASSWORD=password 
POSTGRES_USER=user 
POSTGRES_DB=database 
POSTGRES_PORT=5432
POSTGRES_HOST=localhost

TELEGRAM_TOKEN=
```
# Installation
```
pip install -r requirements.txt
```

# Commands for developers
Start postgres. Migrations will be applied automatically:
```
make postgres-up
```
Stop postgres:
```
make postgres-down
```
Clear postgres data:
```
make postgres-clear
```
Start the bot
```
make run
```