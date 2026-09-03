"""Variables protegidas para el entorno pre."""

# Dominio interno: anewhope.aws
# Dominio público: getmylllm.com (solo nginx frontend)
# Servidores: frontend.anewhope.aws, backend.anewhope.aws, trainer.anewhope.aws

global_shared_key_raw = "TheKeyMustB3_s3cure@test"
sms_api_key = "d93dd9d323662d761b21dddb626b9f2d-cf9b562a-6590-419b-8318-8ab3de06611b"
sms_api_url = "https://pdy6d3.api.infobip.com"
sms_sender_id = "getmylllm"

# JWT (middleware)
jwt_access_secret_key = "TheKeyMustB3_s3cure@test"
jwt_session_secret_key = "TheKeyMustB3_s3cure@test"
jwt_algorithm = "HS256"
jwt_access_expiration_seconds = 900
jwt_session_expiration_seconds = 2700

# Backend routing (broker y core están en backend.anewhope.aws, trainer en trainer.anewhope.aws)
broker_backend_base_url = "http://backend.anewhope.aws:8008"
core_backend_base_url = "http://backend.anewhope.aws:8003"
trainer_backend_base_url = "http://trainer.anewhope.aws:8004"

# MariaDB (en servidor backend.anewhope.aws)
mariadb_host = "backend.anewhope.aws"
mariadb_port = 3306
mariadb_core_database = "myllm_core_db"
mariadb_ai_database = "myllm_projects_db"

mariadb_admin_user = "myllm_admin"
mariadb_admin_password = "Us3r@dminP@ss"
mariadb_writer_user = "myllm_writer"
mariadb_writer_password = "Us3r@wr1t3rP@ss"
mariadb_reader_user = "myllm_reader"
mariadb_reader_password = "Us3r@R3@derP@ss"
mariadb_root_user = "root"
mariadb_root_password = "RootP@ssw0rd2026"

mariadb_admin_dsn = (
    "mysql+pymysql://myllm_admin:Us3r%40dminP%40ss@backend.anewhope.aws:3306/myllm_core_db"
)
mariadb_writer_dsn = (
    "mysql+pymysql://myllm_writer:Us3r%40wr1t3rP%40ss@backend.anewhope.aws:3306/myllm_core_db"
)
mariadb_reader_dsn = (
    "mysql+pymysql://myllm_reader:Us3r%40R3%40derP%40ss@backend.anewhope.aws:3306/myllm_core_db"
)
mariadb_root_dsn = (
    "mysql+pymysql://root:RootP@ssw0rd2026@backend.anewhope.aws:3306/myllm_core_db"
)

# LAIM MariaDB (base de datos laim_core_db - credenciales independientes)
laim_database = "laim_core_db"
laim_admin_user = "laim_admin"
laim_admin_password = "NDt@dL_0Rxw6aiI_@XSE"
laim_writer_user = "laim_writer"
laim_writer_password = "YzKG89nsIWvMf2M5q0B7"
laim_reader_user = "laim_reader"
laim_reader_password = "Avv7VZs4x3iuxAgPysrH"

# LAIM DSN: localhost (backend_core corre en el mismo servidor que MariaDB; grants @localhost)
laim_admin_dsn = (
    "mysql+pymysql://laim_admin:NDt%40dL_0Rxw6aiI_%40XSE@localhost:3306/laim_core_db"
)
laim_writer_dsn = (
    "mysql+pymysql://laim_writer:YzKG89nsIWvMf2M5q0B7@localhost:3306/laim_core_db"
)
laim_reader_dsn = (
    "mysql+pymysql://laim_reader:Avv7VZs4x3iuxAgPysrH@localhost:3306/laim_core_db"
)

# CLI MariaDB (Oracle Linux 10)
mariadb_cli_path = "/usr/bin/mariadb"

# Redis (sesión compartida - en servidor frontend.anewhope.aws)
redis_password = "PassRedis2025"

# Fernet (cifrado de contraseñas)
fernet_key = "a1e4-_9rGGPRpFhcqAy8wrlR2elCWvMsQhLVd82dM1Y="

# Cap CAPTCHA (registro LAIM) — secret del servidor Cap auto-hospedado
# Obtener del dashboard de Cap tras crear una site key.
# IMPORTANTE: Reemplazar con el secret real generado por el dashboard Cap.
laim_cap_secret = "sk-2OlIdE9wXxLj3bEmGTxbRxhKL8RvN7jsbao4aOEBw"
# (Antigua clave hCaptcha conservada como referencia, ya no se usa)
# laim_hcaptcha_secret = "0x0000000000000000000000000000000000000000"

# ChromaDB (autenticación del servidor de base de datos vectorial) - CAMBIAR EN PRODUCCIÓN
chroma_auth_token = "chroma-pre-token-aws-2026"
chroma_auth_provider = "chromadb.auth.token_authn.TokenAuthenticationServerProvider"
chroma_auth_credentials_provider = "chromadb.auth.token_authn.TokenAuthClientProvider"

# Parámetros de entrenamiento por defecto
# Estos valores se usan para crear el registro inicial en jobs_entrenamientos
# al iniciar cada entrenamiento o reentrenamiento
training_default_learning_rate = 0.001
training_default_batch_size = 32
training_default_epochs = 10
training_default_embedding_dimension = 768
training_default_sequence_length = 512
training_default_hidden_units = 256
training_default_dropout_rate = 0.1
training_default_chunk_size = 1000
training_default_chunk_overlap = 200
training_default_temperature = 0.7
training_default_max_tokens = 2048
training_default_distance_metric = "cosine"
training_default_top_k = 5
training_default_loss_function = "cross_entropy"
training_default_optimizer = "adam"
